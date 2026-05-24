from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

import json

from sqlalchemy import select

from app.database import get_db
from app.deps import get_current_user
from app.models.document import Document
from app.models.user import User
from app.rbac import require_permission
from app.schemas.activity import ActivityCreate, ActivityListParams, ActivityResponse, StatusLogEntry
from app.services.activity_service import ActivityService
from app.services.redis_client import get_redis

router = APIRouter(prefix="/activities", tags=["activities"])


def _service(db=Depends(get_db)) -> ActivityService:
    return ActivityService(db)


@router.post("", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
async def create_activity(
    body: ActivityCreate,
    current_user: User = Depends(get_current_user),
    svc: ActivityService = Depends(_service),
    _perm: None = require_permission("create_activity"),
):
    try:
        return await svc.create(current_user.id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT if "冲突" in str(e) else status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=list[ActivityResponse])
async def list_activities(
    status_filter: str | None = Query(None, alias="status"),
    keyword: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    svc: ActivityService = Depends(_service),
    _perm: None = require_permission("view_owned_activity"),
):
    from datetime import datetime

    params = ActivityListParams(
        status=status_filter,
        keyword=keyword,
        date_from=datetime.fromisoformat(date_from) if date_from else None,
        date_to=datetime.fromisoformat(date_to) if date_to else None,
        page=page,
        size=size,
    )
    items, _ = await svc.list(params, current_user.id)
    return items


@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: ActivityService = Depends(_service),
    _perm: None = require_permission("view_owned_activity"),
):
    try:
        return await svc.get(activity_id, current_user.id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{activity_id}/history", response_model=list[StatusLogEntry])
async def get_status_history(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: ActivityService = Depends(_service),
    _perm: None = require_permission("view_owned_activity"),
):
    return await svc.get_status_history(activity_id)


@router.get("/{activity_id}/documents")
async def list_activity_documents(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
    _perm: None = require_permission("view_owned_activity"),
):
    redis = await get_redis()
    cache_key = f"activity:{activity_id}:docs"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    result = await db.execute(
        select(Document).where(Document.activity_id == activity_id).order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    items = [
        {
            "id": str(d.id),
            "activity_id": str(d.activity_id) if d.activity_id else None,
            "uploader_id": str(d.uploader_id),
            "filename": d.filename,
            "minio_path": d.minio_path,
            "file_size": d.file_size,
            "content_type": d.content_type,
            "tags": d.tags,
        }
        for d in docs
    ]
    await redis.set(cache_key, json.dumps(items), ex=300)
    return items
