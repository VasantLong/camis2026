import { create } from "zustand";
import type { UserResponse } from "@/types/auth";

interface AuthState {
  user: UserResponse | null;
  accessToken: string | null;
  isAuthenticated: boolean;

  setAccessToken: (token: string) => void;
  setUser: (user: UserResponse) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  isAuthenticated: false,

  setAccessToken: (token) => set({ accessToken: token, isAuthenticated: true }),

  setUser: (user) => set({ user }),

  clearAuth: () =>
    set({ user: null, accessToken: null, isAuthenticated: false }),
}));

export function getAccessToken(): string | null {
  return useAuthStore.getState().accessToken;
}
