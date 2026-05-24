from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.rbac import require_permission
from app.schemas.dashboard import ActivityDetail, MonthlyReportRequest, PanelData
from app.services.dashboard_service import DashboardService
from app.errors import NotFoundError, ValidationError

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
    current_user: User = Depends(get_current_user),
    svc: DashboardService = Depends(_service),
    _perm: None = require_permission("export_report"),
):
    url = await svc.export_monthly_report(body.month)
    return {"report_url": url, "message": "报表生成中，稍后将发送至消息中心"}
