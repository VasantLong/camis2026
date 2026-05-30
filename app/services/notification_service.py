from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import update

from app.models.notification import Notification
from app.models.rbac import UserRole

logger = logging.getLogger(__name__)

READ_EXPIRE_DAYS = 30


class NotificationService:
    def __init__(self, db: AsyncSession | None = None):
        self.db = db

    async def send_reminder(self, user_id: UUID, message: str, channel: str = "system",
                            reference_id: UUID | None = None, reference_type: str | None = None) -> None:
        if self.db is None:
            logger.info("notification user=%s channel=%s message=%s", user_id, channel, message)
            return
        notif = Notification(
            user_id=user_id, message=message, channel=channel,
            reference_id=reference_id, reference_type=reference_type,
        )
        self.db.add(notif)
        await self.db.commit()

    async def notify_role(self, role_name: str, message: str,
                          reference_id: UUID | None = None, reference_type: str | None = None) -> None:
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
            notif = Notification(
                user_id=user_id, message=message, channel="system",
                reference_id=reference_id, reference_type=reference_type,
            )
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
            notif = Notification(
                user_id=activity.owner_id, message=msg, channel="system",
                reference_id=activity_id, reference_type="activity",
            )
            self.db.add(notif)
            await self.db.commit()

    async def list_for_user(self, user_id: UUID, limit: int = 10) -> list[dict]:
        from datetime import datetime, timedelta, timezone
        from sqlalchemy.orm import aliased
        from app.models.activity import Activity
        cutoff = datetime.now(timezone.utc) - timedelta(days=READ_EXPIRE_DAYS)
        result = await self.db.execute(
            select(
                Notification,
                Activity.name.label("reference_name"),
            )
            .outerjoin(Activity, Notification.reference_id == Activity.id)
            .where(
                Notification.user_id == user_id,
                Notification.created_at >= cutoff,
            )
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        rows = result.all()
        return [
            {**n.__dict__, "reference_name": reference_name}
            for n, reference_name in rows
        ]

    async def count_unread(self, user_id: UUID) -> int:
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(days=READ_EXPIRE_DAYS)
        result = await self.db.execute(
            select(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read == False,
                Notification.created_at >= cutoff,
            )
        )
        return len(list(result.scalars().all()))

    async def mark_read(self, notification_id: UUID, user_id: UUID) -> None:
        await self.db.execute(
            update(Notification)
            .where(Notification.id == notification_id, Notification.user_id == user_id)
            .values(is_read=True)
        )
        await self.db.commit()

    async def mark_all_read(self, user_id: UUID) -> None:
        await self.db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .values(is_read=True)
        )
        await self.db.commit()
