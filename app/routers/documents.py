import json
import logging

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile, status

logger = logging.getLogger("camis.redis")
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.database import get_db
from app.deps import get_current_user
from app.models.activity import Activity
from app.models.user import User
from app.rbac import require_permission
from app.services.document_service import DocumentService
from app.services.redis_client import get_redis

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    id: str
    activity_id: str | None
    uploader_id: str
    filename: str
    minio_path: str
    file_size: int
    content_type: str
    tags: list[str] | None


def _to_response(doc) -> DocumentResponse:
    return DocumentResponse(
        id=str(doc.id),
        activity_id=str(doc.activity_id) if doc.activity_id else None,
        uploader_id=str(doc.uploader_id),
        filename=doc.filename,
        minio_path=doc.minio_path,
        file_size=doc.file_size,
        content_type=doc.content_type,
        tags=doc.tags,
    )


def _service(db=Depends(get_db)) -> DocumentService:
    return DocumentService(db)


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile,
    activity_id: str = Form(...),
    tags: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    svc: DocumentService = Depends(_service),
    db=Depends(get_db),
    _perm: None = require_permission("upload_document"),
):
    activity = await db.get(Activity, activity_id)
    if activity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="活动不存在")

    content = await file.read()
    try:
        svc.validate(file.filename, file.content_type, file.size, content)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    doc = await svc.upload(
        activity_id, current_user.id, file.filename or "unnamed",
        content, file.content_type or "application/octet-stream",
        tags=tags.split(",") if tags else None,
    )

    redis = await get_redis()
    if redis:
        logger.info("redis DEL key=activity:%s:docs", activity_id)
        await redis.delete(f"activity:{activity_id}:docs")

    return _to_response(doc)


class PresignedUrlResponse(BaseModel):
    url: str
    filename: str


@router.get("/{doc_id}/url", response_model=PresignedUrlResponse)
async def get_download_url(
    doc_id: str,
    inline: bool = Query(False),
    current_user: User = Depends(get_current_user),
    svc: DocumentService = Depends(_service),
):
    from app.models.document import Document as DocModel

    d = await svc.db.get(DocModel, doc_id)
    if d is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    url = await svc.get_presigned_download_url(doc_id, inline=inline)
    return PresignedUrlResponse(url=url, filename=d.filename)


@router.get("/{doc_id}")
async def download_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    svc: DocumentService = Depends(_service),
):
    from app.models.document import Document as DocModel

    redis = await get_redis()
    meta = None
    if redis:
        cached = await redis.get(f"doc:{doc_id}")
        logger.info("redis GET key=doc:%s hit=%s", doc_id, cached is not None)
        if cached:
            meta = json.loads(cached)
    if meta is None:
        d = await svc.db.get(DocModel, doc_id)
        if d is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        meta = {
            "id": str(d.id),
            "activity_id": str(d.activity_id) if d.activity_id else None,
            "filename": d.filename,
            "minio_path": d.minio_path,
        }
        if redis:
            logger.info("redis SET key=doc:%s ex=1800", doc_id)
            await redis.set(f"doc:{doc_id}", json.dumps(meta), ex=1800)

    url = await svc.get_presigned_download_url(doc_id)
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)
