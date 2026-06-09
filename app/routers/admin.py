from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.errors import ConflictError, NotFoundError
from app.models.user import User
from app.rbac import require_permission
from app.schemas.role_request import RoleRequestReview, RoleRequestResponse
from app.schemas.user_admin import (
    ActivityActionItem,
    LoginHistoryItem,
    UserDetail,
    UserListItem,
    UserOverview,
    UserRoleUpdate,
    UserStatusUpdate,
)
from app.services.admin_service import AdminService
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/admin", tags=["admin"])


def _service(db=Depends(get_db)) -> AdminService:
    return AdminService(db, NotificationService(db))


# ── Role Requests ──


@router.get("/role-requests", response_model=list[RoleRequestResponse])
async def list_role_requests(
    svc: AdminService = Depends(_service),
    _perm: None = require_permission("manage_users"),
):
    rows = await svc.list_role_requests()
    return [
        RoleRequestResponse(
            id=r["rr"].id, user_id=r["rr"].user_id, role_id=r["rr"].role_id,
            role_name=r["role_name"], status=r["rr"].status, comment=r["rr"].comment,
            created_at=r["rr"].created_at, reviewer_id=r["rr"].reviewer_id,
            reviewed_at=r["rr"].reviewed_at,
            user_email=r["user_email"], user_display_name=r["user_display_name"],
        )
        for r in rows
    ]


@router.post("/role-requests/{request_id}/approve", response_model=RoleRequestResponse)
async def approve_role_request(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: AdminService = Depends(_service),
    _perm: None = require_permission("manage_users"),
):
    try:
        result = await svc.approve_role_request(request_id, current_user.id)
    except LookupError as e:
        raise NotFoundError(str(e))
    except ValueError as e:
        raise ConflictError(str(e))
    return RoleRequestResponse(**result)


@router.post("/role-requests/{request_id}/reject", response_model=RoleRequestResponse)
async def reject_role_request(
    request_id: UUID,
    body: RoleRequestReview,
    current_user: User = Depends(get_current_user),
    svc: AdminService = Depends(_service),
    _perm: None = require_permission("manage_users"),
):
    try:
        result = await svc.reject_role_request(request_id, current_user.id, body.comment)
    except LookupError as e:
        raise NotFoundError(str(e))
    except ValueError as e:
        raise ConflictError(str(e))
    return RoleRequestResponse(**result)


# ── User CRUD ──


@router.get("/users", response_model=list[UserListItem])
async def list_users(
    keyword: str | None = Query(None),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    role: str | None = Query(None),
    status: str | None = Query(None, pattern="^(active|disabled|archived)$"),
    svc: AdminService = Depends(_service),
    _perm: None = require_permission("administer_users"),
):
    rows = await svc.list_users(keyword, sort_order, role, status)
    return [
        UserListItem(
            id=r["user"].id, email=r["user"].email,
            display_name=r["user"].display_name,
            is_active=r["is_active"], is_archived=r["is_archived"],
            archive_reason=r["archive_reason"], archived_at=r["archived_at"],
            roles=r["roles"], created_at=r["user"].created_at,
        )
        for r in rows
    ]


@router.get("/users/{user_id}", response_model=UserDetail)
async def get_user(
    user_id: UUID,
    svc: AdminService = Depends(_service),
    _perm: None = require_permission("administer_users"),
):
    try:
        d = await svc.get_user_detail(user_id)
    except LookupError as e:
        raise NotFoundError(str(e))
    u = d["user"]
    return UserDetail(
        id=u.id, email=u.email, display_name=u.display_name,
        is_active=u.is_active, is_archived=u.is_archived,
        roles=d["roles"], permissions=d["permissions"],
        created_at=u.created_at, updated_at=u.updated_at,
    )


@router.get("/users/{user_id}/overview", response_model=UserOverview)
async def get_user_overview(
    user_id: UUID,
    svc: AdminService = Depends(_service),
    _perm: None = require_permission("administer_users"),
):
    try:
        ov = await svc.get_user_overview(user_id)
    except LookupError as e:
        raise NotFoundError(str(e))
    u = ov["user"]
    return UserOverview(
        id=u.id, email=u.email, display_name=u.display_name,
        is_active=ov["is_active"], is_archived=ov["is_archived"],
        archive_reason=ov["archive_reason"], archived_at=ov["archived_at"],
        roles=ov["roles"], created_at=u.created_at,
        login_history=[LoginHistoryItem(**h) for h in ov["login_history"]],
        recent_actions=[ActivityActionItem(**a) for a in ov["recent_actions"]],
    )


@router.put("/users/{user_id}/roles", response_model=UserDetail)
async def update_user_roles(
    user_id: UUID,
    body: UserRoleUpdate,
    current_user: User = Depends(get_current_user),
    svc: AdminService = Depends(_service),
    _perm: None = require_permission("administer_users"),
):
    if user_id == current_user.id:
        raise ConflictError("不能修改自己的角色")
    try:
        d = await svc.update_user_roles(user_id, body.role_ids)
    except LookupError as e:
        raise NotFoundError(str(e))
    u = d["user"]
    return UserDetail(
        id=u.id, email=u.email, display_name=u.display_name,
        is_active=u.is_active, is_archived=u.is_archived,
        roles=d["roles"], permissions=d["permissions"],
        created_at=u.created_at, updated_at=u.updated_at,
    )


@router.patch("/users/{user_id}/status", response_model=UserDetail)
async def update_user_status(
    user_id: UUID,
    body: UserStatusUpdate,
    current_user: User = Depends(get_current_user),
    svc: AdminService = Depends(_service),
    _perm: None = require_permission("administer_users"),
):
    if user_id == current_user.id:
        raise ConflictError("不能修改自己的状态")
    try:
        d = await svc.update_user_status(user_id, body.is_active)
    except LookupError as e:
        raise NotFoundError(str(e))
    u = d["user"]
    return UserDetail(
        id=u.id, email=u.email, display_name=u.display_name,
        is_active=u.is_active, is_archived=u.is_archived,
        roles=d["roles"], permissions=d["permissions"],
        created_at=u.created_at, updated_at=u.updated_at,
    )


@router.post("/users/{user_id}/archive")
async def archive_user(
    user_id: UUID,
    body: dict | None = None,
    current_user: User = Depends(get_current_user),
    svc: AdminService = Depends(_service),
    _perm: None = require_permission("administer_users"),
):
    if user_id == current_user.id:
        raise ConflictError("不能归档自己")
    try:
        await svc.archive_user(user_id, (body or {}).get("reason"))
    except LookupError as e:
        raise NotFoundError(str(e))
    return {"message": "已归档"}


@router.post("/users/{user_id}/unarchive")
async def unarchive_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: AdminService = Depends(_service),
    _perm: None = require_permission("administer_users"),
):
    try:
        await svc.unarchive_user(user_id)
    except LookupError as e:
        raise NotFoundError(str(e))
    return {"message": "已取消归档"}
