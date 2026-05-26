import { useState } from "react";
import {
  Table,
  Tag,
  Button,
  Typography,
  Modal,
  Select,
  Space,
  Spin,
  Popconfirm,
  message,
} from "antd";
import { StopOutlined, CheckOutlined, DeleteOutlined, EditOutlined } from "@ant-design/icons";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminApi, type UserListItem } from "@/api/admin";
import { authApi } from "@/api/auth";
import { ROLE_LABEL_MAP } from "@/utils/constants";

export default function UserManagementPage() {
  const queryClient = useQueryClient();
  const [editingUser, setEditingUser] = useState<UserListItem | null>(null);
  const [selectedRoleIds, setSelectedRoleIds] = useState<string[]>([]);

  const { data: users = [], isLoading } = useQuery({
    queryKey: ["admin", "users"],
    queryFn: () => adminApi.getUsers().then((r) => r.data),
  });

  const { data: roles = [] } = useQuery({
    queryKey: ["roles"],
    queryFn: () => authApi.getRoles().then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      adminApi.updateUserStatus(id, active).then((r) => r.data),
    onSuccess: () => {
      message.success("状态已更新");
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
    onError: (err: any) => message.error(err?.detail || "操作失败"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => adminApi.deleteUser(id),
    onSuccess: () => {
      message.success("已删除");
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
    onError: (err: any) => message.error(err?.detail || "操作失败"),
  });

  const roleMutation = useMutation({
    mutationFn: ({ id, roleIds }: { id: string; roleIds: string[] }) =>
      adminApi.updateUserRoles(id, roleIds).then((r) => r.data),
    onSuccess: () => {
      message.success("角色已更新");
      setEditingUser(null);
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
    onError: (err: any) => message.error(err?.detail || "操作失败"),
  });

  const columns = [
    {
      title: "邮箱",
      dataIndex: "email",
      key: "email",
    },
    {
      title: "角色",
      dataIndex: "roles",
      key: "roles",
      render: (roles: string[]) => (
        <>
          {roles.length === 0 && <Tag>无角色</Tag>}
          {roles.map((r) => (
            <Tag key={r} color="blue">
              {ROLE_LABEL_MAP[r] || r}
            </Tag>
          ))}
        </>
      ),
    },
    {
      title: "状态",
      dataIndex: "is_active",
      key: "is_active",
      render: (active: boolean) =>
        active ? <Tag color="green">正常</Tag> : <Tag color="red">已禁用</Tag>,
    },
    {
      title: "注册时间",
      dataIndex: "created_at",
      key: "created_at",
      render: (t: string) => new Date(t).toLocaleString("zh-CN"),
    },
    {
      title: "操作",
      key: "actions",
      render: (_: unknown, record: UserListItem) => (
        <Space>
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => {
              setEditingUser(record);
              setSelectedRoleIds(
                roles
                  .filter((r) => record.roles.includes(r.name))
                  .map((r) => r.id)
              );
            }}
          >
            角色
          </Button>
          {record.is_active ? (
            <Popconfirm
              title="确认禁用该用户？"
              onConfirm={() =>
                statusMutation.mutate({ id: record.id, active: false })
              }
            >
              <Button size="small" icon={<StopOutlined />} danger>
                禁用
              </Button>
            </Popconfirm>
          ) : (
            <Popconfirm
              title="确认启用该用户？"
              onConfirm={() =>
                statusMutation.mutate({ id: record.id, active: true })
              }
            >
              <Button size="small" icon={<CheckOutlined />} type="primary">
                启用
              </Button>
            </Popconfirm>
          )}
          <Popconfirm
            title="确认删除该用户？此操作不可撤销"
            onConfirm={() => deleteMutation.mutate(record.id)}
          >
            <Button size="small" icon={<DeleteOutlined />} danger>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  if (isLoading) {
    return (
      <div style={{ textAlign: "center", padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={3}>用户管理</Typography.Title>
      <Table
        columns={columns}
        dataSource={users}
        rowKey="id"
        locale={{ emptyText: "暂无用户" }}
      />

      <Modal
        title="编辑角色"
        open={!!editingUser}
        onCancel={() => setEditingUser(null)}
        onOk={() => {
          if (editingUser) {
            roleMutation.mutate({ id: editingUser.id, roleIds: selectedRoleIds });
          }
        }}
        confirmLoading={roleMutation.isPending}
        okText="保存"
        cancelText="取消"
      >
        {editingUser && (
          <Typography.Paragraph>
            用户：<strong>{editingUser.display_name}</strong>
          </Typography.Paragraph>
        )}
        <Select
          mode="multiple"
          style={{ width: "100%" }}
          placeholder="选择角色"
          value={selectedRoleIds}
          onChange={setSelectedRoleIds}
          options={roles.map((r) => ({
            value: r.id,
            label: `${r.label} (${r.name})`,
          }))}
        />
      </Modal>
    </div>
  );
}
