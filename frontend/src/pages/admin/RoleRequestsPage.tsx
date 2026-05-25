import { useState } from "react";
import {
  Table,
  Button,
  Tag,
  Typography,
  Modal,
  Input,
  Space,
  Spin,
  message,
} from "antd";
import { CheckOutlined, CloseOutlined } from "@ant-design/icons";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminApi, type RoleRequestItem } from "@/api/admin";
import { ROLE_LABEL_MAP } from "@/utils/constants";

export default function RoleRequestsPage() {
  const queryClient = useQueryClient();
  const [rejectTarget, setRejectTarget] = useState<RoleRequestItem | null>(null);
  const [rejectComment, setRejectComment] = useState("");

  const { data = [], isLoading } = useQuery({
    queryKey: ["admin", "role-requests"],
    queryFn: () => adminApi.getRoleRequests().then((r) => r.data),
    refetchInterval: 30_000,
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => adminApi.approveRequest(id).then((r) => r.data),
    onSuccess: () => {
      message.success("已批准");
      queryClient.invalidateQueries({ queryKey: ["admin", "role-requests"] });
    },
    onError: (err: any) => message.error(err?.detail || "操作失败"),
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, comment }: { id: string; comment: string }) =>
      adminApi.rejectRequest(id, comment).then((r) => r.data),
    onSuccess: () => {
      message.success("已驳回");
      setRejectTarget(null);
      setRejectComment("");
      queryClient.invalidateQueries({ queryKey: ["admin", "role-requests"] });
    },
    onError: (err: any) => message.error(err?.detail || "操作失败"),
  });

  const columns = [
    {
      title: "用户",
      dataIndex: "user_id",
      key: "user_id",
      width: 280,
      render: (id: string) => (
        <Typography.Text code style={{ fontSize: 12 }}>
          {id}
        </Typography.Text>
      ),
    },
    {
      title: "申请角色",
      dataIndex: "role_name",
      key: "role_name",
      render: (name: string) => (
        <Tag color="blue">{ROLE_LABEL_MAP[name] || name}</Tag>
      ),
    },
    {
      title: "申请时间",
      dataIndex: "created_at",
      key: "created_at",
      render: (t: string) => new Date(t).toLocaleString("zh-CN"),
    },
    {
      title: "操作",
      key: "actions",
      width: 200,
      render: (_: unknown, record: RoleRequestItem) => (
        <Space>
          <Button
            type="primary"
            size="small"
            icon={<CheckOutlined />}
            loading={approveMutation.isPending}
            onClick={() => approveMutation.mutate(record.id)}
          >
            批准
          </Button>
          <Button
            danger
            size="small"
            icon={<CloseOutlined />}
            onClick={() => {
              setRejectTarget(record);
              setRejectComment("");
            }}
          >
            驳回
          </Button>
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
      <Typography.Title level={3}>角色审批</Typography.Title>
      <Table
        columns={columns}
        dataSource={data}
        rowKey="id"
        locale={{ emptyText: "暂无待审批的申请" }}
      />

      <Modal
        title="驳回角色申请"
        open={!!rejectTarget}
        onCancel={() => setRejectTarget(null)}
        onOk={() => {
          if (rejectTarget && rejectComment.trim()) {
            rejectMutation.mutate({
              id: rejectTarget.id,
              comment: rejectComment.trim(),
            });
          }
        }}
        confirmLoading={rejectMutation.isPending}
        okText="确认驳回"
        okButtonProps={{ danger: true }}
        cancelText="取消"
      >
        <Typography.Paragraph style={{ marginBottom: 8 }}>
          申请角色：{rejectTarget && (ROLE_LABEL_MAP[rejectTarget.role_name] || rejectTarget.role_name)}
        </Typography.Paragraph>
        <Input.TextArea
          placeholder="驳回原因"
          rows={3}
          value={rejectComment}
          onChange={(e) => setRejectComment(e.target.value)}
        />
      </Modal>
    </div>
  );
}
