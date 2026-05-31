import { Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider, App as AntApp } from "antd";
import zhCN from "antd/locale/zh_CN";
import AuthInitializer from "@/components/auth/AuthInitializer";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import AppLayout from "@/components/layout/AppLayout";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import NotFoundPage from "@/pages/NotFoundPage";
import ForbiddenPage from "@/pages/ForbiddenPage";
import ActivityListPage from "@/pages/activities/ActivityListPage";
import ActivityCreatePage from "@/pages/activities/ActivityCreatePage";
import ActivityDetailPage from "@/pages/activities/ActivityDetailPage";
import DashboardPage from "@/pages/dashboard/DashboardPage";
import ProfilePage from "@/pages/profile/ProfilePage";
import RoleRequestsPage from "@/pages/admin/RoleRequestsPage";
import UserManagementPage from "@/pages/admin/UserManagementPage";
import HomePage from "@/pages/HomePage";

export default function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <AntApp>
        <AuthInitializer>
          <Routes>
            {/* public routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/403" element={<ForbiddenPage />} />

            {/* protected routes — inside AppLayout */}
            <Route element={<AppLayout />}>
              <Route path="/" element={<Navigate to="/index" replace />} />
              <Route path="/index" element={<ProtectedRoute><HomePage /></ProtectedRoute>} />
              <Route
                path="/activities"
                element={
                  <ProtectedRoute
                    requiredPermissions={["view_owned_activity", "view_dashboard"]}
                  >
                    <ActivityListPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/activities/new"
                element={
                  <ProtectedRoute requiredPermissions={["create_activity"]}>
                    <ActivityCreatePage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/activities/:id"
                element={
                  <ProtectedRoute
                    requiredPermissions={["view_owned_activity"]}
                  >
                    <ActivityDetailPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute requiredPermissions={["view_dashboard"]}>
                    <DashboardPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/profile"
                element={
                  <ProtectedRoute>
                    <ProfilePage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/role-requests"
                element={
                  <ProtectedRoute requiredPermissions={["manage_users"]}>
                    <RoleRequestsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/users"
                element={
                  <ProtectedRoute requiredPermissions={["administer_users"]}>
                    <UserManagementPage />
                  </ProtectedRoute>
                }
              />
            </Route>

            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </AuthInitializer>
      </AntApp>
    </ConfigProvider>
  );
}
