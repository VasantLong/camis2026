from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ActivityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: str = Field(min_length=1, max_length=128)
    estimated_time: datetime
    location: str = Field(min_length=1, max_length=256)
    sponsor: str = Field(min_length=1, max_length=255)
    sponsor_contact: str = Field(min_length=1, max_length=128)
    sponsor_phone: str = Field(min_length=1, max_length=64)
    deadline: datetime
    designer_id: UUID | None = None


class ActivityResponse(BaseModel):
    id: UUID
    name: str
    type: str
    estimated_time: datetime
    location: str
    sponsor: str
    sponsor_contact: str | None = None
    sponsor_phone: str | None = None
    deadline: datetime
    status: str
    owner_id: UUID
    designer_id: UUID | None = None
    designer_name: str | None = None
    designer_phone: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ActivityPaginatedResponse(BaseModel):
    items: list[ActivityResponse]
    total: int


class ActivityListParams(BaseModel):
    status: str | None = None
    keyword: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class StatusLogEntry(BaseModel):
    id: UUID
    from_status: str | None
    to_status: str
    operator_id: UUID
    comment: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
