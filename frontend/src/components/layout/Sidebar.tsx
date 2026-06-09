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
import { useActivityCounts, useUnreadCount } from "@/hooks/useActivityQueries";

type MenuItem = {
  key: string;
  label: React.ReactNode;
  icon: React.ReactNode;
};

function badge(val: number | undefined) {
  if (val == null || val <= 0) return null;
  return <Badge count={val} size="small" style={{ marginLeft: 8 }} />;
}

export default function Sidebar({ collapsed = false }: { collapsed?: boolean }) {
  const location = useLocation();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const permissions = user?.permissions ?? [];
  const roles: string[] = user?.roles ?? [];
  const role = roles[0];
  const { data: c } = useActivityCounts();
  const { data: unread } = useUnreadCount();

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
        // @ts-expect-error antd v6 MenuItem type missing disabled
        disabled: !user?.contact_phone,
      });
    }
    items.push({
      key: "/activities",
      label: <>我的活动{badge(c?.pending_plan)}</>,
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
      label: "活动面板",
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
    label: <>消息中心{badge(unread)}</>,
    icon: <BellOutlined />,
  });

  // ── 个人中心 (always last) ──
  items.push({
    key: "/profile",
    label: "个人中心",
    icon: <UserOutlined />,
  });

  // ── selected key ──
  const selectedKey = (() => {
    if (location.pathname === "/index") return "/index";
    if (location.pathname === "/activities/new") return "/activities/new";
    if (location.pathname.startsWith("/admin/users")) return "/admin/users";
    if (location.pathname.startsWith("/admin")) return "/admin/role-requests";
    if (location.pathname.startsWith("/activities")) {
      const sp = new URLSearchParams(location.search);
      const status = sp.get("status");
      const tab = sp.get("tab");
      if (status) return `/activities?status=${status}`;
      if (tab === "completed") return "/activities?tab=completed";
      if (tab === "all") return "/activities?tab=all";
      return "/activities";
    }
    if (location.pathname.startsWith("/dashboard")) return "/dashboard";
    if (location.pathname.startsWith("/notifications")) return "/notifications";
    if (location.pathname.startsWith("/profile")) return "/profile";
    return undefined;
  })();

  return (
    <Menu
      mode="inline"
      theme="dark"
      inlineCollapsed={collapsed}
      selectedKeys={selectedKey ? [selectedKey] : []}
      items={items}
      onClick={({ key }) => navigate(key)}
    />
  );
}
