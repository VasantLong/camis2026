from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.rbac import require_permission
from app.schemas.template import (
    DraftRequest, GenerateRequest, GenerateResponse,
    SchemaResponse, VersionDetail, VersionDiff, VersionItem,
)
from app.services.template_service import TemplateService, render_pdf_background

router = APIRouter(prefix="/activities", tags=["templates"])


def _svc(db=Depends(get_db)) -> TemplateService:
    return TemplateService(db)


# ----------------------------------------------------------------
# activity plan
# ----------------------------------------------------------------

@router.get("/{activity_id}/plan/schema")
async def plan_schema(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: TemplateService = Depends(_svc),
):
    """Return activity plan form schema + draft data."""
    s = await svc.get_schema("activity_plan", activity_id)
    return SchemaResponse(
        template_type="activity_plan",
        display_name="活动方案",
        has_draft=s.get("has_draft", False),
        draft_data=s.get("draft_data"),
        snapshot_data=s.get("snapshot_data"),
        current_version=s.get("current_version"),
        fields=s.get("fields", []),
    )


@router.put("/{activity_id}/plan/draft")
async def plan_save_draft(
    activity_id: UUID,
    body: DraftRequest,
    current_user: User = Depends(get_current_user),
    _=require_permission("submit_plan"),
    svc: TemplateService = Depends(_svc),
):
    """Save activity plan draft."""
    await svc.save_draft("activity_plan", activity_id, body.data, current_user.id)
    return {"ok": True}


@router.post("/{activity_id}/plan/generate", response_model=GenerateResponse)
async def plan_generate(
    activity_id: UUID,
    body: GenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    _=require_permission("submit_plan"),
    svc: TemplateService = Depends(_svc),
):
    """Generate activity plan DOCX+PDF from template. PDF rendered in background."""
    result = await svc.generate("activity_plan", activity_id, body.data, current_user.id)
    docx_bytes = result.pop("docx_bytes", None)
    if docx_bytes:
        background_tasks.add_task(
            render_pdf_background, result["id"], docx_bytes,
            activity_id, "activity_plan", result["version_number"],
        )
    return GenerateResponse(**result)


@router.get("/{activity_id}/plan/versions", response_model=list[VersionItem])
async def plan_versions(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: TemplateService = Depends(_svc),
):
    return [VersionItem(**v) for v in await svc.get_versions("activity_plan", activity_id)]


@router.get("/{activity_id}/plan/versions/{version_number}", response_model=VersionDetail)
async def plan_version_detail(
    activity_id: UUID, version_number: int,
    current_user: User = Depends(get_current_user),
    svc: TemplateService = Depends(_svc),
):
    detail = await svc.get_version_detail("activity_plan", activity_id, version_number)
    if not detail:
        raise HTTPException(status_code=404, detail="Version not found")
    return VersionDetail(**detail)


