import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.database import get_db
from app.deps import get_current_user
from app.models.document import Document
from app.models.user import User
from app.services.minio_client import get_presigned_url, upload_file
from app.services.redis_client import get_redis

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    id: str
    project_id: str
    uploader_id: str
    filename: str
    minio_path: str
    file_size: int
    content_type: str
    tags: list[str] | None


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile,
    project_id: str = Form(...),
    tags: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    content = await file.read()
    ext = Path(file.filename).suffix.lstrip(".").lower() if file.filename else "bin"
    minio_path = f"projects/{project_id}/{uuid.uuid4()}.{ext}"

    await upload_file(minio_path, content, file.content_type or "application/octet-stream")

    doc = Document(
        project_id=project_id,
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
    await redis.delete(f"project:{project_id}:docs")

    return DocumentResponse(
        id=str(doc.id),
        project_id=str(doc.project_id),
        uploader_id=str(doc.uploader_id),
        filename=doc.filename,
        minio_path=doc.minio_path,
        file_size=doc.file_size,
        content_type=doc.content_type,
        tags=doc.tags,
    )


@router.get("/project/{project_id}", response_model=list[DocumentResponse])
async def list_documents(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    redis = await get_redis()
    cache_key = f"project:{project_id}:docs"
    cached = await redis.get(cache_key)
    if cached:
        return [DocumentResponse(**item) for item in json.loads(cached)]

    result = await db.execute(
        select(Document).where(Document.project_id == project_id).order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    items = [
        DocumentResponse(
            id=str(d.id),
            project_id=str(d.project_id),
            uploader_id=str(d.uploader_id),
            filename=d.filename,
            minio_path=d.minio_path,
            file_size=d.file_size,
            content_type=d.content_type,
            tags=d.tags,
        )
        for d in docs
    ]
    await redis.set(cache_key, json.dumps([item.model_dump() for item in items]), ex=300)
    return items


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
            "project_id": str(doc.project_id),
            "filename": doc.filename,
            "minio_path": doc.minio_path,
        }
        await redis.set(f"doc:{doc_id}", json.dumps(meta), ex=1800)

    url = await get_presigned_url(meta["minio_path"])
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)
