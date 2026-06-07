import client from "./client";
import type {
  SchemaResponse,
  VersionItem,
  VersionDetail,
  VersionDiff,
  GenerateResponse,
} from "@/types/template";

export const templatesApi = {
  // ── activity plan ──
  getPlanSchema: (activityId: string) =>
    client.get<SchemaResponse>(`/activities/${activityId}/plan/schema`),

  savePlanDraft: (activityId: string, data: Record<string, unknown>) =>
    client.put<{ ok: boolean }>(`/activities/${activityId}/plan/draft`, { data }),

  generatePlan: (activityId: string, data: Record<string, unknown>) =>
    client.post<GenerateResponse>(`/activities/${activityId}/plan/generate`, { data }),

  getPlanVersions: (activityId: string) =>
    client.get<VersionItem[]>(`/activities/${activityId}/plan/versions`),

  getPlanVersionDetail: (activityId: string, version: number) =>
    client.get<VersionDetail>(`/activities/${activityId}/plan/versions/${version}`),

  getPlanVersionDiff: (activityId: string, v1: number, v2: number) =>
    client.get<VersionDiff[]>(`/activities/${activityId}/plan/versions/${v1}/diff/${v2}`),

  getPlanVersionPreview: (activityId: string, version: number) =>
    client.get<{ url: string }>(`/activities/${activityId}/plan/versions/${version}/preview`),

  finalizePlan: (activityId: string) =>
    client.post<{ ok: boolean }>(`/activities/${activityId}/plan/finalize`),

  // ── security plan ──
  getSecurityPlanSchema: (activityId: string) =>
    client.get<SchemaResponse>(`/activities/${activityId}/security-plan/schema`),

  saveSecurityPlanDraft: (activityId: string, data: Record<string, unknown>) =>
    client.put<{ ok: boolean }>(`/activities/${activityId}/security-plan/draft`, { data }),

  generateSecurityPlan: (activityId: string, data: Record<string, unknown>) =>
    client.post<GenerateResponse>(`/activities/${activityId}/security-plan/generate`, { data }),

  getSecurityPlanVersions: (activityId: string) =>
    client.get<VersionItem[]>(`/activities/${activityId}/security-plan/versions`),

  getSecurityPlanVersionDetail: (activityId: string, version: number) =>
    client.get<VersionDetail>(`/activities/${activityId}/security-plan/versions/${version}`),

  getSecurityPlanVersionDiff: (activityId: string, v1: number, v2: number) =>
    client.get<VersionDiff[]>(`/activities/${activityId}/security-plan/versions/${v1}/diff/${v2}`),

  // ── key materials ──
  getMaterialSchema: (activityId: string, materialId: string) =>
    client.get<SchemaResponse>(`/activities/${activityId}/materials/${materialId}/schema`),

  saveMaterialDraft: (activityId: string, materialId: string, data: Record<string, unknown>) =>
    client.put<{ ok: boolean }>(`/activities/${activityId}/materials/${materialId}/draft`, { data }),

  generateMaterial: (activityId: string, materialId: string, data: Record<string, unknown>) =>
    client.post<GenerateResponse>(`/activities/${activityId}/materials/${materialId}/generate`, { data }),

  getMaterialVersions: (activityId: string, materialId: string) =>
    client.get<VersionItem[]>(`/activities/${activityId}/materials/${materialId}/versions`),

  getMaterialVersionDetail: (activityId: string, materialId: string, version: number) =>
    client.get<VersionDetail>(`/activities/${activityId}/materials/${materialId}/versions/${version}`),

  getMaterialVersionDiff: (activityId: string, materialId: string, v1: number, v2: number) =>
    client.get<VersionDiff[]>(`/activities/${activityId}/materials/${materialId}/versions/${v1}/diff/${v2}`),
};
