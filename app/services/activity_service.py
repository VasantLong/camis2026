from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity, ActivityStatusLog
from app.schemas.activity import (
    ActivityCreate,
    ActivityListParams,
    ActivityResponse,
    StatusLogEntry,
)
from app.services.workflow_service import WorkflowService

CONFLICT_STATUSES = {"审批通过-待举办", "举办中", "备案材料已交接", "审批通过"}


class ActivityService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _auto_start_if_due(self, activity: Activity) -> bool:
        """如果活动审批通过且已到举办时间，自动转为举办中。"""
        if activity.status != "审批通过-待举办":
            return False
        if activity.estimated_time and activity.estimated_time <= datetime.now(timezone.utc):
            log = ActivityStatusLog(
                activity_id=activity.id,
                from_status="审批通过-待举办",
                to_status="举办中",
                operator_id=activity.owner_id,
                comment="系统自动：已到达预计举办时间",
            )
            self.db.add(log)
            activity.status = "举办中"
            await self.db.commit()
            return True
        return False

    async def create(self, owner_id: UUID, data: ActivityCreate) -> ActivityResponse:
        if data.deadline <= datetime.now(timezone.utc):
            raise ValueError("截止时间不能早于当前时间")

        conflict = await self.db.execute(
            select(Activity).where(
                Activity.location == data.location,
                Activity.estimated_time == data.estimated_time,
                Activity.status.in_(CONFLICT_STATUSES),
            )
        )
        if conflict.scalar_one_or_none():
            raise ValueError("资源冲突：该场地涉及时段已被占用")

        activity = Activity(
            name=data.name,
            type=data.type,
            estimated_time=data.estimated_time,
            location=data.location,
            sponsor=data.sponsor,
            deadline=data.deadline,
            status="待设计方案",
            owner_id=owner_id,
            designer_id=data.designer_id,
        )
        self.db.add(activity)
        await self.db.commit()
        await self.db.refresh(activity)

        log = ActivityStatusLog(
            activity_id=activity.id,
            from_status=None,
            to_status="待设计方案",
            operator_id=owner_id,
        )
        self.db.add(log)
        await self.db.commit()

        from app.services.notification_service import NotificationService
        ns = NotificationService(self.db)
        if data.designer_id:
            await ns.send_reminder(data.designer_id, f"新活动待设计方案: {activity.name}")

        return ActivityResponse.model_validate(activity)

    async def get(self, activity_id: UUID, user_id: UUID | None = None) -> ActivityResponse:
        query = select(Activity).where(Activity.id == activity_id)
        if user_id:
            query = query.where(Activity.owner_id == user_id)
        result = await self.db.execute(query)
        activity = result.scalar_one_or_none()
        if activity is None:
            raise LookupError("活动不存在")
        await self._auto_start_if_due(activity)
        return ActivityResponse.model_validate(activity)

    async def list(self, params: ActivityListParams, user_id: UUID | None = None) -> tuple[list[ActivityResponse], int]:
        query = select(Activity)
        count_query = select(func.count(Activity.id))
        if user_id:
            query = query.where(Activity.owner_id == user_id)
            count_query = count_query.where(Activity.owner_id == user_id)

        if params.status:
            query = query.where(Activity.status == params.status)
            count_query = count_query.where(Activity.status == params.status)
        if params.keyword:
            kw = f"%{params.keyword}%"
            query = query.where(or_(Activity.name.ilike(kw), Activity.sponsor.ilike(kw)))
            count_query = count_query.where(or_(Activity.name.ilike(kw), Activity.sponsor.ilike(kw)))
        if params.date_from:
            query = query.where(Activity.estimated_time >= params.date_from)
            count_query = count_query.where(Activity.estimated_time >= params.date_from)
        if params.date_to:
            query = query.where(Activity.estimated_time <= params.date_to)
            count_query = count_query.where(Activity.estimated_time <= params.date_to)

        total = (await self.db.execute(count_query)).scalar() or 0

        offset = (params.page - 1) * params.size
        rows = (await self.db.execute(
            query.order_by(Activity.created_at.desc()).offset(offset).limit(params.size)
        )).scalars().all()

        for r in rows:
            await self._auto_start_if_due(r)

        return [ActivityResponse.model_validate(r) for r in rows], total

    async def get_status_history(self, activity_id: UUID) -> list[StatusLogEntry]:
        rows = (await self.db.execute(
            select(ActivityStatusLog)
            .where(ActivityStatusLog.activity_id == activity_id)
            .order_by(ActivityStatusLog.created_at)
        )).scalars().all()
        return [StatusLogEntry.model_validate(r) for r in rows]
