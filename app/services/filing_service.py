from __future__ import annotations

import logging
import tempfile
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.models.filing import FilingDoc, FilingDocMaterial
from app.models.material import KeyMaterial, MaterialAudit
from app.models.template import FilledDocument
from app.models.user import User
from app.schemas.filing import FilingPackResult, MaterialValidation
from app.services import minio_client

# These tables are created by init-scripts/02-activity-tables.sql but ORM models
# not yet defined. We'll use raw SQL for the join queries until models are added.
logger = logging.getLogger("camis.filing")

JOIN_QUERY = """
SELECT km.id, km.name, km.is_qualified, km.opinion, km.sign_status, km.audit_round
FROM key_materials km
JOIN security_plan_materials spm ON spm.material_id = km.id
JOIN security_plans sp ON sp.id = spm.security_plan_id
WHERE sp.activity_id = :activity_id
UNION
SELECT km.id, km.name, km.is_qualified, km.opinion, km.sign_status, km.audit_round
FROM key_materials km
JOIN filing_doc_materials fdm ON fdm.material_id = km.id
JOIN filing_docs fd ON fd.id = fdm.filing_doc_id
WHERE fd.activity_id = :activity_id
UNION
SELECT km.id, km.name, km.is_qualified, km.opinion, km.sign_status, km.audit_round
FROM key_materials km
WHERE km.activity_id = :activity_id
"""


def _generate_pdf(activity_name: str, materials: list[MaterialValidation]) -> bytes:
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 780, f"备案材料包: {activity_name}")
    c.setFont("Helvetica", 10)
    y = 740
    for i, m in enumerate(materials, 1):
        status = "合格" if m.is_qualified else "待审核"
        sig = "已签" if m.has_signature else "未签"
        c.drawString(50, y, f"{i}. {m.name} — {status} — {sig}")
        y -= 18
        if y < 50:
            c.showPage()
            y = 780
    c.save()
    return buf.getvalue()


class FilingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def validate_materials(self, activity_id: UUID) -> list[MaterialValidation]:
        activity = await self.db.get(Activity, activity_id)
        if activity is None:
            raise LookupError("活动不存在")

        result = await self.db.execute(
            text(JOIN_QUERY), {"activity_id": activity_id}
        )
        rows = result.fetchall()

        validations: list[MaterialValidation] = []
        for row in rows:
            issues: list[str] = []
            has_sig = getattr(row, "sign_status", "unsigned") == "signed"
            logger.info("validate_materials: name=%s sign_status=%s has_sig=%s id=%s", row.name, getattr(row, "sign_status", "?"), has_sig, row.id)
            if not has_sig:
                issues.append("材料未签署")
            validations.append(MaterialValidation(
                material_id=row.id,
                name=row.name,
                is_qualified=row.is_qualified,
                has_signature=has_sig,
                issues=issues,
            ))
        return validations

    async def pack_materials(self, activity_id: UUID) -> FilingPackResult:
        validations = await self.validate_materials(activity_id)
        qualified = [v for v in validations if not v.issues]
        all_ok = len(qualified) == len(validations) and len(validations) > 0

        doc = await self.db.execute(
            select(FilingDoc).where(FilingDoc.activity_id == activity_id)
        )
        filing_doc = doc.scalar_one_or_none()

        if filing_doc is None:
            filing_doc = FilingDoc(
                activity_id=activity_id,
                is_qualified=all_ok,
                generated_at=datetime.now(timezone.utc) if all_ok else None,
            )
            self.db.add(filing_doc)
            await self.db.commit()
            await self.db.refresh(filing_doc)
        else:
            filing_doc.is_qualified = all_ok
            if all_ok:
                filing_doc.generated_at = datetime.now(timezone.utc)
            await self.db.commit()

        if not all_ok:
            return FilingPackResult(
                filing_doc_id=filing_doc.id,
                materials_count=len(validations),
                qualified_count=len(qualified),
                missing_signatures=[v.name for v in validations if v.issues],
                ready=False,
            )

        # Link materials to filing doc
        await self._link_materials_to_filing(activity_id, filing_doc.id, validations)

        activity = await self.db.get(Activity, activity_id)

        # Generate simple PDF listing (existing behavior)
        pdf_bytes = _generate_pdf(activity.name if activity else "未知活动", validations)
        pdf_path = f"filings/{activity_id}/pack_{filing_doc.id}.pdf"
        await minio_client.upload_file(pdf_path, pdf_bytes, "application/pdf")

        # Generate ZIP pack with DOCX files
        try:
            zip_bytes = await self._build_zip_pack(
                activity.name if activity else "未知活动", activity_id,
            )
            safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in (activity.name if activity else "未知活动")).strip()[:30]
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
            old_zip = filing_doc.pack_url
            zip_path = f"filings/{activity_id}/{safe_name}_备案材料包_{ts}.zip"
            await minio_client.upload_file(zip_path, zip_bytes, "application/zip")
            filing_doc.pack_url = zip_path
            await self.db.commit()
            if old_zip and old_zip != zip_path:
                try: await minio_client.delete_file(old_zip)
                except Exception: pass  # best-effort cleanup
        except Exception:
            # ZIP pack is best-effort; don't block the pack operation
            pass

        return FilingPackResult(
            filing_doc_id=filing_doc.id,
            materials_count=len(validations),
            qualified_count=len(qualified),
            missing_signatures=[],
            ready=True,
        )

    async def _link_materials_to_filing(
        self, activity_id: UUID, filing_doc_id: UUID, validations: list[MaterialValidation],
    ) -> None:
        """Ensure all qualified materials are linked to the filing doc via filing_doc_materials."""
        material_ids = {v.material_id for v in validations}

        existing = await self.db.execute(
            select(FilingDocMaterial.material_id).where(
                FilingDocMaterial.filing_doc_id == filing_doc_id,
            )
        )
        existing_ids = {r for (r,) in existing.all()}

        for mid in material_ids - existing_ids:
            self.db.add(FilingDocMaterial(filing_doc_id=filing_doc_id, material_id=mid))
        await self.db.commit()

    async def _build_zip_pack(self, activity_name: str, activity_id: UUID) -> bytes:
        """Collect filled DOCX files for materials linked to activity and zip them."""
        # Find filled documents linked via key_materials
        materials_result = await self.db.execute(
            select(KeyMaterial).where(KeyMaterial.activity_id == activity_id)
        )
        materials = materials_result.scalars().all()

        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for i, mat in enumerate(materials, 1):
                if mat.current_filled_document_id:
                    fd = await self.db.get(FilledDocument, mat.current_filled_document_id)
                    if fd:
                        try:
                            docx_data = minio_client.minio_client.get_object(
                                minio_client._bucket, fd.minio_path,
                            ).read()
                            safe_name = f"{i:02d}_{mat.name}_v{fd.version_number}.docx"
                            zf.writestr(safe_name, docx_data)
                        except Exception:
                            # skip individual files that can't be read
                            pass

            # Add index PDF
            pdf_bytes = _generate_pdf(activity_name, [])
            zf.writestr("备案清单.pdf", pdf_bytes)

        buf.seek(0)
        return buf.getvalue()

    async def confirm_handover(self, activity_id: UUID, operator: User) -> FilingDoc:

        result = await self.db.execute(
            select(FilingDoc).where(FilingDoc.activity_id == activity_id)
        )
        filing_doc = result.scalar_one_or_none()
        if filing_doc is None:
            raise LookupError("备案材料不存在，请先执行打包")

        filing_doc.handover_status = "已交接"
        self.db.add(filing_doc)

        from app.services.workflow_service import WorkflowService
        ws = WorkflowService(self.db)
        await ws.transition(activity_id, "备案材料已交接", operator, "线下纸质材料已交接")

        await self.db.commit()
        await self.db.refresh(filing_doc)
        return filing_doc

    async def sign_material(self, activity_id: UUID, material_id: UUID,
                            user_id: UUID) -> dict:
        mat = await self.db.get(KeyMaterial, material_id)
        if mat is None:
            raise LookupError("材料不存在")
        if mat.sign_status == "signed":
            raise ValueError("材料已签署")

        mat.sign_status = "signed"
        self.db.add(mat)
        self.db.add(MaterialAudit(
            material_id=material_id,
            user_id=user_id,
            action="sign",
        ))
        await self.db.commit()
        return {"material_id": str(material_id), "sign_status": "signed"}

    async def audit_material(self, activity_id: UUID, material_id: UUID,
                              user_id: UUID, conclusion: str,
                              opinion: str | None = None) -> dict:
        if conclusion not in ("qualified", "unqualified"):
            raise ValueError("结论必须为 qualified 或 unqualified")

        mat = await self.db.get(KeyMaterial, material_id)
        if mat is None:
            raise LookupError("材料不存在")

        mat.is_qualified = (conclusion == "qualified")
        mat.opinion = opinion
        mat.audit_round += 1
        self.db.add(mat)
        self.db.add(MaterialAudit(
            material_id=material_id,
            user_id=user_id,
            action="audit",
            conclusion=conclusion,
            opinion=opinion,
        ))
        await self.db.commit()
        return {
            "material_id": str(material_id),
            "is_qualified": mat.is_qualified,
            "audit_round": mat.audit_round,
        }

    async def get_filing_status(self, activity_id: UUID) -> dict:
        result = await self.db.execute(
            select(FilingDoc).where(FilingDoc.activity_id == activity_id)
        )
        fd = result.scalar_one_or_none()
        if fd is None:
            return {"packed": False, "handed_over": False, "generated_at": None, "pack_url": None}
        return {
            "packed": fd.generated_at is not None and fd.is_qualified,
            "handed_over": fd.handover_status == "已交接",
            "generated_at": fd.generated_at.isoformat() if fd.generated_at else None,
            "pack_url": fd.pack_url,
        }

    async def create_approval_record(
        self, activity_id: UUID, liaison_id: UUID,
        approval_status: str, attachment_url: str | None = None,
        rectification_opinion: str | None = None,
    ) -> dict:
        """Create ApprovalRecord and transition workflow (GovLiaison decision)."""
        from app.models.activity import ApprovalRecord, Activity
        from app.services.workflow_service import WorkflowService

        activity = await self.db.get(Activity, activity_id)
        if activity is None:
            raise LookupError("活动不存在")
        if activity.status != "备案材料已交接":
            raise ValueError("当前状态不允许创建审批记录")

        if approval_status == "审批通过" and not attachment_url:
            raise ValueError("审批通过必须上传政府批文")
        valid_statuses = {"审批通过", "待补充备案材料", "不通过/已终止"}
        if approval_status not in valid_statuses:
            raise ValueError(f"无效的审批结果: {approval_status}")

        target = "审批通过-待举办" if approval_status == "审批通过" else approval_status
        record = ApprovalRecord(
            activity_id=activity_id,
            liaison_id=liaison_id,
            approval_status=approval_status,
            attachment_url=attachment_url,
            approval_date=datetime.now(timezone.utc),
            rectification_opinion=rectification_opinion,
        )
        self.db.add(record)
        await self.db.flush()

        ws = WorkflowService(self.db)
        User = __import__("app.models.user", fromlist=["User"]).User
        operator = await self.db.get(User, liaison_id)
        await ws.transition(activity_id, target, operator, rectification_opinion)

        await self.db.commit()
        await self.db.refresh(record)

        return {
            "id": str(record.id),
            "activity_id": str(record.activity_id),
            "approval_status": record.approval_status,
            "approval_date": record.approval_date.isoformat() if record.approval_date else None,
            "rectification_opinion": record.rectification_opinion,
        }

    async def list_materials(self, activity_id: UUID) -> list[dict]:
        result = await self.db.execute(
            text("""
                SELECT km.id, km.name, km.is_qualified, km.sign_status,
                       km.audit_round, km.opinion, km.upload_time, km.created_at,
                       km.material_type, fd.minio_path, fd.pdf_path, fd.version_number
                FROM key_materials km
                JOIN security_plan_materials spm ON spm.material_id = km.id
                JOIN security_plans sp ON sp.id = spm.security_plan_id
                LEFT JOIN filled_documents fd ON fd.id = km.current_filled_document_id
                WHERE sp.activity_id = :aid
                UNION
                SELECT km.id, km.name, km.is_qualified, km.sign_status,
                       km.audit_round, km.opinion, km.upload_time, km.created_at,
                       km.material_type, fd.minio_path, fd.pdf_path, fd.version_number
                FROM key_materials km
                LEFT JOIN filled_documents fd ON fd.id = km.current_filled_document_id
                WHERE km.activity_id = :aid
                ORDER BY created_at
            """), {"aid": activity_id})
        rows = result.fetchall()
        return [
            {
                "id": str(r[0]), "name": r[1], "is_qualified": r[2],
                "sign_status": r[3], "audit_round": r[4], "opinion": r[5],
                "upload_time": r[6].isoformat() if r[6] else "",
                "material_type": r[8] or "",
                "minio_path": r[9] or "",
                "pdf_path": r[10] or "",
                "current_version": r[11] or 0,
            }
            for r in rows
        ]

    async def get_audit_history(self, activity_id: UUID) -> list[dict]:
        from app.models.material import KeyMaterial as KM, MaterialAudit
        from app.models.user import User

        result = await self.db.execute(text("""
            SELECT spm.material_id FROM security_plan_materials spm
            JOIN security_plans sp ON sp.id = spm.security_plan_id
            WHERE sp.activity_id = :aid
            UNION
            SELECT fdm.material_id FROM filing_doc_materials fdm
            JOIN filing_docs fd ON fd.id = fdm.filing_doc_id
            WHERE fd.activity_id = :aid
            UNION
            SELECT km.id FROM key_materials km WHERE km.activity_id = :aid
        """), {"aid": activity_id})
        material_ids = [row[0] for row in result.all()]
        if not material_ids:
            return []

        rows = await self.db.execute(
            select(MaterialAudit, User.display_name, KM.name)
            .join(User, User.id == MaterialAudit.user_id)
            .join(KM, KM.id == MaterialAudit.material_id)
            .where(MaterialAudit.material_id.in_(material_ids))
            .order_by(MaterialAudit.created_at.desc())
        )
        result_rows = rows.all()
        return [
            {
                "id": str(ma.id), "action": ma.action,
                "user_name": user_name, "conclusion": ma.conclusion,
                "opinion": ma.opinion, "material_name": mat_name,
                "created_at": ma.created_at.isoformat(),
            }
            for ma, user_name, mat_name in result_rows
        ]
