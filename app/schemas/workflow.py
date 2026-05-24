from uuid import UUID

from pydantic import BaseModel, Field


class StatusTransition(BaseModel):
    to_status: str
    comment: str | None = Field(default=None, max_length=2000)


class RejectRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class ForceChangeRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
