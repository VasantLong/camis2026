from uuid import UUID

from pydantic import BaseModel


class MaterialValidation(BaseModel):
    material_id: UUID
    name: str
    is_qualified: bool
    has_signature: bool
    issues: list[str]


class FilingPackResult(BaseModel):
    filing_doc_id: UUID
    materials_count: int
    qualified_count: int
    missing_signatures: list[str]
    ready: bool
