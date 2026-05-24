import client from "./client";
import type {
  ActivityCreate,
  ActivityResponse,
  ActivityListParams,
  StatusLogEntry,
} from "@/types/activity";
import type { DocumentResponse } from "@/types/document";

export const activitiesApi = {
  list: (params: ActivityListParams) =>
    client.get<ActivityResponse[]>("/activities", { params }),

  get: (id: string) =>
    client.get<ActivityResponse>(`/activities/${id}`),

  create: (data: ActivityCreate) =>
    client.post<ActivityResponse>("/activities", data),

  getHistory: (id: string) =>
    client.get<StatusLogEntry[]>(`/activities/${id}/history`),

  getDocuments: (id: string) =>
    client.get<DocumentResponse[]>(`/activities/${id}/documents`),
};
