from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.filing import FilingPackResult, MaterialValidation
from app.services.filing_service import FilingService

router = APIRouter(prefix="/activities", tags=["filing"])


def _service(db=Depends(get_db)) -> FilingService:
    return FilingService(db)


@router.get("/{activity_id}/filing/validate", response_model=list[MaterialValidation])
async def validate_materials(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: FilingService = Depends(_service),
):
    try:
        return await svc.validate_materials(activity_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{activity_id}/filing/pack", response_model=FilingPackResult)
async def pack_materials(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: FilingService = Depends(_service),
):
    try:
        result = await svc.pack_materials(activity_id)
        if not result.ready:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"材料不齐全，缺失签名: {result.missing_signatures}",
            )
        return result
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{activity_id}/filing/handover")
async def confirm_handover(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: FilingService = Depends(_service),
):
    try:
        filing_doc = await svc.confirm_handover(activity_id)
        return {"filing_doc_id": str(filing_doc.id), "handover_status": filing_doc.handover_status}
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
