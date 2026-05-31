from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.errors import ConflictError, NotFoundError
from app.models.rbac import Permission, Role, RolePermission, RoleRequest, UserRole
from app.models.user import User
from app.rbac import require_permission
from app.schemas.role_request import RoleRequestReview, RoleRequestResponse
from app.models.activity import ActivityStatusLog
from app.models.material import MaterialAudit
from app.schemas.user_admin import (
    ActivityActionItem,
    LoginHistoryItem,
    UserDetail,
    UserListItem,
    UserOverview,
    UserRoleUpdate,
    UserStatusUpdate,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/role-requests", response_model=list[RoleRequestResponse])
async def list_role_requests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _perm: None = require_permission("manage_users"),
):
    result = await db.execute(
        select(RoleRequest, Role.name, User.email, User.display_name)
        .join(Role, Role.id == RoleRequest.role_id)
        .join(User, User.id == RoleRequest.user_id)
        .where(RoleRequest.status == "pending")
        .order_by(RoleRequest.created_at)
    )
    rows = result.all()
    return [
        RoleRequestResponse(
            id=rr.id,
            user_id=rr.user_id,
            role_id=rr.role_id,
            role_name=role_name,
            status=rr.status,
            comment=rr.comment,
            created_at=rr.created_at,
            reviewer_id=rr.reviewer_id,
            reviewed_at=rr.reviewed_at,
            user_email=user_email,
            user_display_name=user_display_name,
        )
        for rr, role_name, user_email, user_display_name in rows
    ]


@router.post("/role-requests/{request_id}/approve", response_model=RoleRequestResponse)
async def approve_role_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _perm: None = require_permission("manage_users"),
):
    rr = await db.get(RoleRequest, request_id)
    if rr is None:
        raise NotFoundError("申请不存在")
    if rr.status != "pending":
        raise ConflictError("该申请已被处理")

    rr.status = "approved"
    rr.reviewer_id = current_user.id
    rr.reviewed_at = datetime.now(timezone.utc)

    user_role = UserRole(user_id=rr.user_id, role_id=rr.role_id)
    db.add(user_role)
    await db.commit()
    await db.refresh(rr)

    role_result = await db.execute(select(Role.name).where(Role.id == rr.role_id))
    role_name = role_result.scalar_one()

    return RoleRequestResponse(
        id=rr.id,
        user_id=rr.user_id,
        role_id=rr.role_id,
        role_name=role_name,
        status=rr.status,
        comment=rr.comment,
        created_at=rr.created_at,
        reviewer_id=rr.reviewer_id,
        reviewed_at=rr.reviewed_at,
    )


@router.post("/role-requests/{request_id}/reject", response_model=RoleRequestResponse)
async def reject_role_request(
    request_id: UUID,
    body: RoleRequestReview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _perm: None = require_permission("manage_users"),
):
    rr = await db.get(RoleRequest, request_id)
    if rr is None:
        raise NotFoundError("申请不存在")
    if rr.status != "pending":
        raise ConflictError("该申请已被处理")

    rr.status = "rejected"
    rr.comment = body.comment
    rr.reviewer_id = current_user.id
    rr.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(rr)

    role_result = await db.execute(select(Role.name).where(Role.id == rr.role_id))
    role_name = role_result.scalar_one()

    return RoleRequestResponse(
        id=rr.id,
        user_id=rr.user_id,
        role_id=rr.role_id,
        role_name=role_name,
        status=rr.status,
        comment=rr.comment,
        created_at=rr.created_at,
        reviewer_id=rr.reviewer_id,
        reviewed_at=rr.reviewed_at,
    )


# ── user CRUD (administer_users) ──


@router.get("/users", response_model=list[UserListItem])
async def list_users(
    keyword: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _perm: None = require_permission("administer_users"),
):
    query = select(User).order_by(User.created_at.desc())
    if keyword:
        pattern = f"%{keyword}%"
        query = query.where(
            or_(User.email.ilike(pattern), User.display_name.ilike(pattern))
        )
    result = await db.execute(query)
    users = result.scalars().all()
    output = []
    for u in users:
        role_result = await db.execute(
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == u.id)
        )
        roles = [row[0] for row in role_result.all()]
        output.append(UserListItem(
            id=u.id,
            email=u.email,
            display_name=u.display_name,
            is_active=u.is_active,
            is_archived=u.is_archived,
            archive_reason=u.archive_reason,
            archived_at=u.archived_at,
            roles=roles,
            created_at=u.created_at,
        ))
    return output


@router.get("/users/{user_id}", response_model=UserDetail)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _perm: None = require_permission("administer_users"),
):
    u = await db.get(User, user_id)
    if u is None:
        raise NotFoundError("用户不存在")

    role_result = await db.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == u.id)
    )
    roles = [row[0] for row in role_result.all()]

    perm_result = await db.execute(
        select(Permission.name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == u.id)
    )
    permissions = [row[0] for row in perm_result.all()]

    return UserDetail(
        id=u.id,
        email=u.email,
        display_name=u.display_name,
        is_active=u.is_active,
        is_archived=u.is_archived,
        roles=roles,
        permissions=permissions,
        created_at=u.created_at,
        updated_at=u.updated_at,
    )


