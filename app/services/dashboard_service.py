from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity, ActivityStatusLog
from app.schemas.activity import ActivityResponse, StatusLogEntry
from app.schemas.dashboard import ActivityDetail, AnomalyEntry, PanelData
from app.services.activity_service import ActivityService


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_panel_data(self) -> PanelData:
        total_result = await self.db.execute(select(func.count(Activity.id)))
        total = total_result.scalar() or 0

        status_rows = (await self.db.execute(
            select(Activity.status, func.count(Activity.id)).group_by(Activity.status)
        )).all()
        by_status = {row[0]: row[1] for row in status_rows}

        approved_result = await self.db.execute(
            select(func.count(Activity.id)).where(
                Activity.status.in_(["审批通过-待举办", "审批通过"])
            )
        )
        approved = approved_result.scalar() or 0
        compliance_rate = approved / total if total > 0 else 0.0

        anomaly_rows = (await self.db.execute(
            select(Activity).where(Activity.status.in_(["已取消", "已延期"])).order_by(
                Activity.updated_at.desc()
            ).limit(10)
        )).scalars().all()

        recent_anomalies = [
            AnomalyEntry(
                activity_id=a.id,
                name=a.name,
                change_status=a.status,
                change_reason=None,
                changed_at=a.updated_at,
            )
            for a in anomaly_rows
        ]

        return PanelData(
            total=total,
            by_status=by_status,
            compliance_rate=round(compliance_rate, 3),
            recent_anomalies=recent_anomalies,
        )

    async def get_activity_detail(self, activity_id: UUID) -> ActivityDetail:
        activity_svc = ActivityService(self.db)
        activity = await activity_svc.get(activity_id)
        history = await activity_svc.get_status_history(activity_id)
        return ActivityDetail(activity=activity, status_history=history)

    async def export_monthly_report(self, month: str) -> str:
        from datetime import datetime, timezone, timedelta
        from io import BytesIO
        from sqlalchemy import text
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        start = datetime(int(month[:4]), int(month[5:7]), 1, tzinfo=timezone(timedelta(hours=8)))
        end = datetime(start.year, start.month + 1, 1, tzinfo=start.tzinfo) if start.month < 12 else datetime(start.year + 1, 1, 1, tzinfo=start.tzinfo)

        result = await self.db.execute(
            text("SELECT count(*) FROM activities WHERE created_at >= :start AND created_at < :end"),
            {"start": start, "end": end},
        )
        count = result.scalar() or 0

        result2 = await self.db.execute(
            text("SELECT status, count(*) FROM activities WHERE created_at >= :start AND created_at < :end GROUP BY status"),
            {"start": start, "end": end},
        )

        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, 780, f"月度合规报告 — {month}")
        c.setFont("Helvetica", 12)
        c.drawString(50, 740, f"本月新增活动: {count}")
        y = 710
        for row in result2.all():
            c.drawString(50, y, f"  {row[0]}: {row[1]}")
            y -= 20
        c.save()
        pdf_bytes = buf.getvalue()

        from app.services.minio_client import upload_file
        path = f"reports/{month}.pdf"
        await upload_file(path, pdf_bytes, "application/pdf")
        return path
