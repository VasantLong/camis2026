import { useState } from "react";
import {
  Card,
  Descriptions,
  Tag,
  Table,
  Select,
  Button,
  Alert,
  Typography,
  Spin,
  message,
} from "antd";
import { UserOutlined, SafetyOutlined, ClockCircleOutlined } from "@ant-design/icons";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { authApi } from "@/api/auth";
import { roleRequestApi } from "@/api/roleRequest";
import { useAuthStore } from "@/stores/authStore";
import { ROLE_LABEL_MAP, ROLE_DESC_MAP } from "@/utils/constants";

export default function ProfilePage() {
  const [selectedRoleId, setSelectedRoleId] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const setUser = useAuthStore((s) => s.setUser);

  const { data: user, isLoading } = useQuery({
    queryKey: ["me"],
    queryFn: () => authApi.me().then((r) => r.data),
  });

  const { data: roles = [] } = useQuery({
    queryKey: ["roles"],
    queryFn: () => authApi.getRoles().then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });

  const submitMutation = useMutation({
    mutationFn: (roleId: string) => roleRequestApi.submit(roleId).then((r) => r.data),
    onSuccess: () => {
      message.success("角色申请已提交，等待管理员审核");
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
    onError: (err: any) => {
      message.error(err?.detail || "提交失败");
    },
  });

  if (isLoading) {
    return (
      <div style={{ textAlign: "center", padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!user) return null;

  const pendingRR = user.pending_role_request;
  const hasRoles = user.roles.length > 0;

  return (
    <div style={{ padding: 24, maxWidth: 720 }}>
      <Typography.Title level={3} style={{ marginBottom: 24 }}>
        个人中心
      </Typography.Title>

      {/* basic info */}
      <Card style={{ marginBottom: 16 }}>
        <Descriptions
          title={
            <span>
              <UserOutlined style={{ marginRight: 8 }} />
              基本信息
            </span>
          }
          column={2}
          bordered
        >
          <Descriptions.Item label="邮箱">{user.email}</Descriptions.Item>
          <Descriptions.Item label="显示名称">
            {user.display_name || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={user.is_active ? "green" : "red"}>
              {user.is_active ? "正常" : "已禁用"}
            </Tag>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* role status */}
      <Card
        title={
          <span>
            <SafetyOutlined style={{ marginRight: 8 }} />
            角色与权限
          </span>
        }
        style={{ marginBottom: 16 }}
      >
        {hasRoles ? (
          <>
            <div style={{ marginBottom: 16 }}>
              {user.roles.map((role) => (
                <Tag key={role} color="blue" style={{ marginBottom: 4 }}>
                  {ROLE_LABEL_MAP[role] || role}
                </Tag>
              ))}
            </div>
            {Object.keys(user.role_permissions).length > 0 && (
              <div style={{ marginTop: 16 }}>
                <Typography.Text type="secondary" style={{ display: "block", marginBottom: 8 }}>
                  角色权限：
                </Typography.Text>
                <Table
                  size="small"
                  pagination={false}
                  dataSource={Object.entries(user.role_permissions).map(
                    ([role, perms]) => ({ role, perms })
                  )}
                  columns={[
                    {
                      title: "角色",
                      dataIndex: "role",
                      key: "role",
                      width: 160,
                      render: (r: string) => ROLE_LABEL_MAP[r] || r,
                    },
                    {
                      title: "权限",
                      dataIndex: "perms",
                      key: "perms",
                      render: (ps: string[]) => (
                        <>
                          {ps.map((p) => (
                            <Tag key={p} style={{ marginBottom: 2 }}>
                              {p}
                            </Tag>
                          ))}
                        </>
                      ),
                    },
                  ]}
                />
              </div>
            )}
          </>
        ) : pendingRR ? (
          <Alert
            type="info"
            icon={<ClockCircleOutlined />}
            title="等待审核"
            description={
              <>
                您申请了 <strong>{ROLE_LABEL_MAP[pendingRR.role_name] || pendingRR.role_name}</strong>{" "}
                角色，正在等待管理员审核。审核通过后即可使用对应功能。
              </>
            }
            showIcon
          />
        ) : (
          <div>
            <Alert
              type="warning"
              title="尚未分配角色"
              description="请选择您的职责并提交申请，管理员审核通过后即可使用系统功能。"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <div style={{ display: "flex", gap: 8 }}>
              <Select
                placeholder="选择角色"
                style={{ width: 280 }}
                value={selectedRoleId}
                onChange={setSelectedRoleId}
                options={roles.map((r) => ({
                  value: r.id,
                  label: `${r.label} (${r.name})`,
                }))}
              />
              <Button
                type="primary"
                disabled={!selectedRoleId}
                loading={submitMutation.isPending}
                onClick={() => selectedRoleId && submitMutation.mutate(selectedRoleId)}
              >
                提交申请
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
