import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.database import get_db
from app.deps import get_current_user
from app.models.document import Document
from app.models.user import User
from app.services.minio_client import upload_file
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