@router.post("/{activity_id}/plan/finalize")
async def plan_finalize(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    _=require_permission("submit_plan"),
    svc: TemplateService = Depends(_svc),
):
    """Finalize activity plan: submit to 安保方案设计 stage."""
    try:
        await svc.finalize_plan(activity_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@router.get("/{activity_id}/plan/versions/{version_number}/preview")
async def plan_version_preview(
    activity_id: UUID, version_number: int,
    current_user: User = Depends(get_current_user),
    svc: TemplateService = Depends(_svc),
):
    """Return pre-signed URL for a specific plan version's PDF."""
    url = await svc.get_version_preview_url("activity_plan", activity_id, version_number)
    if not url:
        raise HTTPException(status_code=404, detail="PDF not available for this version")
    return {"url": url}


@router.get("/{activity_id}/plan/versions/{v1}/diff/{v2}", response_model=list[VersionDiff])
async def plan_version_diff(
    activity_id: UUID, v1: int, v2: int,
    current_user: User = Depends(get_current_user),
    svc: TemplateService = Depends(_svc),
):
    return [VersionDiff(**d) for d in await svc.get_version_diff("activity_plan", activity_id, v1, v2)]


# ----------------------------------------------------------------
# security plan
# ----------------------------------------------------------------

@router.get("/{activity_id}/security-plan/schema")
async def security_plan_schema(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: TemplateService = Depends(_svc),
):
    s = await svc.get_schema("security_plan", activity_id)
    return SchemaResponse(
        template_type="security_plan",
        display_name="安保方案",
        has_draft=s.get("has_draft", False),
        draft_data=s.get("draft_data"),
        snapshot_data=s.get("snapshot_data"),
        current_version=s.get("current_version"),
        risk_level=s.get("risk_level"),
        fields=s.get("fields", []),
    )


@router.put("/{activity_id}/security-plan/draft")
async def security_plan_save_draft(
    activity_id: UUID,
    body: DraftRequest,
    current_user: User = Depends(get_current_user),
    _=require_permission("manage_security"),
    svc: TemplateService = Depends(_svc),
):
    await svc.save_draft("security_plan", activity_id, body.data, current_user.id)
    return {"ok": True}


@router.post("/{activity_id}/security-plan/generate", response_model=GenerateResponse)
async def security_plan_generate(
    activity_id: UUID,
    body: GenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    _=require_permission("manage_security"),
    svc: TemplateService = Depends(_svc),
):
    result = await svc.generate("security_plan", activity_id, body.data, current_user.id)
    docx_bytes = result.pop("docx_bytes", None)
    if docx_bytes:
        background_tasks.add_task(
            render_pdf_background, result["id"], docx_bytes,
            activity_id, "security_plan", result["version_number"],
        )
    return GenerateResponse(**result)


@router.post("/{activity_id}/security-plan/submit-review")
async def security_plan_submit_review(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    _=require_permission("manage_security"),
    svc: TemplateService = Depends(_svc),
):
    """Submit security plan for SecurityManager review after content validation."""
    try:
        await svc.submit_security_plan_for_review(activity_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@router.get("/{activity_id}/security-plan/versions", response_model=list[VersionItem])
async def security_plan_versions(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: TemplateService = Depends(_svc),
):
    return [VersionItem(**v) for v in await svc.get_versions("security_plan", activity_id)]


@router.get("/{activity_id}/security-plan/versions/{version_number}", response_model=VersionDetail)
async def security_plan_version_detail(
    activity_id: UUID, version_number: int,
    current_user: User = Depends(get_current_user),
    svc: TemplateService = Depends(_svc),
):
    detail = await svc.get_version_detail("security_plan", activity_id, version_number)
    if not detail:
        raise HTTPException(status_code=404, detail="Version not found")
    return VersionDetail(**detail)


@router.get("/{activity_id}/security-plan/versions/{v1}/diff/{v2}", response_model=list[VersionDiff])
async def security_plan_version_diff(
    activity_id: UUID, v1: int, v2: int,
    current_user: User = Depends(get_current_user),
    svc: TemplateService = Depends(_svc),
):
    return [VersionDiff(**d) for d in await svc.get_version_diff("security_plan", activity_id, v1, v2)]


# ----------------------------------------------------------------
# key materials (risk_assessment / responsibility_letter / filing_commitment)
# ----------------------------------------------------------------

@router.get("/{activity_id}/materials/{material_id}/schema")
async def material_schema(
    activity_id: UUID, material_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: TemplateService = Depends(_svc),
):
    mat = await svc.db.get(
        __import__("app.models.material", fromlist=["KeyMaterial"]).KeyMaterial, material_id,
    )
    if not mat or mat.activity_id != activity_id:
        raise HTTPException(status_code=404, detail="Material not found")
    template_type = mat.material_type
    if not template_type:
        raise HTTPException(status_code=400, detail="Material has no template type")
    s = await svc.get_schema(template_type, activity_id, template_type)
    return SchemaResponse(
        template_type=template_type,
        display_name=s.get("display_name", template_type),
        has_draft=s.get("has_draft", False),
        draft_data=s.get("draft_data"),
        snapshot_data=s.get("snapshot_data"),
        current_version=s.get("current_version"),
        fields=s.get("fields", []),
    )


@router.put("/{activity_id}/materials/{material_id}/draft")
async def material_save_draft(
    activity_id: UUID, material_id: UUID,
    body: DraftRequest,
    current_user: User = Depends(get_current_user),
    _=require_permission("pack_filing"),
    svc: TemplateService = Depends(_svc),
):
    mat = await svc.db.get(
        __import__("app.models.material", fromlist=["KeyMaterial"]).KeyMaterial, material_id,
    )
    if not mat or mat.activity_id != activity_id or not mat.material_type:
        raise HTTPException(status_code=404, detail="Material not found")
    await svc.save_draft(mat.material_type, activity_id, body.data, current_user.id, mat.material_type)
    return {"ok": True}


@router.post("/{activity_id}/materials/{material_id}/generate", response_model=GenerateResponse)
async def material_generate(
    activity_id: UUID, material_id: UUID,
    body: GenerateRequest,
    current_user: User = Depends(get_current_user),
    _=require_permission("pack_filing"),
    svc: TemplateService = Depends(_svc),
):
    mat = await svc.db.get(
        __import__("app.models.material", fromlist=["KeyMaterial"]).KeyMaterial, material_id,
    )
    if not mat or mat.activity_id != activity_id or not mat.material_type:
        raise HTTPException(status_code=404, detail="Material not found")
    result = await svc.generate(
        mat.material_type, activity_id, body.data, current_user.id, mat.material_type,
    )
    docx_bytes = result.pop("docx_bytes", None)
    if docx_bytes:
        background_tasks.add_task(
            render_pdf_background, result["id"], docx_bytes,
            activity_id, mat.material_type, result["version_number"],
        )
    return GenerateResponse(**result)


@router.get("/{activity_id}/materials/{material_id}/versions", response_model=list[VersionItem])
async def material_versions(
    activity_id: UUID, material_id: UUID,
    current_user: User = Depends(get_current_user),
    svc: TemplateService = Depends(_svc),
):
    mat = await svc.db.get(
        __import__("app.models.material", fromlist=["KeyMaterial"]).KeyMaterial, material_id,
    )
    if not mat or mat.activity_id != activity_id or not mat.material_type:
        raise HTTPException(status_code=404, detail="Material not found")
    return [VersionItem(**v) for v in await svc.get_versions(
        mat.material_type, activity_id, mat.material_type,
    )]


@router.get("/{activity_id}/materials/{material_id}/versions/{version_number}", response_model=VersionDetail)
async def material_version_detail(
    activity_id: UUID, material_id: UUID, version_number: int,
    current_user: User = Depends(get_current_user),
    svc: TemplateService = Depends(_svc),
):
    mat = await svc.db.get(
        __import__("app.models.material", fromlist=["KeyMaterial"]).KeyMaterial, material_id,
    )
    if not mat or mat.activity_id != activity_id or not mat.material_type:
        raise HTTPException(status_code=404, detail="Material not found")
    detail = await svc.get_version_detail(
        mat.material_type, activity_id, version_number, mat.material_type,
    )
    if not detail:
        raise HTTPException(status_code=404, detail="Version not found")
    return VersionDetail(**detail)


@router.get("/{activity_id}/materials/{material_id}/versions/{v1}/diff/{v2}", response_model=list[VersionDiff])
async def material_version_diff(
    activity_id: UUID, material_id: UUID, v1: int, v2: int,
    current_user: User = Depends(get_current_user),
    svc: TemplateService = Depends(_svc),
):
    mat = await svc.db.get(
        __import__("app.models.material", fromlist=["KeyMaterial"]).KeyMaterial, material_id,
    )
    if not mat or mat.activity_id != activity_id or not mat.material_type:
        raise HTTPException(status_code=404, detail="Material not found")
    return [VersionDiff(**d) for d in await svc.get_version_diff(
        mat.material_type, activity_id, v1, v2, mat.material_type,
    )]