@router.get("/users/{user_id}/overview", response_model=UserOverview)
async def get_user_overview(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _perm: None = require_permission("administer_users"),
):
    u = await db.get(User, user_id)
    if u is None:
        raise NotFoundError("用户不存在")

    role_result = await db.execute(
        select(Role.name).join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == u.id)
    )
    roles = [row[0] for row in role_result.all()]

    # Login history (last 20)
    from sqlalchemy import text
    login_result = await db.execute(
        text("SELECT login_id, success, created_at FROM login_attempts "
             "WHERE login_id = :e ORDER BY created_at DESC LIMIT 20"),
        {"e": u.email},
    )
    login_history = [
        LoginHistoryItem(login_id=row[0], success=row[1], created_at=row[2])
        for row in login_result.all()
    ]

    # Recent activity: material audits + status transitions (last 20 combined)
    audit_result = await db.execute(
        select(MaterialAudit.action, MaterialAudit.created_at)
        .where(MaterialAudit.user_id == user_id)
        .order_by(MaterialAudit.created_at.desc())
        .limit(20)
    )
    actions = [
        ActivityActionItem(action=f"{row[0]} 材料", created_at=row[1])
        for row in audit_result.all()
    ]

    status_result = await db.execute(
        select(ActivityStatusLog.to_status, ActivityStatusLog.created_at)
        .where(ActivityStatusLog.operator_id == user_id)
        .order_by(ActivityStatusLog.created_at.desc())
        .limit(20)
    )
    for to_status, ts in status_result.all():
        actions.append(ActivityActionItem(
            action=f"状态变更 → {to_status}", created_at=ts
        ))

    actions.sort(key=lambda a: a.created_at, reverse=True)
    actions = actions[:20]

    return UserOverview(
        id=u.id, email=u.email, display_name=u.display_name,
        is_active=u.is_active, is_archived=u.is_archived,
        archive_reason=u.archive_reason, archived_at=u.archived_at,
        roles=roles, created_at=u.created_at,
        login_history=login_history, recent_actions=actions,
    )


@router.put("/users/{user_id}/roles", response_model=UserDetail)
async def update_user_roles(
    user_id: UUID,
    body: UserRoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _perm: None = require_permission("administer_users"),
):
    u = await db.get(User, user_id)
    if u is None:
        raise NotFoundError("用户不存在")

    existing = (await db.execute(
        select(UserRole).where(UserRole.user_id == user_id)
    )).scalars().all()
    for ur in existing:
        await db.delete(ur)

    for role_id in body.role_ids:
        db.add(UserRole(user_id=user_id, role_id=role_id))

    await db.commit()

    role_result = await db.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == u.id)
    )
    roles = [row[0] for row in role_result.all()]

    perm_result = await db.execute(
        select(Permission.name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == u.id)
    )
    permissions = [row[0] for row in perm_result.all()]

    return UserDetail(
        id=u.id,
        email=u.email,
        display_name=u.display_name,
        is_active=u.is_active,
        is_archived=u.is_archived,
        roles=roles,
        permissions=permissions,
        created_at=u.created_at,
        updated_at=u.updated_at,
    )


@router.patch("/users/{user_id}/status", response_model=UserDetail)
async def update_user_status(
    user_id: UUID,
    body: UserStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _perm: None = require_permission("administer_users"),
):
    u = await db.get(User, user_id)
    if u is None:
        raise NotFoundError("用户不存在")

    u.is_active = body.is_active
    await db.commit()
    await db.refresh(u)

    role_result = await db.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == u.id)
    )
    roles = [row[0] for row in role_result.all()]

    perm_result = await db.execute(
        select(Permission.name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == u.id)
    )
    permissions = [row[0] for row in perm_result.all()]

    return UserDetail(
        id=u.id,
        email=u.email,
        display_name=u.display_name,
        is_active=u.is_active,
        is_archived=u.is_archived,
        roles=roles,
        permissions=permissions,
        created_at=u.created_at,
        updated_at=u.updated_at,
    )


@router.post("/users/{user_id}/archive")
async def archive_user(
    user_id: UUID,
    body: dict | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _perm: None = require_permission("administer_users"),
):
    u = await db.get(User, user_id)
    if u is None:
        raise NotFoundError("用户不存在")
    if u.id == current_user.id:
        raise ConflictError("不能归档自己")
    u.is_archived = True
    u.archived_at = datetime.now(timezone.utc)
    u.archive_reason = (body or {}).get("reason")
    await db.commit()
    return {"message": "已归档"}


@router.post("/users/{user_id}/unarchive")
async def unarchive_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _perm: None = require_permission("administer_users"),
):
    u = await db.get(User, user_id)
    if u is None:
        raise NotFoundError("用户不存在")
    u.is_archived = False
    await db.commit()
    return {"message": "已取消归档"}
