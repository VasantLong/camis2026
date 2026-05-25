from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.rbac import require_permission
from app.schemas.filing import FilingPackResult, MaterialValidation
from app.services.filing_service import FilingService
from app.errors import NotFoundError, ValidationError
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
