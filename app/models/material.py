import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class KeyMaterial(Base):
    __tablename__ = "key_materials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_qualified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    opinion: Mapped[str | None] = mapped_column(Text)
    upload_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sign_status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="unsigned")
    audit_round: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    activity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("activities.id"), nullable=True, index=True
    )
    material_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    draft_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    current_filled_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("filled_documents.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("activity_id", "material_type"),)


class SecurityPlanMaterial(Base):
    __tablename__ = "security_plan_materials"

    security_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("security_plans.id", ondelete="CASCADE"), primary_key=True
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("key_materials.id", ondelete="CASCADE"), primary_key=True
    )


class MaterialAudit(Base):
    __tablename__ = "material_audits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("key_materials.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    conclusion: Mapped[str | None] = mapped_column(String(32))
    opinion: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
