import client from "./client";
import type { MaterialValidation, FilingPackResult } from "@/types/filing";

export const filingsApi = {
  validate: (activityId: string) =>
    client.get<MaterialValidation[]>(
      `/activities/${activityId}/filing/validate`
    ),

  pack: (activityId: string) =>
    client.post<FilingPackResult>(
      `/activities/${activityId}/filing/pack`
    ),

  handover: (activityId: string) =>
    client.post<{ filing_doc_id: string; handover_status: string }>(
      `/activities/${activityId}/filing/handover`
    ),

  getStatus: (activityId: string) =>
    client.get<{ packed: boolean; handed_over: boolean; generated_at: string | null }>(
      `/activities/${activityId}/filing/status`
    ),
};
