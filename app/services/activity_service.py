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

CONFLICT_STATUSES = {"审批通过-待举办", "备案材料已交接", "审批通过"}


class ActivityService:
    def __init__(self, db: AsyncSession):
        self.db = db

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

        return ActivityResponse.model_validate(activity)

    async def get(self, activity_id: UUID) -> ActivityResponse:
        activity = await self.db.get(Activity, activity_id)
        if activity is None:
            raise LookupError("活动不存在")
        return ActivityResponse.model_validate(activity)

    async def list(self, params: ActivityListParams) -> tuple[list[ActivityResponse], int]:
        query = select(Activity)
        count_query = select(func.count(Activity.id))

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

        return [ActivityResponse.model_validate(r) for r in rows], total

    async def get_status_history(self, activity_id: UUID) -> list[StatusLogEntry]:
        rows = (await self.db.execute(
            select(ActivityStatusLog)
            .where(ActivityStatusLog.activity_id == activity_id)
            .order_by(ActivityStatusLog.created_at)
        )).scalars().all()
        return [StatusLogEntry.model_validate(r) for r in rows]
