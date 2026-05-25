from __future__ import annotations

import uuid
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.services.minio_client import get_presigned_url, upload_file

MAGIC_BYTES: dict[str, bytes] = {
    ".pdf": b"%PDF",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".png": b"\x89PNG",
    ".doc": b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",
    ".docx": b"PK\x03\x04",
}

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}
ALLOWED_MIMES = {
    "application/pdf",
    "image/jpeg", "image/png",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_FILE_SIZE = 50 * 1024 * 1024


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def validate(self, filename: str | None, content_type: str | None, size: int | None, content: bytes | None = None) -> None:
        ext = Path(filename).suffix.lower() if filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {ext}")
        if content_type and content_type not in ALLOWED_MIMES:
            raise ValueError(f"不支持的文件类型: {content_type}")
        if size and size > MAX_FILE_SIZE:
            raise ValueError("文件过大，最大允许 50MB")
        if content and ext in MAGIC_BYTES:
            magic = MAGIC_BYTES[ext]
            if not content.startswith(magic):
                raise ValueError(f"文件内容与扩展名不匹配: {ext}")

    async def upload(
        self, activity_id: UUID, uploader_id: UUID,
        filename: str, content: bytes, content_type: str, tags: list[str] | None = None,
    ) -> Document:
        ext = Path(filename).suffix.lstrip(".").lower() or "bin"
        minio_path = f"activities/{activity_id}/{uuid.uuid4()}.{ext}"
        await upload_file(minio_path, content, content_type)

        doc = Document(
            activity_id=activity_id,
            uploader_id=uploader_id,
            filename=filename or "unnamed",
            minio_path=minio_path,
            file_size=len(content),
            content_type=content_type,
            tags=tags,
        )
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def get_presigned_download_url(self, doc_id: UUID, inline: bool = False) -> str:
        doc = await self.db.get(Document, doc_id)
        if doc is None:
            raise LookupError("文档不存在")
        return await get_presigned_url(doc.minio_path, filename=doc.filename, inline=inline)

    async def list_by_activity(self, activity_id: UUID) -> list[Document]:
        result = await self.db.execute(
            select(Document).where(Document.activity_id == activity_id).order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())
