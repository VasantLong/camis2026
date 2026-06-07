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
  Input,
  message,
} from "antd";
import { StopOutlined, CheckOutlined, EditOutlined, LockOutlined } from "@ant-design/icons";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminApi, type UserListItem } from "@/api/admin";
import { authApi } from "@/api/auth";
import { useAuthStore } from "@/stores/authStore";
import { ROLE_LABEL_MAP } from "@/utils/constants";

export default function UserManagementPage() {
  const queryClient = useQueryClient();
  const currentUserId = useAuthStore((s) => s.user?.id);
  const [editingUser, setEditingUser] = useState<UserListItem | null>(null);
  const [selectedRoleIds, setSelectedRoleIds] = useState<string[]>([]);
  const [detailUser, setDetailUser] = useState<UserListItem | null>(null);
  const [archivingUser, setArchivingUser] = useState<UserListItem | null>(null);
  const [archiveReason, setArchiveReason] = useState("");
  const [keyword, setKeyword] = useState("");
  const [searchValue, setSearchValue] = useState("");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [filterRole, setFilterRole] = useState<string | undefined>();
  const [filterStatus, setFilterStatus] = useState<string | undefined>();

  const { data: overview, isFetching: overviewLoading } = useQuery({
    queryKey: ["admin", "users", detailUser?.id, "overview"],
    queryFn: () =>
      adminApi.getUserOverview(detailUser!.id).then((r) => r.data),
    enabled: !!detailUser,
  });

  const { data: users = [], isLoading } = useQuery({
    queryKey: ["admin", "users", keyword, sortOrder, filterRole, filterStatus],
    queryFn: () => adminApi.getUsers(keyword || undefined, sortOrder, filterRole, filterStatus).then((r) => r.data),
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
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      adminApi.archiveUser(id, reason),
    onSuccess: () => {
      message.success("已归档，操作不可撤回");
      setArchivingUser(null);
      setArchiveReason("");
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
            <Tag color="volcano">已归档</Tag>
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
      render: (_: unknown, record: UserListItem) => {
        if (record.is_archived) {
          return (
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              已封存
            </Typography.Text>
          );
        }
        if (record.id === currentUserId) {
          return (
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              当前用户
            </Typography.Text>
          );
        }
        return (
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
            <Button
              size="small"
              icon={<LockOutlined />}
              danger
              onClick={(e) => {
                e.stopPropagation();
                setArchivingUser(record);
                setArchiveReason("");
              }}
            >
              归档
            </Button>
          </Space>
        );
      },
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
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Typography.Title level={3} style={{ margin: 0 }}>用户管理</Typography.Title>
        <Space wrap>
          <Input.Search
            placeholder="搜索邮箱或显示名称"
            allowClear
            style={{ width: 280 }}
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            onSearch={(v) => setKeyword(v)}
          />
          <Select
            placeholder="角色"
            allowClear
            value={filterRole}
            onChange={(v) => setFilterRole(v)}
            style={{ width: 120 }}
            options={roles.map((r) => ({ value: r.name, label: r.label }))}
          />
          <Select
            placeholder="状态"
            allowClear
            value={filterStatus}
            onChange={(v) => setFilterStatus(v)}
            style={{ width: 100 }}
            options={[
              { value: "active", label: "正常" },
              { value: "disabled", label: "已禁用" },
              { value: "archived", label: "已归档" },
            ]}
          />
          <Select
            value={sortOrder}
            onChange={(v) => setSortOrder(v)}
            style={{ width: 100 }}
            options={[
              { value: "desc", label: "最新优先" },
              { value: "asc", label: "最早优先" },
            ]}
          />
          {(keyword || sortOrder !== "desc" || filterRole || filterStatus) && (
            <Button
              onClick={() => { setKeyword(""); setSearchValue(""); setSortOrder("desc"); setFilterRole(undefined); setFilterStatus(undefined); }}
            >
              重置
            </Button>
          )}
        </Space>
      </div>
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
            {overview.is_archived && (
              <div style={{
                background: "#fff2f0",
                border: "1px solid #ffccc7",
                borderRadius: 8,
                padding: "12px 16px",
                marginBottom: 16,
              }}>
                <Typography.Text strong style={{ color: "#ff4d4f", fontSize: 14 }}>
                  此用户已于 {overview.archived_at ? new Date(overview.archived_at).toLocaleString("zh-CN") : "—"} 归档封存
                </Typography.Text>
                {overview.archive_reason && (
                  <Typography.Paragraph style={{ marginTop: 8, marginBottom: 0 }}>
                    归档凭证：{overview.archive_reason}
                  </Typography.Paragraph>
                )}
              </div>
            )}
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
                    <Tag color="volcano">已归档</Tag>
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

      <Modal
        title="确认归档"
        open={!!archivingUser}
        onCancel={() => setArchivingUser(null)}
        onOk={() => {
          if (archivingUser) {
            archiveMutation.mutate({ id: archivingUser.id, reason: archiveReason });
          }
        }}
        confirmLoading={archiveMutation.isPending}
        okText="确认归档"
        cancelText="取消"
        okButtonProps={{ danger: true }}
      >
        {archivingUser && (
          <>
            <Typography.Paragraph style={{ marginBottom: 12 }}>
              归档用户 <strong>{archivingUser.display_name}</strong>（{archivingUser.email}），
              此操作<strong style={{ color: "#ff4d4f" }}>不可撤回</strong>。
            </Typography.Paragraph>
            <Typography.Text type="secondary" style={{ display: "block", marginBottom: 8 }}>
              归档凭证（原因说明、证明材料编号等）：
            </Typography.Text>
            <Input.TextArea
              rows={3}
              placeholder="请填写归档原因或凭证编号"
              value={archiveReason}
              onChange={(e) => setArchiveReason(e.target.value)}
            />
          </>
        )}
      </Modal>
    </div>
  );
}
