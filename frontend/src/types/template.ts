export interface FieldDef {
  name: string;
  ui_label: string;
  ui_type: "text" | "textarea" | "number" | "date" | "select" | "repeater" | "signature" | "checkbox";
  required?: boolean;
  min?: number;
  max?: number;
  min_items?: number;
  options?: string[];
  condition?: string;
  auto_calc?: string;
  validate?: { pattern: string; message: string };
}

export interface SchemaResponse {
  template_type: string;
  display_name: string;
  has_draft: boolean;
  draft_data: Record<string, unknown> | null;
  snapshot_data: Record<string, unknown> | null;
  current_version: number | null;
  risk_level: string | null;
  fields: FieldDef[];
}

export interface VersionItem {
  id: string;
  version_number: number;
  generated_by: string;
  created_at: string | null;
  is_current: boolean;
  pdf_ready: boolean;
}

export interface VersionDetail extends VersionItem {
  data_snapshot: Record<string, unknown>;
  template_hash: string;
}

export interface VersionDiff {
  field: string;
  old: unknown;
  new: unknown;
}

export interface GenerateResponse {
  id: string;
  template_type: string;
  version_number: number;
  minio_path: string;
  pdf_ready: boolean;
  pdf_preview_url: string | null;
  created_at: string | null;
}
