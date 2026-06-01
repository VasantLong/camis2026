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
    svc: FilingService = Depends(_service),
):
    result = await svc.get_filing_status(activity_id)
    return FilingStatus(**result)


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
    svc: FilingService = Depends(_service),
):
    rows = await svc.list_materials(activity_id)
    return [MaterialWithStatus(**r) for r in rows]


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
    svc: FilingService = Depends(_service),
):
    rows = await svc.get_audit_history(activity_id)
    return [AuditHistoryItem(**r) for r in rows]
