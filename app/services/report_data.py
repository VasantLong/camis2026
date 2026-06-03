from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone, timedelta
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity, ActivityStatusLog, ImplementationRecord, SecurityPlan
from app.services.workflow_service import TERMINAL_STATUSES


@dataclass
class MonthlyReportData:
    month: str
    generated_at: str
    total: int
    by_status: dict[str, int]
    by_type: dict[str, int]
    daily_creation: list[dict]
    compliance_rate: float
    by_audit_status: dict[str, int]
    anomalies: list[dict]


class ReportDataService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def gather(self, month: str) -> MonthlyReportData:
        tz = timezone(timedelta(hours=8))
        start = datetime(int(month[:4]), int(month[5:7]), 1, tzinfo=tz)
        end = (datetime(start.year, start.month + 1, 1, tzinfo=tz)
               if start.month < 12
               else datetime(start.year + 1, 1, 1, tzinfo=tz))

        total = await self._count(Activity.id, Activity.created_at >= start, Activity.created_at < end)

        status_rows = (await self.db.execute(
            select(Activity.status, func.count(Activity.id))
            .where(Activity.created_at >= start, Activity.created_at < end)
            .group_by(Activity.status)
        )).all()
        by_status = {row[0]: row[1] for row in status_rows}

        type_rows = (await self.db.execute(
            select(Activity.type, func.count(Activity.id))
            .where(Activity.created_at >= start, Activity.created_at < end)
            .group_by(Activity.type)
        )).all()
        by_type = {row[0]: row[1] for row in type_rows}

        daily_rows = (await self.db.execute(
            select(func.date(Activity.created_at), func.count(Activity.id))
            .where(Activity.created_at >= start, Activity.created_at < end)
            .group_by(func.date(Activity.created_at))
            .order_by(func.date(Activity.created_at))
        )).all()
        daily_creation = [{"date": str(row[0]), "count": row[1]} for row in daily_rows]

        approved = await self._count(
            Activity.id,
            Activity.created_at >= start,
            Activity.created_at < end,
            Activity.status.in_({"审批通过-待举办", "审批通过"}),
        )
        concluded = approved + await self._count(
            Activity.id,
            Activity.created_at >= start,
            Activity.created_at < end,
            Activity.status.in_({"不通过/已终止", "已取消", "已延期"}),
        )
        compliance_rate = approved / concluded if concluded else 0.0

        audit_rows = (await self.db.execute(
            select(SecurityPlan.audit_status, func.count(SecurityPlan.id))
            .join(Activity, Activity.id == SecurityPlan.activity_id)
            .where(Activity.created_at >= start, Activity.created_at < end)
            .group_by(SecurityPlan.audit_status)
        )).all()
        by_audit_status = {row[0]: row[1] for row in audit_rows}

        anomaly_rows = (await self.db.execute(
            select(Activity.id, Activity.name, Activity.status, ImplementationRecord.change_reason,
                   ImplementationRecord.archived_at)
            .join(ImplementationRecord, ImplementationRecord.activity_id == Activity.id)
            .where(Activity.created_at >= start, Activity.created_at < end)
            .order_by(ImplementationRecord.archived_at.desc())
        )).all()
        anomalies = [
            {"id": str(r[0]), "name": r[1], "status": r[2], "reason": r[3], "changed_at": str(r[4])}
            for r in anomaly_rows
        ]

        return MonthlyReportData(
            month=month,
            generated_at=datetime.now(tz).isoformat(),
            total=total,
            by_status=by_status,
            by_type=by_type,
            daily_creation=daily_creation,
            compliance_rate=round(compliance_rate, 3),
            by_audit_status=by_audit_status,
            anomalies=anomalies,
        )

    async def _count(self, col, *where_clauses) -> int:
        query = select(func.count(col))
        for clause in where_clauses:
            query = query.where(clause)
        result = await self.db.execute(query)
        return result.scalar() or 0
