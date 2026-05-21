from uuid import UUID

from pydantic import BaseModel, Field


class StatusTransition(BaseModel):
    to_status: str
    comment: str | None = None


class RejectRequest(BaseModel):
    reason: str = Field(min_length=1)


class ForceChangeRequest(BaseModel):
    reason: str = Field(min_length=1)
