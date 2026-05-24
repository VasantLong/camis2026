import client from "./client";
import type {
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  UserResponse,
} from "@/types/auth";

export const authApi = {
  login: (data: LoginRequest) =>
    client.post<TokenResponse>("/auth/login", data),

  register: (data: RegisterRequest) =>
    client.post<TokenResponse>("/auth/register", data),

  me: () => client.get<UserResponse>("/auth/me"),

  refresh: () => client.post<TokenResponse>("/auth/refresh"),

  logout: () => client.post("/auth/logout"),
};
