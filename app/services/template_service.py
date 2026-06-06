from __future__ import annotations

import hashlib
import logging
import subprocess
import tempfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

from docxtpl import DocxTemplate
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity, ActivityPlan, SecurityPlan
from app.models.material import KeyMaterial
from app.models.template import FilledDocument
from app.models.document import Document
from app.services import minio_client
from app.templates import (
    FORM_MODELS, SCHEMAS, TEMPLATES_ROOT, TEMPLATE_DISPLAY_NAMES, TEMPLATE_ENTITY_MAP,
)
from app.templates.security_plan.schema import CONDITIONAL_FIELDS

logger = logging.getLogger("camis.template")

MINIO_BUCKET = "camis2026"


class TemplateService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # schema + draft
    # ------------------------------------------------------------------

    async def get_schema(
        self, template_type: str, activity_id: UUID, material_type: str | None = None,
    ) -> dict:
        schema = SCHEMAS[template_type].copy()
        schema["template_type"] = template_type

        entity = await self._get_entity(template_type, activity_id, material_type)
        draft_data = getattr(entity, "draft_data", None) if entity else None
        current_fd_id = getattr(entity, "current_filled_document_id", None) if entity else None

        schema["has_draft"] = draft_data is not None
        schema["draft_data"] = draft_data

        current_version = None
        if current_fd_id:
            fd = await self.db.get(FilledDocument, current_fd_id)
            current_version = fd.version_number if fd else None
        schema["current_version"] = current_version

        # security plan: expose risk_level for conditional field filtering
        if template_type == "security_plan":
            risk_level = getattr(entity, "risk_level", None) if entity else None
            schema["risk_level"] = risk_level

        return schema

    async def save_draft(
        self, template_type: str, activity_id: UUID, data: dict, user_id: UUID,
        material_type: str | None = None,
    ) -> None:
        entity = await self._get_or_create_entity(template_type, activity_id, user_id, material_type)
        entity.draft_data = data
        await self.db.flush()
        await self.db.commit()
        logger.info("draft saved type=%s activity=%s", template_type, activity_id)

    # ------------------------------------------------------------------
    # generate
    # ------------------------------------------------------------------

    async def generate(
        self, template_type: str, activity_id: UUID, data: dict, user_id: UUID,
        material_type: str | None = None,
    ) -> dict:
        entity = await self._get_or_create_entity(template_type, activity_id, user_id, material_type)

        # resolve version
        version_number = await self._next_version(activity_id, template_type)
        risk_level = getattr(entity, "risk_level", None)

        # render DOCX
        docx_bytes = await self._render_docx(template_type, data, risk_level)
        template_hash = hashlib.sha256(
            (TEMPLATES_ROOT / template_type / "template.docx").read_bytes()
        ).hexdigest()

        # upload DOCX
        minio_path = f"filled_documents/{activity_id}/{template_type}/v{version_number}.docx"
        await minio_client.upload_file(minio_path, docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

        # convert to PDF
        pdf_path = None
        pdf_preview_url = None
        try:
            pdf_bytes = await self._docx_to_pdf(docx_bytes)
            pdf_path = f"filled_documents/{activity_id}/{template_type}/v{version_number}.pdf"
            await minio_client.upload_file(pdf_path, pdf_bytes, "application/pdf")
            pdf_preview_url = await minio_client.get_presigned_url(pdf_path, inline=True)
        except Exception:
            logger.warning("pdf conversion failed type=%s activity=%s", template_type, activity_id)

        # create FilledDocument
        fd = FilledDocument(
            activity_id=activity_id,
            template_type=template_type,
            version_number=version_number,
            data_snapshot=data,
            minio_path=minio_path,
            pdf_path=pdf_path,
            template_hash=template_hash,
            generated_by=user_id,
        )
        self.db.add(fd)
        await self.db.flush()

        # link to entity
        entity.current_filled_document_id = fd.id
        entity.draft_data = None
        entity.submit_time = datetime.now(timezone.utc)
        await self.db.flush()

        # workflow trigger for activity plan (also commits)
        if template_type == "activity_plan":
            activity = await self.db.get(Activity, activity_id)
            if activity and activity.status == "待设计方案":
                from app.services.workflow_service import WorkflowService
                from app.services.notification_service import NotificationService
                ws = WorkflowService(self.db, NotificationService(self.db))
                await ws.transition(
                    activity_id, "待安保方案设计",
                    await self.db.get(
                        __import__("app.models.user", fromlist=["User"]).User, user_id,
                    ),
                )

        logger.info(
            "generated type=%s activity=%s v%d",
            template_type, activity_id, version_number,
        )
        return {
            "id": fd.id,
            "template_type": fd.template_type,
            "version_number": fd.version_number,
            "minio_path": fd.minio_path,
            "pdf_preview_url": pdf_preview_url,
            "created_at": fd.created_at.isoformat() if fd.created_at else None,
        }

    # ------------------------------------------------------------------
    # versions
    # ------------------------------------------------------------------

    async def get_versions(
        self, template_type: str, activity_id: UUID, material_type: str | None = None,
    ) -> list[dict]:
        result = await self.db.execute(
            select(FilledDocument)
            .where(
                FilledDocument.activity_id == activity_id,
                FilledDocument.template_type == template_type,
            )
            .order_by(FilledDocument.version_number.desc())
        )
        rows = result.scalars().all()

        entity = await self._get_entity(template_type, activity_id, material_type)
        current_id = getattr(entity, "current_filled_document_id", None) if entity else None

        return [
            {
                "id": str(r.id),
                "version_number": r.version_number,
                "generated_by": str(r.generated_by),
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "is_current": r.id == current_id,
            }
            for r in rows
        ]

    async def get_version_detail(
        self, template_type: str, activity_id: UUID, version_number: int,
        material_type: str | None = None,
    ) -> dict | None:
        result = await self.db.execute(
            select(FilledDocument).where(
                FilledDocument.activity_id == activity_id,
                FilledDocument.template_type == template_type,
                FilledDocument.version_number == version_number,
            )
        )
        fd = result.scalar_one_or_none()
        if not fd:
            return None

        entity = await self._get_entity(template_type, activity_id, material_type)
        current_id = getattr(entity, "current_filled_document_id", None) if entity else None

        return {
            "id": str(fd.id),
            "version_number": fd.version_number,
            "data_snapshot": fd.data_snapshot,
            "template_hash": fd.template_hash,
            "generated_by": str(fd.generated_by),
            "created_at": fd.created_at.isoformat() if fd.created_at else None,
            "is_current": fd.id == current_id,
        }

    async def get_version_preview_url(
        self, template_type: str, activity_id: UUID, version_number: int,
    ) -> str | None:
        fd = await self._get_version_row(activity_id, template_type, version_number)
        if not fd or not fd.pdf_path:
            return None
        return await minio_client.get_presigned_url(fd.pdf_path, inline=True)

    async def get_version_diff(
        self, template_type: str, activity_id: UUID, v1: int, v2: int,
        material_type: str | None = None,
    ) -> list[dict]:
        fd1 = await self._get_version_row(activity_id, template_type, v1)
        fd2 = await self._get_version_row(activity_id, template_type, v2)
        if not fd1 or not fd2:
            return []

        s1 = fd1.data_snapshot or {}
        s2 = fd2.data_snapshot or {}
        all_keys = set(s1) | set(s2)
        diffs = []
        for key in sorted(all_keys):
            old_val = s1.get(key)
            new_val = s2.get(key)
            if old_val != new_val:
                diffs.append({"field": key, "old": old_val, "new": new_val})
        return diffs

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    async def _render_docx(
        self, template_type: str, data: dict, risk_level: str | None,
    ) -> bytes:
        from docxtpl import InlineImage
        from docx.shared import Mm

        template_path = TEMPLATES_ROOT / template_type / "template.docx"
        if not template_path.exists():
            raise FileNotFoundError(f"template not found: {template_path}")

        doc = DocxTemplate(template_path)
        context = dict(data)

        # detect signature fields and embed images if value is a minio_path
        for field_name, value in list(context.items()):
            if "signature" in field_name and isinstance(value, str) and value:
                try:
                    img_bytes = minio_client.minio_client.get_object(
                        minio_client._bucket, value,
                    ).read()
                    context[field_name] = InlineImage(doc, BytesIO(img_bytes), width=Mm(30))
                except Exception:
                    pass  # fall back to text rendering

        doc.render(context)
        buf = BytesIO()
        doc.save(buf)
        return buf.getvalue()

    async def _docx_to_pdf(self, docx_bytes: bytes) -> bytes:
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tf_in:
            tf_in.write(docx_bytes)
            in_path = tf_in.name

        out_dir = tempfile.mkdtemp()
        try:
            subprocess.run(
                ["soffice", "--headless", "--convert-to", "pdf", "--outdir", out_dir, in_path],
                check=True, timeout=60, capture_output=True,
            )
            pdf_name = Path(in_path).stem + ".pdf"
            pdf_path = Path(out_dir) / pdf_name
            if not pdf_path.exists():
                raise RuntimeError("pdf not produced by soffice")
            return pdf_path.read_bytes()
        finally:
            Path(in_path).unlink(missing_ok=True)
            import shutil
            shutil.rmtree(out_dir, ignore_errors=True)

    async def _next_version(self, activity_id: UUID, template_type: str) -> int:
        result = await self.db.execute(
            select(func.max(FilledDocument.version_number)).where(
                FilledDocument.activity_id == activity_id,
                FilledDocument.template_type == template_type,
            )
        )
        current_max = result.scalar() or 0
        return current_max + 1

    async def _get_version_row(
        self, activity_id: UUID, template_type: str, version_number: int,
    ) -> FilledDocument | None:
        result = await self.db.execute(
            select(FilledDocument).where(
                FilledDocument.activity_id == activity_id,
                FilledDocument.template_type == template_type,
                FilledDocument.version_number == version_number,
            )
        )
        return result.scalar_one_or_none()

    async def _get_entity(
        self, template_type: str, activity_id: UUID, material_type: str | None = None,
    ):
        entity_type = TEMPLATE_ENTITY_MAP[template_type]
        if entity_type == "activity_plan":
            result = await self.db.execute(
                select(ActivityPlan).where(ActivityPlan.activity_id == activity_id)
            )
            return result.scalar_one_or_none()
        elif entity_type == "security_plan":
            result = await self.db.execute(
                select(SecurityPlan).where(SecurityPlan.activity_id == activity_id)
            )
            return result.scalar_one_or_none()
        elif entity_type == "key_material":
            if not material_type:
                raise ValueError("material_type required for key_material templates")
            result = await self.db.execute(
                select(KeyMaterial).where(
                    KeyMaterial.activity_id == activity_id,
                    KeyMaterial.material_type == material_type,
                )
            )
            return result.scalar_one_or_none()
        return None

    async def _get_or_create_entity(
        self, template_type: str, activity_id: UUID, user_id: UUID,
        material_type: str | None = None,
    ):
        entity_type = TEMPLATE_ENTITY_MAP[template_type]
        if entity_type == "activity_plan":
            result = await self.db.execute(
                select(ActivityPlan).where(ActivityPlan.activity_id == activity_id)
            )
            entity = result.scalar_one_or_none()
            if not entity:
                entity = ActivityPlan(activity_id=activity_id, designer_id=user_id)
                self.db.add(entity)
                await self.db.flush()
            return entity
        elif entity_type == "security_plan":
            result = await self.db.execute(
                select(SecurityPlan).where(SecurityPlan.activity_id == activity_id)
            )
            entity = result.scalar_one_or_none()
            if not entity:
                entity = SecurityPlan(activity_id=activity_id)
                self.db.add(entity)
                await self.db.flush()
            return entity
        elif entity_type == "key_material":
            if not material_type:
                raise ValueError("material_type required for key_material templates")
            result = await self.db.execute(
                select(KeyMaterial).where(
                    KeyMaterial.activity_id == activity_id,
                    KeyMaterial.material_type == material_type,
                )
            )
            entity = result.scalar_one_or_none()
            if not entity:
                display_name = TEMPLATE_DISPLAY_NAMES.get(template_type, template_type)
                entity = KeyMaterial(
                    name=display_name,
                    activity_id=activity_id,
                    material_type=material_type,
                )
                self.db.add(entity)
                await self.db.flush()
            return entity
        raise ValueError(f"unknown entity type: {entity_type}")
