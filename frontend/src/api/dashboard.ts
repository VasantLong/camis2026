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

  downloadReport: async (month: string) => {
    const res = await client.get(`/dashboard/reports/${month}`, {
      responseType: "blob",
    });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = `月报_${month}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  },
};
