import { useState, useCallback } from "react";
import { Badge, Button, Dropdown, List, Typography, Empty } from "antd";
import { BellOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notificationsApi, type NotificationItem } from "@/api/notifications";

export default function HeaderNotifications() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const qc = useQueryClient();

  const { data: notifications = [] } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => notificationsApi.list(10).then((r) => r.data),
    refetchInterval: 60_000,
  });

  const { data: unread } = useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: () => notificationsApi.unreadCount().then((r) => r.data.count),
    refetchInterval: 30_000,
  });

  const markAllRead = useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const handleOpenChange = useCallback(
    (visible: boolean) => {
      setOpen(visible);
      if (visible && (unread ?? 0) > 0) {
        markAllRead.mutate();
      }
    },
    [unread, markAllRead]
  );

  const handleClick = (item: NotificationItem) => {
    setOpen(false);
    // Extract activity name from message (e.g. "活动 XXX 需进行安保方案设计")
    // Navigate to activity list pending tab; user finds the activity there
    if ((notifications?.length ?? 0) <= 3) {
      navigate("/activities?tab=pending");
    } else {
      navigate("/activities?tab=pending");
    }
  };

  const items = notifications.map((n) => ({
    key: n.id,
    label: (
      <div style={{ maxWidth: 300, whiteSpace: "normal", padding: "4px 0" }}>
        <Typography.Text>{n.message}</Typography.Text>
        <br />
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          {new Date(n.created_at).toLocaleString("zh-CN")}
        </Typography.Text>
      </div>
    ),
  }));

  if (notifications.length > 3) {
    items.push({
      key: "view-all",
      label: (
        <Typography.Link onClick={() => { setOpen(false); navigate("/activities?tab=pending"); }}>
          查看全部 ({notifications.length} 条)
        </Typography.Link>
      ),
    });
  }

  return (
    <Dropdown
      menu={{ items }}
      open={open}
      onOpenChange={handleOpenChange}
      trigger={["click"]}
      placement="bottomRight"
      dropdownRender={(menu) => (
        <div style={{ maxHeight: 360, overflow: "auto", minWidth: 280 }}>
          {notifications.length === 0 ? (
            <Empty description="暂无通知" style={{ padding: 24 }} />
          ) : (
            menu
          )}
        </div>
      )}
    >
      <Badge count={unread} size="small" offset={[-2, 2]}>
        <Button
          icon={<BellOutlined />}
          type="text"
          style={{ color: "#333" }}
          aria-label="通知"
        />
      </Badge>
    </Dropdown>
  );
}
