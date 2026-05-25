from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.errors import ConflictError, NotFoundError
from app.models.rbac import Role, RoleRequest, UserRole
from app.models.user import User
from app.rbac import require_permission
from app.schemas.role_request import RoleRequestReview, RoleRequestResponse

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
