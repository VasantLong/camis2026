from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User


async def get_user_roles(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    result = await db.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
    )
    return [row[0] for row in result.all()]


async def get_user_permissions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> set[str]:
    result = await db.execute(
        select(Permission.name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user.id)
    )
    return {row[0] for row in result.all()}


def require_permission(perm: str):
    async def check(
        permissions: set[str] = Depends(get_user_permissions),
    ):
        if perm not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"缺少权限: {perm}",
            )
    return Depends(check)


def require_any_permission(*perms: str):
    """Require at least one of the given permissions."""
    async def check(
        permissions: set[str] = Depends(get_user_permissions),
    ):
        if not any(p in permissions for p in perms):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"缺少权限，需要以下之一: {', '.join(perms)}",
            )
    return Depends(check)
