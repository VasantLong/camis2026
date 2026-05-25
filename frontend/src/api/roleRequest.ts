import client from "./client";

export interface RoleRequestResponse {
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

export const roleRequestApi = {
  submit: (roleId: string) =>
    client.post<RoleRequestResponse>("/auth/me/role-request", {
      role_id: roleId,
    }),
};
