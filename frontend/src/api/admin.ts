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

export interface UserListItem {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  roles: string[];
  created_at: string;
}

export interface UserDetail extends UserListItem {
  permissions: string[];
  updated_at: string;
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

  getUsers: () => client.get<UserListItem[]>("/admin/users"),

  getUser: (id: string) => client.get<UserDetail>(`/admin/users/${id}`),

  updateUserRoles: (id: string, roleIds: string[]) =>
    client.put<UserDetail>(`/admin/users/${id}/roles`, { role_ids: roleIds }),

  updateUserStatus: (id: string, isActive: boolean) =>
    client.patch<UserDetail>(`/admin/users/${id}/status`, {
      is_active: isActive,
    }),

  deleteUser: (id: string) =>
    client.delete(`/admin/users/${id}`),
};
