from __future__ import annotations

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


class NotificationService:
    async def send_reminder(self, user_id: UUID, message: str, channel: str = "system") -> None:
        logger.info("notification user=%s channel=%s message=%s", user_id, channel, message)

    async def notify_role(self, role_name: str, message: str) -> None:
        logger.info("notification role=%s message=%s", role_name, message)

    async def check_overdue(self, activity_id: UUID) -> None:
        logger.info("overdue check activity=%s", activity_id)
