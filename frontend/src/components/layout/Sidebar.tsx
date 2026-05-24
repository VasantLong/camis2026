import { Menu } from "antd";
import {
  UnorderedListOutlined,
  PlusOutlined,
  DashboardOutlined,
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

  if (permissions.includes("view_owned_activity")) {
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

  const selectedKey =
    location.pathname === "/activities/new"
      ? "/activities/new"
      : location.pathname.startsWith("/activities")
        ? "/activities"
        : location.pathname.startsWith("/dashboard")
          ? "/dashboard"
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
