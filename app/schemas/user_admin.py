from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class UserListItem(BaseModel):
    id: UUID
    username: str
    email: str
    display_name: str | None = None
    is_active: bool
    roles: list[str]
    created_at: datetime


class UserDetail(BaseModel):
    id: UUID
    username: str
    email: str
    display_name: str | None = None
    is_active: bool
    roles: list[str]
    permissions: list[str]
    created_at: datetime
    updated_at: datetime


class UserRoleUpdate(BaseModel):
    role_ids: list[UUID]


class UserStatusUpdate(BaseModel):
    is_active: bool
