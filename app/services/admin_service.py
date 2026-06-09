"""User and role administration."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import ActivityStatusLog
from app.models.material import MaterialAudit
from app.models.rbac import Permission, Role, RolePermission, RoleRequest, UserRole
from app.models.user import User
from app.services.notification_service import NotificationService


class AdminService:
    def __init__(self, db: AsyncSession, notification: NotificationService | None = None):
        self.db = db
        self.notification = notification

    # ── Role Requests ──

    async def list_role_requests(self) -> list[dict]:
        result = await self.db.execute(
            select(RoleRequest, Role.name, User.email, User.display_name)
            .join(Role, Role.id == RoleRequest.role_id)
            .join(User, User.id == RoleRequest.user_id)
            .where(RoleRequest.status == "pending")
            .order_by(RoleRequest.created_at)
        )
        rows = result.all()
        return [
            {
                "rr": rr, "role_name": role_name,
                "user_email": user_email, "user_display_name": user_display_name,
            }
            for rr, role_name, user_email, user_display_name in rows
        ]

    async def approve_role_request(self, request_id: UUID, reviewer_id: UUID) -> dict:
        rr = await self._get_role_request(request_id)
        rr.status = "approved"
        rr.reviewer_id = reviewer_id
        rr.reviewed_at = datetime.now(timezone.utc)

        user_role = UserRole(user_id=rr.user_id, role_id=rr.role_id)
        self.db.add(user_role)
        await self.db.commit()
        await self.db.refresh(rr)

        role_result = await self.db.execute(select(Role.name).where(Role.id == rr.role_id))
        role_name = role_result.scalar_one()
        if self.notification:
            await self.notification.send_reminder(
                rr.user_id, f"你的角色申请（{role_name}）已通过审批"
            )
        return self._format_role_request(rr, role_name)

    async def reject_role_request(self, request_id: UUID, reviewer_id: UUID, comment: str) -> dict:
        rr = await self._get_role_request(request_id)
        rr.status = "rejected"
        rr.comment = comment
        rr.reviewer_id = reviewer_id
        rr.reviewed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(rr)

        role_result = await self.db.execute(select(Role.name).where(Role.id == rr.role_id))
        role_name = role_result.scalar_one()
        if self.notification:
            reason_suffix = f"原因：{comment}" if comment else ""
            await self.notification.send_reminder(
                rr.user_id,
                f"你的角色申请（{role_name}）未通过审批。{reason_suffix}".strip()
            )
        return self._format_role_request(rr, role_name)

    # ── User CRUD ──

    async def list_users(self, keyword: str | None = None, sort_order: str = "desc",
                         role: str | None = None, status: str | None = None) -> list[dict]:
        order = User.created_at.asc() if sort_order == "asc" else User.created_at.desc()
        query = select(User).order_by(order)
        if keyword:
            pattern = f"%{keyword}%"
            query = query.where(or_(User.email.ilike(pattern), User.display_name.ilike(pattern)))
        if role:
            sub = select(UserRole.user_id).join(Role, UserRole.role_id == Role.id).where(Role.name == role)
            query = query.where(User.id.in_(sub))
        if status == "active":
            query = query.where(User.is_active == True, User.is_archived == False)
        elif status == "disabled":
            query = query.where(User.is_active == False, User.is_archived == False)
        elif status == "archived":
            query = query.where(User.is_archived == True)
        result = await self.db.execute(query)
        users = result.scalars().all()

        output = []
        for u in users:
            roles = await self._get_user_roles(u.id)
            output.append({
                "user": u, "roles": roles,
                "is_active": u.is_active, "is_archived": u.is_archived,
                "archive_reason": u.archive_reason, "archived_at": u.archived_at,
            })
        return output

    async def get_user_detail(self, user_id: UUID) -> dict:
        u = await self._get_user(user_id)
        roles = await self._get_user_roles(u.id)
        permissions = await self._get_user_permissions(u.id)
        return {"user": u, "roles": roles, "permissions": permissions}

    async def get_user_overview(self, user_id: UUID) -> dict:
        u = await self._get_user(user_id)
        roles = await self._get_user_roles(u.id)

        login_result = await self.db.execute(
            text("SELECT login_id, success, created_at FROM login_attempts "
                 "WHERE login_id = :e ORDER BY created_at DESC LIMIT 20"),
            {"e": u.email},
        )
        login_history = [
            {"login_id": row[0], "success": row[1], "created_at": row[2]}
            for row in login_result.all()
        ]

        audit_result = await self.db.execute(
            select(MaterialAudit.action, MaterialAudit.created_at)
            .where(MaterialAudit.user_id == user_id)
            .order_by(MaterialAudit.created_at.desc()).limit(20)
        )
        actions = [
            {"action": f"{row[0]} 材料", "created_at": row[1]}
            for row in audit_result.all()
        ]

        status_result = await self.db.execute(
            select(ActivityStatusLog.to_status, ActivityStatusLog.created_at)
            .where(ActivityStatusLog.operator_id == user_id)
            .order_by(ActivityStatusLog.created_at.desc()).limit(20)
        )
        for to_status, ts in status_result.all():
            actions.append({"action": f"状态变更 → {to_status}", "created_at": ts})

        actions.sort(key=lambda a: a["created_at"], reverse=True)
        actions = actions[:20]

        return {
            "user": u, "roles": roles,
            "is_active": u.is_active, "is_archived": u.is_archived,
            "archive_reason": u.archive_reason, "archived_at": u.archived_at,
            "login_history": login_history, "recent_actions": actions,
        }

    async def update_user_roles(self, user_id: UUID, role_ids: list[UUID]) -> dict:
        u = await self._get_user(user_id)

        existing = (await self.db.execute(
            select(UserRole).where(UserRole.user_id == user_id)
        )).scalars().all()
        for ur in existing:
            await self.db.delete(ur)

        for role_id in role_ids:
            self.db.add(UserRole(user_id=user_id, role_id=role_id))
        await self.db.commit()

        roles = await self._get_user_roles(u.id)
        permissions = await self._get_user_permissions(u.id)
        return {"user": u, "roles": roles, "permissions": permissions}

    async def update_user_status(self, user_id: UUID, is_active: bool) -> dict:
        u = await self._get_user(user_id)
        u.is_active = is_active
        await self.db.commit()
        await self.db.refresh(u)
        roles = await self._get_user_roles(u.id)
        permissions = await self._get_user_permissions(u.id)
        return {"user": u, "roles": roles, "permissions": permissions}

    async def archive_user(self, user_id: UUID, reason: str | None = None) -> None:
        u = await self._get_user(user_id)
        u.is_archived = True
        u.archived_at = datetime.now(timezone.utc)
        u.archive_reason = reason
        await self.db.commit()

    async def unarchive_user(self, user_id: UUID) -> None:
        u = await self._get_user(user_id)
        u.is_archived = False
        await self.db.commit()

    # ── Helpers ──

    async def _get_user(self, user_id: UUID) -> User:
        u = await self.db.get(User, user_id)
        if u is None:
            raise LookupError("用户不存在")
        return u

    async def _get_role_request(self, request_id: UUID) -> RoleRequest:
        rr = await self.db.get(RoleRequest, request_id)
        if rr is None:
            raise LookupError("申请不存在")
        if rr.status != "pending":
            raise ValueError("该申请已被处理")
        return rr

    async def _get_user_roles(self, user_id: UUID) -> list[str]:
        result = await self.db.execute(
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        return [row[0] for row in result.all()]

    async def _get_user_permissions(self, user_id: UUID) -> list[str]:
        result = await self.db.execute(
            select(Permission.name)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(UserRole.user_id == user_id)
        )
        return [row[0] for row in result.all()]

    @staticmethod
    def _format_role_request(rr: RoleRequest, role_name: str) -> dict:
        return {
            "id": rr.id, "user_id": rr.user_id, "role_id": rr.role_id,
            "role_name": role_name, "status": rr.status, "comment": rr.comment,
            "created_at": rr.created_at,
            "reviewer_id": rr.reviewer_id, "reviewed_at": rr.reviewed_at,
        }
