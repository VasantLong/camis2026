from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token
from app.models.activity import Activity, ActivityStatusLog
from app.schemas.activity import ActivityResponse, StatusLogEntry
from app.schemas.dashboard import ActivityDetail, AnomalyEntry, PanelData
from app.services.activity_service import ActivityService
from app.services.report_data import ReportDataService
from app.services.report_renderer import ReportRenderer


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

    async def export_monthly_report(self, month: str, user_id: str, user_email: str) -> str:
        from app.services.minio_client import upload_file
        from app.services.redis_client import get_redis

        data_svc = ReportDataService(self.db)
        data = await data_svc.gather(month)

        data_key = str(uuid4())
        redis = await get_redis()
        if redis is None:
            raise RuntimeError("缓存服务不可用")
        await redis.setex(
            f"report_data:{data_key}", 300,
            json.dumps(asdict(data), ensure_ascii=False),
        )

        token = create_access_token(user_id, user_email)

        renderer = ReportRenderer()
        loop = asyncio.get_event_loop()
        pdf_bytes = await loop.run_in_executor(
            None,
            lambda: renderer.render_pdf(month, data_key, token),
        )

        path = f"reports/{month}.pdf"
        await upload_file(path, pdf_bytes, "application/pdf")
        return path
