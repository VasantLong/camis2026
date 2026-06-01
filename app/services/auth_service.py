"""Authentication and user profile management."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    create_email_change_token,
    create_refresh_token,
    hash_password,
    record_login_attempt,
    revoke_user_tokens,
    verify_email_change_token,
    verify_password,
)
from app.models.auth import RefreshToken
from app.models.rbac import Permission, Role, RolePermission, RoleRequest, UserRole
from app.models.user import User

logger = logging.getLogger("camis.auth_service")


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Registration & Login ──

    async def register_user(
        self, email: str, password: str, display_name: str, contact_phone: str | None
    ) -> User:
        existing = await self.db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise ValueError("邮箱已注册")

        user = User(
            email=email,
            password_hash=hash_password(password),
            display_name=display_name,
            contact_phone=contact_phone,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def authenticate_user(self, email: str, password: str) -> User:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None or not verify_password(password, user.password_hash):
            raise ValueError("邮箱或密码错误")
        if user.is_archived:
            raise PermissionError("该账号已被归档，请联系管理员")
        if not user.is_active:
            raise PermissionError("该账号已被禁用")
        return user

    # ── Token management ──

    async def create_session(self, user: User) -> tuple[str, str]:
        """Create access + refresh token pair. Returns (access_token, refresh_token)."""
        access = create_access_token(str(user.id), user.email)
        refresh = await create_refresh_token(self.db, str(user.id))
        return access, refresh

    async def refresh_session(self, refresh_token_raw: str) -> tuple[User, str, str]:
        """Validate refresh token and create new token pair."""
        from app.auth import verify_refresh_token

        token_record = await verify_refresh_token(self.db, refresh_token_raw)
        if token_record is None:
            raise ValueError("Invalid refresh token")

        token_record.revoked = True
        self.db.add(token_record)
        await self.db.commit()

        user = await self.db.get(User, token_record.user_id)
        if user is None:
            raise LookupError("User not found")

        access = create_access_token(str(user.id), user.email)
        new_refresh = await create_refresh_token(self.db, str(user.id))
        return user, access, new_refresh

    async def revoke_session(self, user_id: UUID) -> None:
        await revoke_user_tokens(self.db, str(user_id))

    # ── User profile ──

    async def get_user_profile(self, user: User) -> dict:
        """Return user profile dict with roles, permissions, pending role request."""
        roles, role_perms, perm_set = await self._resolve_permissions(user.id)

        pending_rr = None
        rr_result = await self.db.execute(
            select(RoleRequest, Role.name)
            .join(Role, Role.id == RoleRequest.role_id)
            .where(RoleRequest.user_id == user.id, RoleRequest.status == "pending")
            .order_by(RoleRequest.created_at.desc())
            .limit(1)
        )
        row = rr_result.first()
        if row:
            rr, role_name = row
            pending_rr = {
                "id": str(rr.id),
                "role_id": str(rr.role_id),
                "role_name": role_name,
                "status": rr.status,
                "created_at": rr.created_at.isoformat(),
            }

        return {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "is_active": user.is_active,
            "contact_phone": user.contact_phone,
            "permissions": list(perm_set),
            "roles": roles,
            "role_permissions": role_perms,
            "pending_role_request": pending_rr,
        }

    async def update_profile(
        self, user: User, display_name: str, contact_phone: str | None
    ) -> User:
        user.display_name = display_name
        if contact_phone is not None:
            user.contact_phone = contact_phone
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    # ── Email change ──

    async def request_email_change(self, current_user: User, new_email: str) -> str:
        existing = await self.db.execute(select(User).where(User.email == new_email))
        if existing.scalar_one_or_none():
            raise ValueError("该邮箱已被注册")
        token = create_email_change_token(str(current_user.id), new_email)
        return token

    async def verify_and_apply_email_change(self, token_str: str) -> User:
        try:
            payload = verify_email_change_token(token_str)
        except Exception:
            raise ValueError("验证链接无效或已过期")

        user_id = payload.get("sub")
        new_email = payload.get("email")
        if not user_id or not new_email:
            raise ValueError("验证链接无效")

        existing = await self.db.execute(select(User).where(User.email == new_email))
        if existing.scalar_one_or_none():
            raise ValueError("该邮箱已被注册")

        user = await self.db.get(User, user_id)
        if user is None:
            raise LookupError("用户不存在")

        user.email = new_email
        self.db.add(user)
        await self.db.commit()
        await revoke_user_tokens(self.db, user_id)
        return user

    # ── Roles ──

    async def list_available_roles(self) -> list[Role]:
        result = await self.db.execute(
            select(Role).where(Role.name != "SuperAdmin").order_by(Role.name)
        )
        return list(result.scalars().all())

    async def submit_role_request(self, user_id: UUID, role_id: UUID) -> RoleRequest:
        existing = await self.db.execute(
            select(RoleRequest).where(
                RoleRequest.user_id == user_id, RoleRequest.status == "pending"
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("您已有待审批的角色申请")

        role = await self.db.get(Role, role_id)
        if role is None:
            raise LookupError("角色不存在")
        if role.name == "SuperAdmin":
            raise PermissionError("不能申请超级管理员角色")

        rr = RoleRequest(user_id=user_id, role_id=role_id)
        self.db.add(rr)
        await self.db.commit()
        await self.db.refresh(rr)
        return rr

    # ── Helpers ──

    async def _resolve_permissions(self, user_id: UUID) -> tuple[list[str], dict[str, list[str]], set[str]]:
        rp_result = await self.db.execute(
            select(Role.name, Permission.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .join(RolePermission, RolePermission.role_id == Role.id)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .where(UserRole.user_id == user_id)
            .order_by(Role.name)
        )
        role_perms: dict[str, list[str]] = {}
        perm_set: set[str] = set()
        for role_name, perm_name in rp_result.all():
            role_perms.setdefault(role_name, []).append(perm_name)
            perm_set.add(perm_name)

        role_result = await self.db.execute(
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        roles = [row[0] for row in role_result.all()]

        return roles, role_perms, perm_set
