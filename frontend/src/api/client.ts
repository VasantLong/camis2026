import axios, { type InternalAxiosRequestConfig } from "axios";
import { getAccessToken, useAuthStore } from "@/stores/authStore";

const client = axios.create({
  baseURL: "/api",
});

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error || !token) reject(error);
    else resolve(token);
  });
  failedQueue = [];
}

client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getAccessToken();
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status !== 401) {
      return Promise.reject(error.response?.data || error);
    }

    if (originalRequest.url === "/auth/refresh" || originalRequest.url === "/auth/login") {
      return Promise.reject(error.response?.data || error);
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({
          resolve: (token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(client(originalRequest));
          },
          reject,
        });
      });
    }

    isRefreshing = true;

    try {
      const { data } = await axios.post("/api/auth/refresh");
      const newToken = data.access_token;
      useAuthStore.getState().setAccessToken(newToken);
      processQueue(null, newToken);
      originalRequest.headers.Authorization = `Bearer ${newToken}`;
      return client(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError, null);
      useAuthStore.getState().clearAuth();
      window.location.href = "/login";
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

export default client;
