import client from "./client";

export interface NotificationItem {
  id: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export const notificationsApi = {
  list: (limit?: number) =>
    client.get<NotificationItem[]>("/notifications", { params: { limit } }),

  unreadCount: () =>
    client.get<{ count: number }>("/notifications/unread-count"),

  markRead: (id: string) =>
    client.patch(`/notifications/${id}/read`),

  markAllRead: () =>
    client.patch("/notifications/read-all"),
};
