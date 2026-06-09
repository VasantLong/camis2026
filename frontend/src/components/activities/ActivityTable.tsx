import { Table, Tag } from "antd";
import { useNavigate, useSearchParams } from "react-router-dom";
import dayjs from "dayjs";
import { STATUS_COLOR_MAP } from "@/utils/constants";
import type { ActivityResponse } from "@/types/activity";

interface Props {
  data: ActivityResponse[];
  total: number;
  loading: boolean;
}

export default function ActivityTable({ data, total, loading }: Props) {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Number(searchParams.get("page") || "1");
  const size = Number(searchParams.get("size") || "20");

  const columns = [
    {
      title: "活动名称",
      dataIndex: "name",
      key: "name",
      fixed: "left" as const,
      render: (text: string, record: ActivityResponse) => (
        <a onClick={() => navigate(`/activities/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: "类型",
      dataIndex: "type",
      key: "type",
      width: 100,
      responsive: ["lg" as const],
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 140,
      render: (status: string) => (
        <Tag color={STATUS_COLOR_MAP[status] || "default"}>{status}</Tag>
      ),
    },
    {
      title: "地点",
      dataIndex: "location",
      key: "location",
      width: 160,
      ellipsis: true,
      responsive: ["md" as const],
    },
    {
      title: "主办方",
      dataIndex: "sponsor",
      key: "sponsor",
      width: 140,
      ellipsis: true,
      responsive: ["md" as const],
    },
    {
      title: "预计时间",
      dataIndex: "estimated_time",
      key: "estimated_time",
      width: 160,
      render: (t: string) => dayjs(t).format("YYYY-MM-DD HH:mm"),
      responsive: ["lg" as const],
    },
    {
      title: "截止日期",
      dataIndex: "deadline",
      key: "deadline",
      width: 120,
      render: (t: string) => dayjs(t).format("YYYY-MM-DD"),
      responsive: ["xl" as const],
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 160,
      render: (t: string) => dayjs(t).format("YYYY-MM-DD HH:mm"),
      responsive: ["xl" as const],
    },
  ];

  return (
    <Table
      rowKey="id"
      columns={columns}
      scroll={{ x: "max-content" }}
      dataSource={data}
      loading={loading}
      pagination={{
        current: page,
        pageSize: size,
        total,
        showSizeChanger: true,
        pageSizeOptions: ["10", "20", "50"],
        showTotal: (total) => `共 ${total} 条`,
        onChange: (p, s) => {
          const next = new URLSearchParams(searchParams);
          next.set("page", String(p));
          next.set("size", String(s));
          setSearchParams(next);
        },
      }}
    />
  );
}
