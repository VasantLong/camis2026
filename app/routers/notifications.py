from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationItem(BaseModel):
    id: UUID
    message: str
    is_read: bool
    created_at: str

    model_config = {"from_attributes": True}


def _svc(db=Depends(get_db)) -> NotificationService:
    return NotificationService(db)


@router.get("", response_model=list[NotificationItem])
async def list_notifications(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    svc: NotificationService = Depends(_svc),
):
    rows = await svc.list_for_user(current_user.id, limit)
    return [
        NotificationItem(
            id=r.id,
            message=r.message,
            is_read=r.is_read,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


@router.get("/unread-count")
async def unread_count(
    current_user: User = Depends(get_current_user),
    svc: NotificationService = Depends(_svc),
):
    count = await svc.count_unread(current_user.id)
    return {"count": count}


@router.patch("/{notification_id}/read")
async def mark_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: NotificationService = Depends(_svc),
):
    await svc.mark_read(notification_id, current_user.id)
    return {"message": "ok"}


@router.patch("/read-all")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    svc: NotificationService = Depends(_svc),
):
    await svc.mark_all_read(current_user.id)
    return {"message": "ok"}
