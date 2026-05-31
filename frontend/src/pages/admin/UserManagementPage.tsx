import { useState } from "react";
import {
  Table,
  Tag,
  Typography,
  Button,
  Modal,
  Select,
  Space,
  Drawer,
  Descriptions,
  Timeline,
  List,
  Spin,
  Popconfirm,
  message,
} from "antd";
import { StopOutlined, CheckOutlined, EditOutlined, LockOutlined, UndoOutlined } from "@ant-design/icons";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminApi, type UserListItem, type UserOverview } from "@/api/admin";
import { authApi } from "@/api/auth";
import { ROLE_LABEL_MAP } from "@/utils/constants";

export default function UserManagementPage() {
  const queryClient = useQueryClient();
  const [editingUser, setEditingUser] = useState<UserListItem | null>(null);
  const [selectedRoleIds, setSelectedRoleIds] = useState<string[]>([]);
  const [detailUser, setDetailUser] = useState<UserListItem | null>(null);

  const { data: overview, isFetching: overviewLoading } = useQuery({
    queryKey: ["admin", "users", detailUser?.id, "overview"],
    queryFn: () =>
      adminApi.getUserOverview(detailUser!.id).then((r) => r.data),
    enabled: !!detailUser,
  });

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

  const archiveMutation = useMutation({
    mutationFn: (id: string) => adminApi.archiveUser(id),
    onSuccess: () => {
      message.success("已归档");
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
    onError: (err: any) => message.error(err?.detail || "操作失败"),
  });

  const unarchiveMutation = useMutation({
    mutationFn: (id: string) => adminApi.unarchiveUser(id),
    onSuccess: () => {
      message.success("已取消归档");
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
      title: "用户",
      dataIndex: "email",
      key: "email",
      render: (_: string, record: UserListItem) => (
        <span>
          {record.email}
          <Typography.Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
            ({record.display_name})
          </Typography.Text>
        </span>
      ),
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
      key: "status",
      render: (_: unknown, record: UserListItem) => (
        <Space size={4}>
          {record.is_archived ? (
            <Tag color="default">已归档</Tag>
          ) : record.is_active ? (
            <Tag color="green">正常</Tag>
          ) : (
            <Tag color="red">已禁用</Tag>
          )}
        </Space>
      ),
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
            onClick={(e) => {
              e.stopPropagation();
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
              <Button size="small" icon={<StopOutlined />} danger onClick={(e) => e.stopPropagation()}>
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
              <Button size="small" icon={<CheckOutlined />} type="primary" onClick={(e) => e.stopPropagation()}>
                启用
              </Button>
            </Popconfirm>
          )}
          {record.is_archived ? (
            <Popconfirm
              title="确认取消归档该用户？"
              onConfirm={() => unarchiveMutation.mutate(record.id)}
            >
              <Button size="small" icon={<UndoOutlined />} onClick={(e) => e.stopPropagation()}>
                取消归档
              </Button>
            </Popconfirm>
          ) : (
            <Popconfirm
              title="确认归档该用户？归档后该用户将无法登录"
              onConfirm={() => archiveMutation.mutate(record.id)}
            >
              <Button size="small" icon={<LockOutlined />} danger onClick={(e) => e.stopPropagation()}>
                归档
              </Button>
            </Popconfirm>
          )}
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
        onRow={(record) => ({
          style: { cursor: "pointer" },
          onClick: () => {
            setDetailUser(record);
          },
        })}
      />

      <Drawer
        title="用户详情"
        open={!!detailUser}
        onClose={() => setDetailUser(null)}
        size="large"
      >
        {overviewLoading ? (
          <Spin />
        ) : overview ? (
          <>
            <Descriptions column={1} bordered size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="UUID">
                <Typography.Text code style={{ fontSize: 11 }}>
                  {overview.id}
                </Typography.Text>
              </Descriptions.Item>
              <Descriptions.Item label="邮箱">{overview.email}</Descriptions.Item>
              <Descriptions.Item label="显示名称">{overview.display_name}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Space size={4}>
                  {overview.is_archived ? (
                    <Tag color="default">已归档</Tag>
                  ) : overview.is_active ? (
                    <Tag color="green">正常</Tag>
                  ) : (
                    <Tag color="red">已禁用</Tag>
                  )}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="角色">
                {overview.roles.map((r) => (
                  <Tag key={r} color="blue">{ROLE_LABEL_MAP[r] || r}</Tag>
                ))}
              </Descriptions.Item>
              <Descriptions.Item label="注册时间">
                {new Date(overview.created_at).toLocaleString("zh-CN")}
              </Descriptions.Item>
            </Descriptions>

            <Typography.Title level={5}>登录记录</Typography.Title>
            {overview.login_history.length > 0 ? (
              <Timeline
                items={overview.login_history.slice(0, 10).map((h) => ({
                  color: h.success ? "green" : "red",
                  content: (
                    <span>
                      {new Date(h.created_at).toLocaleString("zh-CN")}
                      {" "}
                      <Tag color={h.success ? "green" : "red"}>
                        {h.success ? "成功" : "失败"}
                      </Tag>
                    </span>
                  ),
                }))}
              />
            ) : (
              <Typography.Text type="secondary">暂无记录</Typography.Text>
            )}

            <Typography.Title level={5} style={{ marginTop: 16 }}>
              最近操作
            </Typography.Title>
            {overview.recent_actions.length > 0 ? (
              <List
                size="small"
                dataSource={overview.recent_actions.slice(0, 15)}
                renderItem={(a) => (
                  <List.Item>
                    <span>
                      {new Date(a.created_at).toLocaleString("zh-CN")}
                      {" — "}
                      {a.action}
                    </span>
                  </List.Item>
                )}
              />
            ) : (
              <Typography.Text type="secondary">暂无记录</Typography.Text>
            )}
          </>
        ) : null}
      </Drawer>

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
