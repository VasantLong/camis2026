import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Form, Input, Button, Card, Typography, App } from "antd";
import { MailOutlined, LockOutlined, UserOutlined } from "@ant-design/icons";
import { authApi } from "@/api/auth";
import { useAuthStore } from "@/stores/authStore";

function useIsMobile() {
  const [mobile, setMobile] = useState(window.innerWidth < 768);
  useEffect(() => {
    const onResize = () => setMobile(window.innerWidth < 768);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);
  return mobile;
}

export default function RegisterPage() {
  const [loading, setLoading] = useState(false);
  const isMobile = useIsMobile();
  const { message } = App.useApp();
  const navigate = useNavigate();
  const setAccessToken = useAuthStore((s) => s.setAccessToken);
  const setUser = useAuthStore((s) => s.setUser);

  const onFinish = async (values: {
    email: string;
    password: string;
    display_name: string;
  }) => {
    setLoading(true);
    try {
      const { data } = await authApi.register(values);
      setAccessToken(data.access_token);
      const { data: user } = await authApi.me();
      setUser(user);
      message.success("注册成功");
      navigate("/profile", { replace: true });
    } catch (err: unknown) {
      const detail =
        (err as { detail?: string })?.detail || "注册失败，请重试";
      message.error(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        background: "linear-gradient(rgba(0,0,0,0.25), rgba(0,0,0,0.15)), url(/background.png) center / cover no-repeat",
        padding: 24,
      }}
    >
      <div
        style={{
          display: "flex",
          borderRadius: 12,
          overflow: "hidden",
          boxShadow: "0 8px 40px rgba(0,0,0,0.15)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
        }}
      >
        {!isMobile && (
          <div style={{ width: 280, display: "flex", overflow: "hidden" }}>
            <img
              src="/logo-vertical.png"
              alt="CAMIS"
              style={{ width: "100%", height: "100%", objectFit: "cover", borderTopLeftRadius: 12, borderBottomLeftRadius: 12 }}
            />
          </div>
        )}
        <Card
          style={{
            width: isMobile ? "100%" : 400,
            borderRadius: 0,
            border: "none",
            borderLeft: isMobile ? "none" : "1px solid rgba(255,255,255,0.3)",
            display: "flex",
            alignItems: "center",
            background: "rgba(255,255,255,0.75)",
            backdropFilter: "blur(8px)",
          }}
          styles={{ body: { padding: "32px 32px 24px", width: "100%" } }}
        >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 12, marginBottom: 20 }}>
          <img src="/logo.png" alt="" style={{ height: 40, width: 40, objectFit: "contain" }} />
          <Typography.Title level={3} style={{ margin: 0 }}>
            注册 CAMIS
          </Typography.Title>
        </div>
        <Form layout="vertical" onFinish={onFinish} size="large">
          <Form.Item
            name="email"
            rules={[
              { required: true, message: "请输入邮箱" },
              { type: "email", message: "邮箱格式不正确" },
            ]}
          >
            <Input prefix={<MailOutlined />} placeholder="邮箱" />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[{ required: true, message: "请输入密码" }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Form.Item
            name="display_name"
            rules={[{ required: true, message: "请输入显示名称" }]}
          >
            <Input prefix={<UserOutlined />} placeholder="显示名称" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              注册
            </Button>
          </Form.Item>
        </Form>
        <div style={{ textAlign: "center" }}>
          已有帐号？<Link to="/login">去登录</Link>
        </div>
      </Card>
      </div>
    </div>
  );
}
