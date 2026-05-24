import client from "./client";
import type { PanelData, ActivityDetail } from "@/types/dashboard";

export const dashboardApi = {
  getPanel: () => client.get<PanelData>("/dashboard"),

  getActivityDetail: (activityId: string) =>
    client.get<ActivityDetail>(`/dashboard/activities/${activityId}`),

  exportMonthlyReport: (month: string) =>
    client.post<{ report_url: string; message: string }>(
      "/dashboard/reports/monthly",
      { month }
    ),
};
