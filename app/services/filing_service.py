from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.models.user import User
from app.schemas.filing import FilingPackResult, MaterialValidation

# These tables are created by init-scripts/02-activity-tables.sql but ORM models
# not yet defined. We'll use raw SQL for the join queries until models are added.
JOIN_QUERY = """
SELECT km.id, km.name, km.is_qualified, km.opinion
FROM key_materials km
JOIN security_plan_materials spm ON spm.material_id = km.id
JOIN security_plans sp ON sp.id = spm.security_plan_id
WHERE sp.activity_id = :activity_id
UNION
SELECT km.id, km.name, km.is_qualified, km.opinion
FROM key_materials km
JOIN filing_doc_materials fdm ON fdm.material_id = km.id
JOIN filing_docs fd ON fd.id = fdm.filing_doc_id
WHERE fd.activity_id = :activity_id
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
            if not row.is_qualified:
                issues.append("材料未通过合规校验")
            if row.opinion and "缺失" in row.opinion:
                issues.append(f"意见: {row.opinion}")
            validations.append(MaterialValidation(
                material_id=row.id,
                name=row.name,
                is_qualified=row.is_qualified,
                has_signature=False,
                issues=issues,
            ))
        return validations

    async def pack_materials(self, activity_id: UUID) -> FilingPackResult:
        validations = await self.validate_materials(activity_id)
        qualified = [v for v in validations if v.is_qualified and not v.issues]
        all_ok = len(qualified) == len(validations) and len(validations) > 0

        from app.models.filing import FilingDoc

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
                missing_signatures=[v.name for v in validations if not v.is_qualified],
                ready=False,
            )

        from app.models.activity import Activity
        activity = await self.db.get(Activity, activity_id)

        pdf_bytes = _generate_pdf(activity.name if activity else "未知活动", validations)
        from app.services.minio_client import upload_file as minio_upload
        pdf_path = f"filings/{activity_id}/pack_{filing_doc.id}.pdf"
        await minio_upload(pdf_path, pdf_bytes, "application/pdf")

        return FilingPackResult(
            filing_doc_id=filing_doc.id,
            materials_count=len(validations),
            qualified_count=len(qualified),
            missing_signatures=[],
            ready=True,
        )

    async def confirm_handover(self, activity_id: UUID, operator: User) -> FilingDoc:
        from app.models.filing import FilingDoc

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
