import client from "./client";

export interface AuditHistoryItem {
  id: string;
  action: string;
  user_name: string;
  material_name: string;
  conclusion: string | null;
  opinion: string | null;
  created_at: string;
}

export interface MaterialWithStatus {
  id: string;
  name: string;
  is_qualified: boolean;
  sign_status: string;
  audit_round: number;
  opinion: string | null;
  upload_time: string;
  material_type: string;
  minio_path: string;
  pdf_path: string;
  current_version: number;
}

export const materialsApi = {
  list: (activityId: string) =>
    client.get<MaterialWithStatus[]>(`/activities/${activityId}/materials`),

  sign: (activityId: string, materialId: string) =>
    client.post(`/activities/${activityId}/materials/${materialId}/sign`),

  audit: (activityId: string, materialId: string, conclusion: string, opinion?: string) =>
    client.post(`/activities/${activityId}/materials/${materialId}/audit`, {
      conclusion,
      opinion,
    }),

  getAuditHistory: (activityId: string) =>
    client.get<AuditHistoryItem[]>(`/activities/${activityId}/materials/audit-history`),
};
