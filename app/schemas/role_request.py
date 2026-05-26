from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RoleRequestCreate(BaseModel):
    role_id: UUID


class RoleRequestReview(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    comment: str | None = Field(default=None, max_length=1024)


class RoleRequestResponse(BaseModel):
    id: UUID
    user_id: UUID
    role_id: UUID
    role_name: str
    status: str
    comment: str | None = None
    created_at: datetime
    reviewer_id: UUID | None = None
    reviewed_at: datetime | None = None
    user_email: str | None = None
    user_display_name: str | None = None
