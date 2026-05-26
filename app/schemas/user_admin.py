from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class UserListItem(BaseModel):
    id: UUID
    email: str
    display_name: str
    is_active: bool
    roles: list[str]
    created_at: datetime


class UserDetail(BaseModel):
    id: UUID
    email: str
    display_name: str
    is_active: bool
    roles: list[str]
    permissions: list[str]
    created_at: datetime
    updated_at: datetime


class UserRoleUpdate(BaseModel):
    role_ids: list[UUID]


class UserStatusUpdate(BaseModel):
    is_active: bool


class LoginHistoryItem(BaseModel):
    login_id: str
    success: bool
    created_at: datetime


class ActivityActionItem(BaseModel):
    action: str
    target: str | None = None
    created_at: datetime


class UserOverview(BaseModel):
    id: UUID
    email: str
    display_name: str
    is_active: bool
    roles: list[str]
    created_at: datetime
    login_history: list[LoginHistoryItem] = []
    recent_actions: list[ActivityActionItem] = []
