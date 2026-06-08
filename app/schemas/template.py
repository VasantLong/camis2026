from uuid import UUID

from pydantic import BaseModel


class SchemaResponse(BaseModel):
    template_type: str
    display_name: str
    has_draft: bool = False
    draft_data: dict | None = None
    snapshot_data: dict | None = None
    current_version: int | None = None
    risk_level: str | None = None  # security plan only
    fields: list[dict]


class DraftRequest(BaseModel):
    data: dict


class GenerateRequest(BaseModel):
    data: dict


class GenerateResponse(BaseModel):
    id: UUID
    template_type: str
    version_number: int
    minio_path: str | None = None
    pdf_ready: bool = False
    pdf_preview_url: str | None = None
    created_at: str | None


class VersionItem(BaseModel):
    id: str
    version_number: int
    generated_by: str
    created_at: str | None
    is_current: bool
    pdf_ready: bool = False


class VersionDetail(BaseModel):
    id: str
    version_number: int
    data_snapshot: dict
    template_hash: str
    generated_by: str
    created_at: str | None
    is_current: bool
    pdf_ready: bool = False


class VersionDiff(BaseModel):
    field: str
    old: object
    new: object


class CreateMaterialRequest(BaseModel):
    material_type: str  # "risk_assessment" | "responsibility_letter"


class CreateMaterialResponse(BaseModel):
    material_id: UUID
    name: str
    template_type: str
