import { Menu } from "antd";
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

export default function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const userPermissions = useAuthStore((s) => s.user?.permissions);
  const permissions = userPermissions ?? [];
  const EMPTY: string[] = [];

  const items: Array<{
    key: string;
    label: string;
    icon: React.ReactNode;
    children?: typeof items;
  }> = [];

  const canViewActivities =
    permissions.includes("view_owned_activity") || permissions.includes("view_dashboard");

  if (canViewActivities) {
    const children = [
      {
        key: "/activities",
        label: "全部活动",
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
      label: "活动面板",
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
      label: "角色审批",
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
