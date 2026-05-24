import client from "./client";
import type {
  StatusTransition,
  RejectRequest,
  ForceChangeRequest,
} from "@/types/workflow";
import type { StatusLogEntry } from "@/types/activity";

export const workflowsApi = {
  transition: (activityId: string, data: StatusTransition) =>
    client.put<StatusLogEntry>(`/activities/${activityId}/status`, data),

  reject: (activityId: string, data: RejectRequest) =>
    client.post<StatusLogEntry>(`/activities/${activityId}/reject`, data),

  forceCancel: (activityId: string, data: ForceChangeRequest) =>
    client.post<StatusLogEntry>(
      `/activities/${activityId}/force-cancel`,
      data
    ),

  forcePostpone: (activityId: string, data: ForceChangeRequest) =>
    client.post<StatusLogEntry>(
      `/activities/${activityId}/force-postpone`,
      data
    ),
};
