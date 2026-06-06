import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class FilledDocument(Base):
    __tablename__ = "filled_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("activities.id", ondelete="CASCADE"), nullable=False
    )
    template_type: Mapped[str] = mapped_column(String(64), nullable=False)
    version_number: Mapped[int] = mapped_column(nullable=False)
    data_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    minio_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    pdf_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    template_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    generated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("activity_id", "template_type", "version_number"),
        Index("idx_filled_documents_activity", "activity_id"),
    )
