import { useState } from "react";
import { Layout, Button, Dropdown } from "antd";
import { LogoutOutlined, UserOutlined, BulbOutlined } from "@ant-design/icons";
import { Outlet, useNavigate } from "react-router-dom";
import { authApi } from "@/api/auth";
import { useAuthStore } from "@/stores/authStore";
import { useTheme } from "@/hooks/useTheme";
import Sidebar from "./Sidebar";
import HeaderNotifications from "./HeaderNotifications";

const { Header, Sider, Content } = Layout;

export default function AppLayout() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const [collapsed, setCollapsed] = useState(true);
  const { isDark, toggle: toggleTheme } = useTheme();

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch {
      // ignore
    }
    clearAuth();
    navigate("/login");
  };

  return (
    <Layout style={{ height: "100vh" }}>
      <Sider
        collapsible
        trigger={null}
        collapsed={collapsed}
        collapsedWidth={72}
        breakpoint="lg"
        onBreakpoint={(broken) => { if (broken) setCollapsed(true); }}
        style={{
          background: isDark ? undefined : "#1a1f2e",
          overflow: "hidden",
          height: "100vh",
          position: "fixed",
          left: 0,
          top: 0,
          boxShadow: "2px 0 8px rgba(0,0,0,0.08)",
          bottom: 0,
          zIndex: 100,
          transition: "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
        }}
        onMouseEnter={() => setCollapsed(false)}
        onMouseLeave={() => setCollapsed(true)}
      >
        <div
          style={{
            height: 64,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: collapsed ? 14 : 16,
            transition: "padding 0.2s",
          }}
        >
          <img
            src="/logo.png"
            alt="CAMIS"
            style={{
              height: collapsed ? 44 : 56,
              width: collapsed ? 44 : 56,
              transition: "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
              objectFit: "contain",
            }}
          />
        </div>
        <Sidebar collapsed={collapsed} />
      </Sider>
      <div style={{ width: collapsed ? 72 : 200, transition: "width 0.2s cubic-bezier(0.4, 0, 0.2, 1)", flexShrink: 0 }} />
      <Layout style={{ overflow: "hidden" }}>
        <Header
          style={{
            background: "#fff",
            padding: "0 24px",
            display: "flex",
            justifyContent: "flex-end",
            alignItems: "center",
          }}
        >
          <Button
            type="text"
            icon={<BulbOutlined />}
            onClick={toggleTheme}
            style={{ color: "inherit", marginRight: 8 }}
            title={isDark ? "切换浅色主题" : "切换深色主题"}
          />
          <HeaderNotifications />
        <Dropdown
            menu={{
              items: [
                {
                  key: "logout",
                  label: "退出登录",
                  icon: <LogoutOutlined />,
                  onClick: handleLogout,
                },
              ],
            }}
          >
            <Button icon={<UserOutlined />}>
              {user?.display_name || "用户"}
            </Button>
          </Dropdown>
        </Header>
        <Content style={{ overflow: "auto" }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
