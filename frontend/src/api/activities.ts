import client from "./client";
import type {
  ActivityCreate,
  ActivityResponse,
  ActivityListParams,
  ActivityPaginatedResponse,
  StatusLogEntry,
} from "@/types/activity";
import type { DocumentResponse } from "@/types/document";

export const activitiesApi = {
  list: (params: ActivityListParams) =>
    client.get<ActivityPaginatedResponse>("/activities", { params }),

  get: (id: string) =>
    client.get<ActivityResponse>(`/activities/${id}`),

  create: (data: ActivityCreate) =>
    client.post<ActivityResponse>("/activities", data),

  getHistory: (id: string) =>
    client.get<StatusLogEntry[]>(`/activities/${id}/history`),

  getDocuments: (id: string) =>
    client.get<DocumentResponse[]>(`/activities/${id}/documents`),

  getSecurityPlan: (id: string) =>
    client.get<{
      risk_level: string | null;
      audit_status: string | null;
      manager_name: string | null;
      sign_time: string | null;
      last_reject_reason: string | null;
      rejected_at: string | null;
    }>(`/activities/${id}/security-plan`),

  updateSecurityPlan: (id: string, data: { risk_level?: string }) =>
    client.put<{
      risk_level: string | null;
      audit_status: string | null;
      manager_name: string | null;
      sign_time: string | null;
      last_reject_reason: string | null;
      rejected_at: string | null;
    }>(`/activities/${id}/security-plan`, data),

  fetchCounts: () =>
    client.get<Record<string, number>>("/activities/counts"),
};
