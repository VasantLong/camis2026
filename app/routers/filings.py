from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.rbac import require_permission
from app.schemas.filing import FilingPackResult, MaterialValidation
from app.services.filing_service import FilingService
from app.errors import NotFoundError, ValidationError, ConflictError
from pydantic import BaseModel

router = APIRouter(prefix="/activities", tags=["filing"])


def _service(db=Depends(get_db)) -> FilingService:
    return FilingService(db)


class FilingStatus(BaseModel):
    packed: bool = False
    handed_over: bool = False
    generated_at: str | None = None


@router.get("/{activity_id}/filing/status", response_model=FilingStatus)
async def get_filing_status(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    from app.models.filing import FilingDoc
    from sqlalchemy import select as sa_select
    result = await db.execute(
        sa_select(FilingDoc).where(FilingDoc.activity_id == activity_id)
    )
    fd = result.scalar_one_or_none()
    if fd is None:
        return FilingStatus()
    return FilingStatus(
        packed=fd.generated_at is not None and fd.is_qualified,
        handed_over=fd.handover_status == "已交接",
        generated_at=fd.generated_at.isoformat() if fd.generated_at else None,
    )


@router.get("/{activity_id}/filing/validate", response_model=list[MaterialValidation])
async def validate_materials(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: FilingService = Depends(_service),
    _perm: None = require_permission("pack_filing"),
):
    try:
        return await svc.validate_materials(activity_id)
    except LookupError as e:
        raise NotFoundError(str(e))


@router.post("/{activity_id}/filing/pack", response_model=FilingPackResult)
async def pack_materials(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: FilingService = Depends(_service),
    _perm: None = require_permission("pack_filing"),
):
    try:
        result = await svc.pack_materials(activity_id)
        if not result.ready:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"材料不齐全，缺失签名: {result.missing_signatures}",
            )
        return result
    except LookupError as e:
        raise NotFoundError(str(e))


@router.post("/{activity_id}/filing/handover")
async def confirm_handover(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: FilingService = Depends(_service),
    _perm: None = require_permission("pack_filing"),
):
    try:
        filing_doc = await svc.confirm_handover(activity_id, current_user)
        return {"filing_doc_id": str(filing_doc.id), "handover_status": filing_doc.handover_status}
    except LookupError as e:
        raise NotFoundError(str(e))


# ── material sign & audit ──


class MaterialSignRequest(BaseModel):
    pass


class MaterialAuditRequest(BaseModel):
    conclusion: str
    opinion: str | None = None


class AuditHistoryItem(BaseModel):
    id: str
    action: str
    user_name: str
    conclusion: str | None = None
    opinion: str | None = None
    created_at: str


class MaterialWithStatus(BaseModel):
    id: str
    name: str
    is_qualified: bool
    sign_status: str
    audit_round: int
    opinion: str | None = None
    upload_time: str


@router.get("/{activity_id}/materials", response_model=list[MaterialWithStatus])
async def list_materials(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    from sqlalchemy import text
    result = await db.execute(text("""
        SELECT km.id, km.name, km.is_qualified, km.sign_status,
               km.audit_round, km.opinion, km.upload_time
        FROM key_materials km
        JOIN security_plan_materials spm ON spm.material_id = km.id
        JOIN security_plans sp ON sp.id = spm.security_plan_id
        WHERE sp.activity_id = :aid
        ORDER BY km.created_at
    """), {"aid": activity_id})
    rows = result.fetchall()
    return [
        MaterialWithStatus(
            id=str(r[0]), name=r[1], is_qualified=r[2], sign_status=r[3],
            audit_round=r[4], opinion=r[5],
            upload_time=r[6].isoformat() if r[6] else "",
        )
        for r in rows
    ]


@router.post("/{activity_id}/materials/{material_id}/sign")
async def sign_material(
    activity_id: UUID,
    material_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: FilingService = Depends(_service),
    _perm: None = require_permission("sign_document"),
):
    try:
        return await svc.sign_material(activity_id, material_id, current_user.id)
    except LookupError as e:
        raise NotFoundError(str(e))
    except ValueError as e:
        raise ConflictError(str(e))


@router.post("/{activity_id}/materials/{material_id}/audit")
async def audit_material(
    activity_id: UUID,
    material_id: UUID,
    body: MaterialAuditRequest,
    current_user: User = Depends(get_current_user),
    svc: FilingService = Depends(_service),
    _perm: None = require_permission("audit_material"),
):
    try:
        return await svc.audit_material(activity_id, material_id, current_user.id,
                                         body.conclusion, body.opinion)
    except LookupError as e:
        raise NotFoundError(str(e))
    except ValueError as e:
        raise ValidationError(str(e))


@router.get("/{activity_id}/materials/audit-history", response_model=list[AuditHistoryItem])
async def get_audit_history(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    from app.models.material import MaterialAudit, KeyMaterial
    from sqlalchemy import select as sa_select, text
    # Get material IDs linked to this activity via security_plan_materials
    sp_result = await db.execute(text("""
        SELECT spm.material_id FROM security_plan_materials spm
        JOIN security_plans sp ON sp.id = spm.security_plan_id
        WHERE sp.activity_id = :aid
        UNION
        SELECT fdm.material_id FROM filing_doc_materials fdm
        JOIN filing_docs fd ON fd.id = fdm.filing_doc_id
        WHERE fd.activity_id = :aid
    """), {"aid": activity_id})
    material_ids = [row[0] for row in sp_result.all()]
    if not material_ids:
        return []

    result = await db.execute(
        sa_select(MaterialAudit, User.username, KeyMaterial.name)
        .join(User, User.id == MaterialAudit.user_id)
        .join(KeyMaterial, KeyMaterial.id == MaterialAudit.material_id)
        .where(MaterialAudit.material_id.in_(material_ids))
        .order_by(MaterialAudit.created_at.desc())
    )
    rows = result.all()
    return [
        AuditHistoryItem(
            id=str(ma.id),
            action=ma.action,
            user_name=user_name,
            conclusion=ma.conclusion,
            opinion=ma.opinion,
            created_at=ma.created_at.isoformat(),
        )
        for ma, user_name, mat_name in rows
    ]
