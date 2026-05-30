import React, { useEffect, useState } from "react";
import { Spin } from "antd";
import { authApi } from "@/api/auth";
import { useAuthStore } from "@/stores/authStore";

export default function AuthInitializer({ children }: { children: React.ReactNode }) {
  const [checking, setChecking] = useState(true);
  const setAccessToken = useAuthStore((s) => s.setAccessToken);
  const setUser = useAuthStore((s) => s.setUser);
  const doneRef = React.useRef(false);

  useEffect(() => {
    let cancelled = false;
    if (!doneRef.current) {
      doneRef.current = true;
      (async () => {
        try {
          const { data } = await authApi.refresh();
          setAccessToken(data.access_token);
          const { data: user } = await authApi.me();
          setUser(user);
        } catch {
          // cookie absent or expired — stay unauthenticated
        }
        if (!cancelled) setChecking(false);
      })();
    } else {
      setChecking(false);
    }
    return () => {
      cancelled = true;
    };
  }, []);

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
