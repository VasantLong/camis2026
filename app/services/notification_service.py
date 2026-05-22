from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.rbac import UserRole

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, db: AsyncSession | None = None):
        self.db = db

    async def send_reminder(self, user_id: UUID, message: str, channel: str = "system") -> None:
        if self.db is None:
            logger.info("notification user=%s channel=%s message=%s", user_id, channel, message)
            return
        notif = Notification(user_id=user_id, message=message, channel=channel)
        self.db.add(notif)
        await self.db.commit()

    async def notify_role(self, role_name: str, message: str) -> None:
        if self.db is None:
            logger.info("notification role=%s message=%s", role_name, message)
            return
        from app.models.rbac import Role
        role_result = await self.db.execute(
            select(Role.id).where(Role.name == role_name)
        )
        role_id = role_result.scalar()
        if role_id is None:
            return
        user_result = await self.db.execute(
            select(UserRole.user_id).where(UserRole.role_id == role_id)
        )
        for (user_id,) in user_result.all():
            notif = Notification(user_id=user_id, message=message, channel="system")
            self.db.add(notif)
        await self.db.commit()

    async def check_overdue(self, activity_id: UUID) -> None:
        if self.db is None:
            logger.info("overdue check activity=%s", activity_id)
            return
        from app.models.activity import Activity
        from datetime import datetime, timezone

        activity = await self.db.get(Activity, activity_id)
        if activity and activity.deadline < datetime.now(timezone.utc) and activity.status == "待设计方案":
            msg = f"活动 {activity.name} 已逾期，请尽快提交方案"
            notif = Notification(user_id=activity.owner_id, message=msg, channel="system")
            self.db.add(notif)
            await self.db.commit()
