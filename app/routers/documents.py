import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.database import get_db
from app.deps import get_current_user
from app.models.activity import Activity
from app.models.document import Document
from app.models.user import User
from app.services.minio_client import get_presigned_url, upload_file
from app.services.redis_client import get_redis

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}
ALLOWED_MIMES = {
    "application/pdf",
    "image/jpeg", "image/png",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

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


def _to_response(d: Document) -> DocumentResponse:
    return DocumentResponse(
        id=str(d.id),
        activity_id=str(d.activity_id) if d.activity_id else None,
        uploader_id=str(d.uploader_id),
        filename=d.filename,
        minio_path=d.minio_path,
        file_size=d.file_size,
        content_type=d.content_type,
        tags=d.tags,
    )


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile,
    activity_id: str = Form(...),
    tags: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    activity = await db.get(Activity, activity_id)
    if activity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="活动不存在")

    # 文件格式/大小校验
    ext = Path(file.filename).suffix.lower() if file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件格式: {ext}，允许: {', '.join(ALLOWED_EXTENSIONS)}")
    if file.content_type and file.content_type not in ALLOWED_MIMES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {file.content_type}")
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件过大，最大允许 50MB")

    content = await file.read()
    ext = Path(file.filename).suffix.lstrip(".").lower() if file.filename else "bin"
    minio_path = f"activities/{activity_id}/{uuid.uuid4()}.{ext}"

    await upload_file(minio_path, content, file.content_type or "application/octet-stream")

    doc = Document(
        activity_id=activity_id,
        uploader_id=current_user.id,
        filename=file.filename or "unnamed",
        minio_path=minio_path,
        file_size=len(content),
        content_type=file.content_type or "application/octet-stream",
        tags=tags.split(",") if tags else None,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    redis = await get_redis()
    await redis.delete(f"activity:{activity_id}:docs")

    return _to_response(doc)


@router.get("/{doc_id}")
async def download_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    redis = await get_redis()
    cached = await redis.get(f"doc:{doc_id}")
    if cached:
        meta = json.loads(cached)
    else:
        doc = await db.get(Document, doc_id)
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        meta = {
            "id": str(doc.id),
            "activity_id": str(doc.activity_id) if doc.activity_id else None,
            "filename": doc.filename,
            "minio_path": doc.minio_path,
        }
        await redis.set(f"doc:{doc_id}", json.dumps(meta), ex=1800)

    url = await get_presigned_url(meta["minio_path"])
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)
