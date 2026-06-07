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
        if data.deadline >= data.estimated_time:
            raise ValueError("截止时间必须早于预计举办时间")

        conflict = await self.db.execute(
            select(Activity).where(
                Activity.location == data.location,
                Activity.estimated_time == data.estimated_time,
                Activity.status.in_(CONFLICT_STATUSES),
            )
        )
        if conflict.scalar_one_or_none():
            raise ValueError("资源冲突：该场地涉及时段已被占用")

        if data.designer_id:
            from app.models.user import User
            designer = await self.db.get(User, data.designer_id)
            if designer and not designer.contact_phone:
                raise ValueError("编制人的联系方式为空，请先在个人中心补充联系方式")

        activity = Activity(
            name=data.name,
            type=data.type,
            estimated_time=data.estimated_time,
            location=data.location,
            sponsor=data.sponsor,
            sponsor_contact=data.sponsor_contact,
            sponsor_phone=data.sponsor_phone,
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

        return ActivityResponse.model_validate(activity)

    async def get(self, activity_id: UUID, user_id: UUID | None = None,
                 allowed_statuses: set[str] | None = None) -> ActivityResponse:
        query = select(Activity).where(Activity.id == activity_id)
        if user_id:
            query = query.where(Activity.owner_id == user_id)
        if allowed_statuses:
            query = query.where(Activity.status.in_(allowed_statuses))
        result = await self.db.execute(query)
        activity = result.scalar_one_or_none()
        if activity is None:
            raise LookupError("活动不存在")
        await self._auto_start_if_due(activity)
        return ActivityResponse.model_validate(activity)

    async def list(self, params: ActivityListParams, user_id: UUID | None = None,
                   allowed_statuses: set[str] | None = None,
                   include_terminal: bool = False) -> tuple[list[ActivityResponse], int]:
        query = select(Activity)
        count_query = select(func.count(Activity.id))
        if user_id:
            query = query.where(Activity.owner_id == user_id)
            count_query = count_query.where(Activity.owner_id == user_id)
        if allowed_statuses:
            query = query.where(Activity.status.in_(allowed_statuses))
            count_query = count_query.where(Activity.status.in_(allowed_statuses))
        else:
            if not include_terminal:
                # Roles that see all statuses: exclude terminal from pending tab
                from app.services.workflow_service import TERMINAL_STATUSES
                query = query.where(Activity.status.not_in(TERMINAL_STATUSES))
                count_query = count_query.where(Activity.status.not_in(TERMINAL_STATUSES))

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

    async def list_completed(
        self, user_id: UUID, owner_filter: UUID | None,
        allowed_statuses: set[str] | None, page: int, size: int,
        status_filter: str | None = None, keyword: str | None = None,
        date_from: str | None = None, date_to: str | None = None,
    ) -> tuple[list[ActivityResponse], int]:
        """已完成：当前用户操作过 且 当前状态不在待操作集中"""
        from datetime import datetime

        operated_ids = select(ActivityStatusLog.activity_id.distinct()).where(
            ActivityStatusLog.operator_id == user_id
        ).subquery()

        query = select(Activity).where(Activity.id.in_(operated_ids))
        count_query = select(func.count(Activity.id)).where(Activity.id.in_(operated_ids))

        if allowed_statuses:
            query = query.where(Activity.status.not_in(allowed_statuses))
            count_query = count_query.where(Activity.status.not_in(allowed_statuses))
        else:
            # Roles that see all statuses: "completed" = terminal statuses
            from app.services.workflow_service import TERMINAL_STATUSES
            query = query.where(Activity.status.in_(TERMINAL_STATUSES))
            count_query = count_query.where(Activity.status.in_(TERMINAL_STATUSES))
        if owner_filter:
            query = query.where(Activity.owner_id == owner_filter)
            count_query = count_query.where(Activity.owner_id == owner_filter)
        if status_filter:
            query = query.where(Activity.status == status_filter)
            count_query = count_query.where(Activity.status == status_filter)
        if keyword:
            kw = f"%{keyword}%"
            query = query.where(or_(Activity.name.ilike(kw), Activity.sponsor.ilike(kw)))
            count_query = count_query.where(or_(Activity.name.ilike(kw), Activity.sponsor.ilike(kw)))
        if date_from:
            d = datetime.fromisoformat(date_from) if isinstance(date_from, str) else date_from
            query = query.where(Activity.estimated_time >= d)
            count_query = count_query.where(Activity.estimated_time >= d)
        if date_to:
            d = datetime.fromisoformat(date_to) if isinstance(date_to, str) else date_to
            query = query.where(Activity.estimated_time <= d)
            count_query = count_query.where(Activity.estimated_time <= d)

        total = (await self.db.execute(count_query)).scalar() or 0

        offset = (page - 1) * size
        rows = (await self.db.execute(
            query.order_by(Activity.created_at.desc()).offset(offset).limit(size)
        )).scalars().all()

        for r in rows:
            await self._auto_start_if_due(r)

        return [ActivityResponse.model_validate(r) for r in rows], total

    async def get_status_history(self, activity_id: UUID) -> list[StatusLogEntry]:
        from app.models.user import User
        rows = (await self.db.execute(
            select(ActivityStatusLog, User.display_name.label("operator_name"))
            .outerjoin(User, ActivityStatusLog.operator_id == User.id)
            .where(ActivityStatusLog.activity_id == activity_id)
            .order_by(ActivityStatusLog.created_at)
        )).all()
        return [
            StatusLogEntry(
                id=r.id, from_status=r.from_status, to_status=r.to_status,
                operator_id=r.operator_id, operator_name=operator_name,
                comment=r.comment, created_at=r.created_at,
            )
            for r, operator_name in rows
        ]

    async def get_security_plan(self, activity_id: UUID) -> dict | None:
        from app.models.activity import SecurityPlan
        from app.models.user import User

        result = await self.db.execute(
            select(SecurityPlan).where(SecurityPlan.activity_id == activity_id)
        )
        sp = result.scalar_one_or_none()
        if sp is None:
            return None

        manager_name = None
        if sp.manager_id:
            mgr = await self.db.get(User, sp.manager_id)
            manager_name = mgr.display_name if mgr else None

        return {
            "risk_level": sp.risk_level,
            "audit_status": sp.audit_status,
            "manager_name": manager_name,
            "sign_time": sp.sign_time.isoformat() if sp.sign_time else None,
        }

    async def set_security_risk_level(self, activity_id: UUID, risk_level: str) -> None:
        from app.models.activity import SecurityPlan

        result = await self.db.execute(
            select(SecurityPlan).where(SecurityPlan.activity_id == activity_id)
        )
        sp = result.scalar_one_or_none()
        if sp is None:
            sp = SecurityPlan(activity_id=activity_id, risk_level=risk_level)
            self.db.add(sp)
        else:
            sp.risk_level = risk_level
        await self.db.flush()
        await self.db.commit()
