import { Badge, Menu, Space } from "antd";
import {
  UnorderedListOutlined,
  PlusOutlined,
  DashboardOutlined,
  UserOutlined,
  TeamOutlined,
  AuditOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import { useActivityCounts } from "@/hooks/useActivityQueries";

export default function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const userPermissions = useAuthStore((s) => s.user?.permissions);
  const permissions = userPermissions ?? [];
  const EMPTY: string[] = [];
  const { data: counts } = useActivityCounts();

  const items: Array<{
    key: string;
    label: React.ReactNode;
    icon: React.ReactNode;
    children?: typeof items;
  }> = [];

  const activityBadge = counts
    ? (counts.my_activities ?? counts.pending_draft ?? counts.pending_review ?? counts.pending_sign_confirm ?? counts.total)
    : null;

  const canViewActivities =
    permissions.includes("view_owned_activity") || permissions.includes("view_dashboard");

  if (canViewActivities) {
    const children = [
      {
        key: "/activities",
        label: (
          <Space>
            <span>全部活动</span>
            {activityBadge != null && activityBadge > 0 && <Badge count={activityBadge} size="small" />}
          </Space>
        ),
        icon: <UnorderedListOutlined />,
      },
    ];
    if (permissions.includes("create_activity")) {
      children.push({
        key: "/activities/new",
        label: "创建新活动",
        icon: <PlusOutlined />,
      });
    }
    items.push({
      key: "activities-group",
      label: "活动管理",
      icon: <UnorderedListOutlined />,
      children,
    });
  }

  if (permissions.includes("view_dashboard")) {
    items.push({
      key: "/dashboard",
      label: (
        <Space>
          <span>活动面板</span>
          {counts?.total != null && <Badge count={counts.total} size="small" />}
        </Space>
      ),
      icon: <DashboardOutlined />,
    });
  }

  if (permissions.includes("manage_users") || permissions.includes("administer_users")) {
    const children: typeof items = [];
    if (permissions.includes("administer_users")) {
      children.push({
        key: "/admin/users",
        label: "用户列表",
        icon: <SettingOutlined />,
      });
    }
    children.push({
      key: "/admin/role-requests",
      label: (
        <Space>
          <span>角色审批</span>
          {counts?.pending_role_requests != null && counts.pending_role_requests > 0 && (
            <Badge count={counts.pending_role_requests} size="small" />
          )}
        </Space>
      ),
      icon: <AuditOutlined />,
    });
    items.push({
      key: "admin-group",
      label: "用户管理",
      icon: <TeamOutlined />,
      children,
    });
  }

  items.push({
    key: "/profile",
    label: "个人中心",
    icon: <UserOutlined />,
  });

  const selectedKey =
    location.pathname === "/activities/new"
      ? "/activities/new"
      : location.pathname.startsWith("/admin/users")
        ? "/admin/users"
        : location.pathname.startsWith("/admin")
          ? "/admin/role-requests"
          : location.pathname.startsWith("/activities")
            ? "/activities"
            : location.pathname.startsWith("/dashboard")
              ? "/dashboard"
              : location.pathname.startsWith("/profile")
                ? "/profile"
                : undefined;

  return (
    <Menu
      mode="inline"
      selectedKeys={selectedKey ? [selectedKey] : EMPTY}
      items={items}
      onClick={({ key }) => navigate(key)}
    />
  );
}
