import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

logger = logging.getLogger("camis.redis")

from sqlalchemy import func, select

from app.database import get_db
from app.deps import get_current_user
from app.models.activity import Activity, ActivityStatusLog, SecurityPlan
from app.models.document import Document
from app.models.rbac import Role, RoleRequest, UserRole
from app.models.user import User
from app.rbac import get_user_permissions, get_user_roles, require_permission
from app.schemas.activity import ActivityCreate, ActivityListParams, ActivityPaginatedResponse, ActivityResponse, StatusLogEntry
from app.services.activity_service import ActivityService
from app.services.redis_client import get_redis
from app.errors import NotFoundError, ValidationError

router = APIRouter(prefix="/activities", tags=["activities"])


def _service(db=Depends(get_db)) -> ActivityService:
    return ActivityService(db)


PROMOTER_STATUSES = {"待设计方案"}
SECURITY_OFFICER_STATUSES = {"待安保方案设计", "待备案申请"}
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

    # Promoter 只看待设计方案（待操作），已完成=操作过的活动
    if "Promoter" in roles:
        return current_user.id, PROMOTER_STATUSES

    return current_user.id, None


@router.post("", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
async def create_activity(
    body: ActivityCreate,
    current_user: User = Depends(get_current_user),
    svc: ActivityService = Depends(_service),
    _perm: None = require_permission("create_activity"),
):
    try:
        if body.designer_id is None:
            body.designer_id = current_user.id
        return await svc.create(current_user.id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT if "冲突" in str(e) else status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=ActivityPaginatedResponse)
async def list_activities(
    status_filter: str | None = Query(None, alias="status"),
    keyword: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    tab: str | None = Query(None, pattern="^(pending|completed|all)$"),
    current_user: User = Depends(get_current_user),
    svc: ActivityService = Depends(_service),
    _perm: None = require_permission("view_owned_activity"),
    db=Depends(get_db),
):
    from datetime import datetime

    owner_id, allowed = await _visibility(current_user, db)

    if tab == "completed":
        items, total = await svc.list_completed(current_user.id, owner_id, allowed, page, size,
            status_filter, keyword, date_from, date_to)
    else:
        params = ActivityListParams(
            status=status_filter,
            keyword=keyword,
            date_from=datetime.fromisoformat(date_from) if date_from else None,
            date_to=datetime.fromisoformat(date_to) if date_to else None,
            page=page,
            size=size,
        )
        include_terminal = (tab == "all")
        items, total = await svc.list(params, owner_id, allowed, include_terminal)
    return ActivityPaginatedResponse(items=items, total=total)


@router.get("/counts")
async def get_counts(
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    from datetime import date, datetime, timezone

    roles = await get_user_roles(current_user, db)

    from app.services.workflow_service import TERMINAL_STATUSES

    counts: dict = {}

    # SuperAdmin (check first — highest priority)
    if "SuperAdmin" in roles:
        total_users = await db.scalar(
            select(func.count(User.id)).where(User.is_archived == False)
        )
        pending_rr = await db.scalar(
            select(func.count(RoleRequest.id)).where(RoleRequest.status == "pending")
        )
        total_acts = await db.scalar(select(func.count(Activity.id)))
        counts["total_users"] = total_users or 0
        counts["pending_role_requests"] = pending_rr or 0
        counts["total_activities"] = total_acts or 0
        return counts

    # AdminManager / AdminStaff
    if "AdminManager" in roles or "AdminStaff" in roles:
        total = await db.scalar(select(func.count(Activity.id)))
        # approval_rate: numerator = approved-and-beyond; denominator = ever-reached-filing
        numerator = await db.scalar(
            select(func.count(Activity.id)).where(
                Activity.status.in_({"审批通过-待举办", "举办中", "已结束"})
            )
        )
        filing_subq = (
            select(ActivityStatusLog.activity_id.distinct())
            .where(ActivityStatusLog.to_status == "备案材料已交接")
            .subquery()
        )
        denominator = await db.scalar(
            select(func.count(Activity.id)).where(Activity.id.in_(filing_subq))
        )
        denom_val = denominator or 0
        approval_rate = round((numerator or 0) / denom_val, 2) if denom_val > 0 else 0.0

        now_utc = datetime.now(timezone.utc)
        month_start = now_utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        new_this_month = await db.scalar(
            select(func.count(Activity.id)).where(Activity.created_at >= month_start)
        )

        counts["total"] = total or 0
        counts["approval_rate"] = approval_rate
        counts["new_this_month"] = new_this_month or 0
        counts["pending_force_confirm"] = 0  # future: AdminManager confirmation flow
        return counts

    # SecurityManager
    if "SecurityManager" in roles:
        pending_sign = await db.scalar(
            select(func.count(Activity.id)).where(Activity.status == "待安保方案设计")
        )
        pending_pack = await db.scalar(
            select(func.count(Activity.id)).where(Activity.status == "待备案申请")
        )
        counts["pending_sign_confirm"] = pending_sign or 0
        counts["pending_pack"] = pending_pack or 0
        return counts

    # SecurityOfficer
    if "SecurityOfficer" in roles:
        pending_draft = await db.scalar(
            select(func.count(Activity.id)).where(Activity.status == "待安保方案设计")
        )
        handled_subq = (
            select(ActivityStatusLog.activity_id.distinct())
            .where(ActivityStatusLog.operator_id == current_user.id)
            .subquery()
        )
        pending_pack = await db.scalar(
            select(func.count(Activity.id)).where(
                Activity.status == "待备案申请",
                Activity.id.in_(handled_subq),
            )
        )
        counts["pending_draft"] = pending_draft or 0
        counts["pending_pack"] = pending_pack or 0
        return counts

    # GovLiaison
    if "GovLiaison" in roles:
        pending_review = await db.scalar(
            select(func.count(Activity.id)).where(Activity.status == "备案材料已交接")
        )
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        registered_today = await db.scalar(
            select(func.count(func.distinct(ActivityStatusLog.activity_id))).where(
                ActivityStatusLog.operator_id == current_user.id,
                ActivityStatusLog.created_at >= today_start,
            )
        )
        counts["pending_review"] = pending_review or 0
        counts["registered_today"] = registered_today or 0
        return counts

    # Promoter (default / fallback)
    my_activities = await db.scalar(
        select(func.count(Activity.id)).where(
            Activity.owner_id == current_user.id,
            Activity.status.notin_(TERMINAL_STATUSES),
        )
    )
    pending_plan = await db.scalar(
        select(func.count(Activity.id)).where(
            Activity.owner_id == current_user.id,
            Activity.status == "待设计方案",
        )
    )
    counts["my_activities"] = my_activities or 0
    counts["pending_plan"] = pending_plan or 0
    return counts


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
        activity = await svc.get(activity_id, owner_id, allowed)
    except LookupError:
        # Fallback: user may have operated on this activity (status_log)
        from app.models.activity import ActivityStatusLog
        op_check = await db.execute(
            select(ActivityStatusLog.id).where(
                ActivityStatusLog.activity_id == activity_id,
                ActivityStatusLog.operator_id == current_user.id,
            ).limit(1)
        )
        if op_check.scalar_one_or_none() is None:
            raise NotFoundError("活动不存在")
        activity = await svc.get(activity_id, None, None)
    if activity.designer_id:
        designer = await db.get(User, activity.designer_id)
        if designer:
            activity.designer_name = designer.display_name
            activity.designer_phone = designer.contact_phone
    return activity


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
    from app.services.document_service import DocumentService

    redis = await get_redis()
    cache_key = f"activity:{activity_id}:docs"
    if redis:
        cached = await redis.get(cache_key)
        logger.info("redis GET key=%s hit=%s", cache_key, cached is not None)
        if cached:
            return json.loads(cached)

    docs = await DocumentService(db).list_by_activity(activity_id)
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
    if redis:
        logger.info("redis SET key=%s ex=300", cache_key)
        await redis.set(cache_key, json.dumps(items), ex=300)
    return items


class SecurityPlanResponse(BaseModel):
    risk_level: str | None = None
    audit_status: str | None = None
    manager_name: str | None = None
    sign_time: str | None = None
    last_reject_reason: str | None = None
    rejected_at: str | None = None


class SecurityPlanUpdate(BaseModel):
    risk_level: str | None = None


@router.get("/{activity_id}/security-plan", response_model=SecurityPlanResponse)
async def get_security_plan(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: ActivityService = Depends(_service),
    _perm: None = require_permission("view_owned_activity"),
):
    result = await svc.get_security_plan(activity_id)
    if result is None:
        return SecurityPlanResponse()
    return SecurityPlanResponse(**result)


@router.put("/{activity_id}/security-plan", response_model=SecurityPlanResponse)
async def update_security_plan(
    activity_id: UUID,
    body: SecurityPlanUpdate,
    current_user: User = Depends(get_current_user),
    svc: ActivityService = Depends(_service),
    _perm: None = require_permission("manage_security"),
):
    if body.risk_level is not None:
        await svc.set_security_risk_level(activity_id, body.risk_level)
    result = await svc.get_security_plan(activity_id)
    return SecurityPlanResponse(**result) if result else SecurityPlanResponse()
