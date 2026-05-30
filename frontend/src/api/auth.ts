import client from "./client";
import type {
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  UserResponse,
} from "@/types/auth";

export interface RoleOption {
  id: string;
  name: string;
  label: string;
}

export const authApi = {
  login: (data: LoginRequest) =>
    client.post<TokenResponse>("/auth/login", data),

  register: (data: RegisterRequest) =>
    client.post<TokenResponse>("/auth/register", data),

  me: () => client.get<UserResponse>("/auth/me"),

  refresh: () => client.post<TokenResponse>("/auth/refresh"),

  logout: () => client.post("/auth/logout"),

  getRoles: () => client.get<RoleOption[]>("/auth/roles"),

  updateProfile: (data: { display_name: string; contact_phone?: string }) =>
    client.patch<UserResponse>("/auth/me", data),

  requestEmailChange: (new_email: string) =>
    client.post("/auth/me/email-change", { new_email }),
};
