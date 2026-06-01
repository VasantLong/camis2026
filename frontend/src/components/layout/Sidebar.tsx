import { Badge, Menu } from "antd";
import {
  BellOutlined,
  HomeOutlined,
  PlusOutlined,
  UnorderedListOutlined,
  DashboardOutlined,
  UserOutlined,
  AuditOutlined,
  SettingOutlined,
  SearchOutlined,
  CheckOutlined,
  FileTextOutlined,
} from "@ant-design/icons";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import { useActivityCounts } from "@/hooks/useActivityQueries";

type MenuItem = {
  key: string;
  label: React.ReactNode;
  icon: React.ReactNode;
};

function badge(val: number | undefined) {
  if (val == null || val <= 0) return null;
  return <Badge count={val} size="small" style={{ marginLeft: 8 }} />;
}

export default function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const permissions = user?.permissions ?? [];
  const roles: string[] = user?.roles ?? [];
  const role = roles[0];
  const { data: c } = useActivityCounts();

  const items: MenuItem[] = [];

  // ── 工作台 (always first) ──
  items.push({
    key: "/index",
    label: "工作台",
    icon: <HomeOutlined />,
  });

  // ── Role-specific task items ──
  if (role === "Promoter") {
    if (permissions.includes("create_activity")) {
      items.push({
        key: "/activities/new",
        label: "新建立项",
        icon: <PlusOutlined />,
        disabled: !user?.contact_phone,
      });
    }
    items.push({
      key: "/activities",
      label: <>我的活动{badge(c?.my_activities)}</>,
      icon: <UnorderedListOutlined />,
    });
  } else if (role === "SecurityOfficer") {
    items.push({
      key: "/activities?status=待安保方案设计",
      label: <>待编制安保方案{badge(c?.pending_draft)}</>,
      icon: <FileTextOutlined />,
    });
    items.push({
      key: "/activities?status=待备案申请",
      label: <>待打包备案{badge(c?.pending_pack)}</>,
      icon: <CheckOutlined />,
    });
  } else if (role === "SecurityManager") {
    items.push({
      key: "/activities?status=待安保方案设计",
      label: <>待签署确认{badge(c?.pending_sign_confirm)}</>,
      icon: <CheckOutlined />,
    });
    items.push({
      key: "/activities?status=待备案申请",
      label: <>备案申请{badge(c?.pending_pack)}</>,
      icon: <FileTextOutlined />,
    });
  } else if (role === "GovLiaison") {
    items.push({
      key: "/activities?status=备案材料已交接",
      label: <>待审查材料{badge(c?.pending_review)}</>,
      icon: <SearchOutlined />,
    });
    items.push({
      key: "/activities?tab=completed",
      label: "审批记录",
      icon: <AuditOutlined />,
    });
  } else if (role === "AdminStaff" || role === "AdminManager") {
    items.push({
      key: "/dashboard",
      label: <>活动面板{badge(c?.total)}</>,
      icon: <DashboardOutlined />,
    });
    items.push({
      key: "/activities?tab=all",
      label: "全部活动",
      icon: <UnorderedListOutlined />,
    });
  } else if (role === "SuperAdmin") {
    items.push({
      key: "/admin/users",
      label: "用户管理",
      icon: <SettingOutlined />,
    });
    items.push({
      key: "/admin/role-requests",
      label: <>角色审批{badge(c?.pending_role_requests)}</>,
      icon: <AuditOutlined />,
    });
    items.push({
      key: "/activities?tab=all",
      label: <>全部活动{badge(c?.total_activities)}</>,
      icon: <UnorderedListOutlined />,
    });
  } else {
    // No role (new user) — show basic activity list if permitted
    if (permissions.includes("view_owned_activity") || permissions.includes("view_dashboard")) {
      items.push({
        key: "/activities",
        label: "全部活动",
        icon: <UnorderedListOutlined />,
      });
    }
    if (permissions.includes("view_dashboard")) {
      items.push({
        key: "/dashboard",
        label: "活动面板",
        icon: <DashboardOutlined />,
      });
    }
  }

  // ── 消息中心 ──
  items.push({
    key: "/notifications",
    label: "消息中心",
    icon: <BellOutlined />,
  });

  // ── 个人中心 (always last) ──
  items.push({
    key: "/profile",
    label: "个人中心",
    icon: <UserOutlined />,
  });

  // ── selected key ──
  const selectedKey =
    location.pathname === "/index"
      ? "/index"
      : location.pathname === "/activities/new"
        ? "/activities/new"
        : location.pathname.startsWith("/admin/users")
          ? "/admin/users"
          : location.pathname.startsWith("/admin")
            ? "/admin/role-requests"
            : location.pathname.startsWith("/activities")
              ? location.pathname + location.search
              : location.pathname.startsWith("/dashboard")
                ? "/dashboard"
                : location.pathname.startsWith("/notifications")
                  ? "/notifications"
                  : location.pathname.startsWith("/profile")
                    ? "/profile"
                    : undefined;

  return (
    <Menu
      mode="inline"
      selectedKeys={selectedKey ? [selectedKey] : []}
      items={items}
      onClick={({ key }) => navigate(key)}
    />
  );
}
