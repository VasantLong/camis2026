from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.activity import ActivityResponse, StatusLogEntry


class AnomalyEntry(BaseModel):
    activity_id: UUID
    name: str
    change_status: str
    change_reason: str | None
    changed_at: datetime


class PanelData(BaseModel):
    total: int
    by_status: dict[str, int]
    compliance_rate: float
    recent_anomalies: list[AnomalyEntry]


class ActivityDetail(BaseModel):
    activity: ActivityResponse
    status_history: list[StatusLogEntry]


class MonthlyReportRequest(BaseModel):
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
