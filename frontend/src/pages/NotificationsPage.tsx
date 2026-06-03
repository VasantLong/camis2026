import { useState } from "react";
import { List, Typography, Tabs, Button, Empty, Badge, Space, message } from "antd";
import { BellOutlined, MailOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notificationsApi, type NotificationItem } from "@/api/notifications";
import { dashboardApi } from "@/api/dashboard";

const { Title, Text } = Typography;

export default function NotificationsPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [tab, setTab] = useState<"unread" | "all">("unread");

  const { data: notifications = [], isLoading } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => notificationsApi.list(50).then((r) => r.data),
    refetchInterval: 30_000,
    staleTime: 0,
  });

  const markRead = useMutation({
    mutationFn: (id: string) => notificationsApi.markRead(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications"] });
      qc.invalidateQueries({ queryKey: ["notifications", "unread-count"] });
    },
  });

  const markAllRead = useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications"] });
      qc.invalidateQueries({ queryKey: ["notifications", "unread-count"] });
      message.success("已全部标为已读");
    },
  });

  const handleClick = (item: NotificationItem) => {
    if (!item.is_read) markRead.mutate(item.id);
    if (item.reference_type === "report") {
      const m = item.message.match(/(\d{4}-\d{2})/);
      if (m) dashboardApi.downloadReport(m[1]);
    } else if (item.reference_type === "activity" && item.reference_id) {
      navigate(`/activities/${item.reference_id}`);
    } else {
      navigate("/activities?tab=pending");
    }
  };

  const filtered = tab === "unread" ? notifications.filter((n) => !n.is_read) : notifications;
  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>消息中心</Title>
        {unreadCount > 0 && (
          <Button size="small" onClick={() => markAllRead.mutate()} loading={markAllRead.isPending}>
            全部标为已读
          </Button>
        )}
      </div>

      <Tabs
        activeKey={tab}
        onChange={(k) => setTab(k as "unread" | "all")}
        items={[
          {
            key: "unread",
            label: <Space>未读{unreadCount > 0 && <Badge count={unreadCount} size="small" />}</Space>,
          },
          { key: "all", label: "全部" },
        ]}
      />

      <List
        loading={isLoading}
        dataSource={filtered}
        locale={{ emptyText: <Empty description={tab === "unread" ? "没有未读消息" : "暂无消息"} /> }}
        renderItem={(item) => (
          <List.Item
            key={item.id}
            style={{
              cursor: "pointer",
              background: item.is_read ? undefined : "#f0f5ff",
              padding: "12px 16px",
            }}
            onClick={() => handleClick(item)}
          >
            <List.Item.Meta
              avatar={
                item.is_read ? <MailOutlined style={{ color: "#bbb" }} /> : <BellOutlined style={{ color: "#1677ff" }} />
              }
              title={
                <Space>
                  {item.reference_name && <Text strong>{item.reference_name}</Text>}
                  {!item.is_read && <Badge status="processing" />}
                </Space>
              }
              description={
                <>
                  <div>{item.message}</div>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {new Date(item.created_at).toLocaleString("zh-CN")}
                  </Text>
                </>
              }
            />
          </List.Item>
        )}
      />
    </div>
  );
}
