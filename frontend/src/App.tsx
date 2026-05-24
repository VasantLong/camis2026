import { Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider, App as AntApp } from "antd";
import zhCN from "antd/locale/zh_CN";
import AuthInitializer from "@/components/auth/AuthInitializer";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import NotFoundPage from "@/pages/NotFoundPage";
import ForbiddenPage from "@/pages/ForbiddenPage";
import ActivityListPage from "@/pages/activities/ActivityListPage";

export default function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <AntApp>
        <AuthInitializer>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/403" element={<ForbiddenPage />} />
            <Route
              path="/"
              element={<Navigate to="/activities" replace />}
            />
            <Route
              path="/activities"
              element={
                <ProtectedRoute requiredPermissions={["view_owned_activity"]}>
                  <ActivityListPage />
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </AuthInitializer>
      </AntApp>
    </ConfigProvider>
  );
}
