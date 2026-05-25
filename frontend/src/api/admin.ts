import client from "./client";

export interface RoleRequestItem {
  id: string;
  user_id: string;
  role_id: string;
  role_name: string;
  status: string;
  comment: string | null;
  created_at: string;
  reviewer_id: string | null;
  reviewed_at: string | null;
}

export const adminApi = {
  getRoleRequests: () =>
    client.get<RoleRequestItem[]>("/admin/role-requests"),

  approveRequest: (id: string) =>
    client.post<RoleRequestItem>(`/admin/role-requests/${id}/approve`),

  rejectRequest: (id: string, comment: string) =>
    client.post<RoleRequestItem>(`/admin/role-requests/${id}/reject`, {
      status: "rejected",
      comment,
    }),
};
