import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

logger = logging.getLogger("camis.redis")

from sqlalchemy import select

from app.database import get_db
from app.deps import get_current_user
from app.models.activity import SecurityPlan
from app.models.document import Document
from app.models.user import User
from app.models.rbac import Role, UserRole
from app.rbac import get_user_permissions, require_permission
from app.schemas.activity import ActivityCreate, ActivityListParams, ActivityResponse, StatusLogEntry
from app.services.activity_service import ActivityService
from app.services.redis_client import get_redis
from app.errors import NotFoundError, ValidationError

router = APIRouter(prefix="/activities", tags=["activities"])


def _service(db=Depends(get_db)) -> ActivityService:
    return ActivityService(db)


SECURITY_OFFICER_STATUSES = {"待安保方案设计"}
SECURITY_MANAGER_STATUSES = {
    "待安保方案设计", "待备案申请", "备案材料已交接",
    "审批通过", "待补充备案材料",
}
GOV_LIAISON_STATUSES = {"备案材料已交接"}


async def _visibility(current_user: User, db) -> tuple[UUID | None, set[str] | None]:
    """返回 (owner_id_filter, allowed_statuses) 控制活动可见性。"""
    role_result = await db.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == current_user.id)
    )
    roles = {row[0] for row in role_result.all()}

    # SuperAdmin/Admin/Manager 看全部
    if roles & {"SuperAdmin", "AdminStaff", "AdminManager"}:
        return None, None

    # SecurityManager 看安保流程所有状态
    if "SecurityManager" in roles:
        return None, SECURITY_MANAGER_STATUSES

    # SecurityOfficer 只看待安保方案设计
    if "SecurityOfficer" in roles:
        return None, SECURITY_OFFICER_STATUSES

    # GovLiaison 只看备案材料已交接
    if "GovLiaison" in roles:
        return None, GOV_LIAISON_STATUSES

    # Promoter 看自己创建的所有状态
    if "Promoter" in roles:
        return current_user.id, None

    return current_user.id, None


@router.post("", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
async def create_activity(
    body: ActivityCreate,
    current_user: User = Depends(get_current_user),
    svc: ActivityService = Depends(_service),
    _perm: None = require_permission("create_activity"),
):
    try:
        return await svc.create(current_user.id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT if "冲突" in str(e) else status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=list[ActivityResponse])
async def list_activities(
    status_filter: str | None = Query(None, alias="status"),
    keyword: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    svc: ActivityService = Depends(_service),
    _perm: None = require_permission("view_owned_activity"),
    db=Depends(get_db),
):
    from datetime import datetime

    owner_id, allowed = await _visibility(current_user, db)
    params = ActivityListParams(
        status=status_filter,
        keyword=keyword,
        date_from=datetime.fromisoformat(date_from) if date_from else None,
        date_to=datetime.fromisoformat(date_to) if date_to else None,
        page=page,
        size=size,
    )
    items, _ = await svc.list(params, owner_id, allowed)
    return items


@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: ActivityService = Depends(_service),
    _perm: None = require_permission("view_owned_activity"),
    db=Depends(get_db),
):
    try:
        owner_id, allowed = await _visibility(current_user, db)
        return await svc.get(activity_id, owner_id, allowed)
    except LookupError as e:
        raise NotFoundError(str(e))


@router.get("/{activity_id}/history", response_model=list[StatusLogEntry])
async def get_status_history(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: ActivityService = Depends(_service),
    _perm: None = require_permission("view_owned_activity"),
):
    return await svc.get_status_history(activity_id)


@router.get("/{activity_id}/documents")
async def list_activity_documents(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
    _perm: None = require_permission("view_owned_activity"),
):
    redis = await get_redis()
    cache_key = f"activity:{activity_id}:docs"
    cached = await redis.get(cache_key)
    logger.info("redis GET key=%s hit=%s", cache_key, cached is not None)
    if cached:
        return json.loads(cached)

    result = await db.execute(
        select(Document).where(Document.activity_id == activity_id).order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    items = [
        {
            "id": str(d.id),
            "activity_id": str(d.activity_id) if d.activity_id else None,
            "uploader_id": str(d.uploader_id),
            "filename": d.filename,
            "minio_path": d.minio_path,
            "file_size": d.file_size,
            "content_type": d.content_type,
            "tags": d.tags,
        }
        for d in docs
    ]
    logger.info("redis SET key=%s ex=300", cache_key)
    await redis.set(cache_key, json.dumps(items), ex=300)
    return items


class SecurityPlanResponse(BaseModel):
    risk_level: str | None = None
    audit_status: str | None = None
    manager_name: str | None = None
    sign_time: str | None = None


@router.get("/{activity_id}/security-plan", response_model=SecurityPlanResponse)
async def get_security_plan(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
    _perm: None = require_permission("view_owned_activity"),
):
    result = await db.execute(
        select(SecurityPlan).where(SecurityPlan.activity_id == activity_id)
    )
    sp = result.scalar_one_or_none()
    if sp is None:
        return SecurityPlanResponse()

    manager_name = None
    if sp.manager_id:
        mgr = await db.get(User, sp.manager_id)
        manager_name = mgr.display_name if mgr else None

    return SecurityPlanResponse(
        risk_level=sp.risk_level,
        audit_status=sp.audit_status,
        manager_name=manager_name,
        sign_time=sp.sign_time.isoformat() if sp.sign_time else None,
    )
