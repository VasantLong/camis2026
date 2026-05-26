from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.errors import ConflictError, NotFoundError
from app.models.rbac import Permission, Role, RolePermission, RoleRequest, UserRole
from app.models.user import User
from app.rbac import require_permission
from app.schemas.role_request import RoleRequestReview, RoleRequestResponse
from app.schemas.user_admin import (
    UserDetail,
    UserListItem,
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
        select(RoleRequest, Role.name)
        .join(Role, Role.id == RoleRequest.role_id)
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
        )
        for rr, role_name in rows
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _perm: None = require_permission("administer_users"),
):
    result = await db.execute(
        select(User).order_by(User.created_at.desc())
    )
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
        roles=roles,
        permissions=permissions,
        created_at=u.created_at,
        updated_at=u.updated_at,
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
        roles=roles,
        permissions=permissions,
        created_at=u.created_at,
        updated_at=u.updated_at,
    )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _perm: None = require_permission("administer_users"),
):
    u = await db.get(User, user_id)
    if u is None:
        raise NotFoundError("用户不存在")
    if u.id == current_user.id:
        raise ConflictError("不能删除自己")

    await db.delete(u)
    await db.commit()
    return {"message": "已删除"}
