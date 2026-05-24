import { useEffect, useState } from "react";
import { Spin } from "antd";
import { authApi } from "@/api/auth";
import { useAuthStore } from "@/stores/authStore";

export default function AuthInitializer({ children }: { children: React.ReactNode }) {
  const [checking, setChecking] = useState(true);
  const setAccessToken = useAuthStore((s) => s.setAccessToken);
  const setUser = useAuthStore((s) => s.setUser);

  useEffect(() => {
    let cancelled = false;
    async function tryRefresh() {
      try {
        const { data } = await authApi.refresh();
        if (!cancelled) {
          setAccessToken(data.access_token);
          const { data: user } = await authApi.me();
          setUser(user);
        }
      } catch {
        // cookie absent or expired — stay unauthenticated
      } finally {
        if (!cancelled) setChecking(false);
      }
    }
    tryRefresh();
    return () => {
      cancelled = true;
    };
  }, [setAccessToken, setUser]);

  if (checking) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <Spin size="large" />
      </div>
    );
  }

  return <>{children}</>;
}
