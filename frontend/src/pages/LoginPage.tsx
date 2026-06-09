import { useState } from "react";
import { Link, useNavigate, useLocation, useSearchParams } from "react-router-dom";
import { Form, Input, Button, Card, Typography, Alert, message } from "antd";
import { MailOutlined, LockOutlined } from "@ant-design/icons";
import { authApi } from "@/api/auth";
import { useAuthStore } from "@/stores/authStore";

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const setAccessToken = useAuthStore((s) => s.setAccessToken);
  const setUser = useAuthStore((s) => s.setUser);

  const from =
    (location.state as { from?: { pathname: string } })?.from?.pathname ||
    "/index";

  const onFinish = async (values: { email: string; password: string }) => {
    setLoading(true);
    try {
      const { data } = await authApi.login(values);
      setAccessToken(data.access_token);
      const { data: user } = await authApi.me();
      setUser(user);
      message.success("登录成功");
      navigate(from, { replace: true });
    } catch (err: unknown) {
      const detail = (err as { detail?: string })?.detail || "登录失败，请重试";
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
        <div
          style={{
            width: 280,
            display: "flex",
            overflow: "hidden",
          }}
        >
          <img
            src="/logo-vertical.png"
            alt="CAMIS"
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              borderTopLeftRadius: 12,
              borderBottomLeftRadius: 12,
            }}
          />
        </div>
        <Card
          style={{
            width: 400,
            borderRadius: 0,
            border: "none",
            borderLeft: "1px solid rgba(255,255,255,0.3)",
            display: "flex",
            alignItems: "center",
            background: "rgba(255,255,255,0.75)",
            backdropFilter: "blur(8px)",
          }}
          styles={{ body: { padding: "32px 32px 24px", width: "100%" } }}
        >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 12, marginBottom: 20 }}>
          <img
            src="/logo.png"
            alt=""
            style={{ height: 40, width: 40, objectFit: "contain" }}
          />
          <Typography.Title level={3} style={{ margin: 0 }}>
            欢迎使用 CAMIS
          </Typography.Title>
        </div>
        {searchParams.get("verified") === "1" && (
          <Alert
            type="success"
            message="邮箱验证成功，请用新邮箱重新登录"
            style={{ marginBottom: 16 }}
          />
        )}
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
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              登录
            </Button>
          </Form.Item>
        </Form>
        <div style={{ textAlign: "center" }}>
          没有帐号？<Link to="/register">立即注册</Link>
        </div>
      </Card>
      </div>
    </div>
  );
}
