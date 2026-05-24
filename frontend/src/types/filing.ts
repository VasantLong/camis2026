export interface MaterialValidation {
  material_id: string;
  name: string;
  is_qualified: boolean;
  has_signature: boolean;
  issues: string[];
}

export interface FilingPackResult {
  filing_doc_id: string;
  materials_count: number;
  qualified_count: number;
  missing_signatures: string[];
  ready: boolean;
}
