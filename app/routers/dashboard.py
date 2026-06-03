import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.database import async_session, get_db
from app.deps import get_current_user
from app.models.user import User
from app.rbac import require_permission
from app.schemas.dashboard import ActivityDetail, MonthlyReportRequest, PanelData
from app.services.dashboard_service import DashboardService
from app.services.notification_service import NotificationService
from app.services.redis_client import get_redis
from app.errors import NotFoundError, ValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _service(db=Depends(get_db)) -> DashboardService:
    return DashboardService(db)


@router.get("", response_model=PanelData)
async def get_panel(
    current_user: User = Depends(get_current_user),
    svc: DashboardService = Depends(_service),
    _perm: None = require_permission("view_dashboard"),
):
    return await svc.get_panel_data()


@router.get("/activities/{activity_id}", response_model=ActivityDetail)
async def get_activity_detail(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: DashboardService = Depends(_service),
    _perm: None = require_permission("view_dashboard"),
):
    try:
        return await svc.get_activity_detail(activity_id)
    except LookupError as e:
        raise NotFoundError(str(e))


@router.post("/reports/monthly")
async def export_monthly_report(
    body: MonthlyReportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    svc: DashboardService = Depends(_service),
    _perm: None = require_permission("export_report"),
):
    user_id = current_user.id
    user_email = current_user.email
    month = body.month

    async def _generate_and_notify():
        async with async_session() as db:
            try:
                report_svc = DashboardService(db)
                url = await report_svc.export_monthly_report(month, str(user_id), user_email)
                notif_svc = NotificationService(db)
                await notif_svc.send_reminder(
                    user_id,
                    f"月度报告 {month} 已生成，点击下载",
                    reference_type="report",
                )
                logger.info("report generated month=%s user=%s url=%s", month, user_id, url)
            except Exception:
                logger.exception("report generation failed month=%s user=%s", month, user_id)

    background_tasks.add_task(_generate_and_notify)
    return {"message": "报表生成中，生成完毕后将推送至消息中心"}


@router.get("/reports/{month}")
async def download_report(
    month: str,
    current_user: User = Depends(get_current_user),
    _perm: None = require_permission("export_report"),
):
    from app.services.minio_client import minio_client
    from app.config import settings
    try:
        obj = minio_client.get_object(settings.minio_bucket, f"reports/{month}.pdf")
    except Exception:
        raise NotFoundError("报表不存在或尚未生成")
    return StreamingResponse(
        obj.stream(amt=64 * 1024),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=report-{month}.pdf"},
    )


@router.get("/reports/{month}/data")
async def get_report_data(
    month: str,
    data_key: str = Query(...),
    current_user: User = Depends(get_current_user),
    _perm: None = require_permission("export_report"),
):
    redis = await get_redis()
    if redis is None:
        raise HTTPException(status_code=503, detail="缓存服务不可用")
    cached = await redis.get(f"report_data:{data_key}")
    if not cached:
        raise NotFoundError("报表数据已过期，请重新生成")
    import json
    return json.loads(cached)
