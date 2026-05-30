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
      render: (text: string, record: ActivityResponse) => (
        <a onClick={() => navigate(`/activities/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: "类型",
      dataIndex: "type",
      key: "type",
      width: 120,
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 150,
      render: (status: string) => (
        <Tag color={STATUS_COLOR_MAP[status] || "default"}>{status}</Tag>
      ),
    },
    {
      title: "地点",
      dataIndex: "location",
      key: "location",
      width: 180,
      ellipsis: true,
    },
    {
      title: "主办方",
      dataIndex: "sponsor",
      key: "sponsor",
      width: 160,
      ellipsis: true,
    },
    {
      title: "预计时间",
      dataIndex: "estimated_time",
      key: "estimated_time",
      width: 170,
      render: (t: string) => dayjs(t).format("YYYY-MM-DD HH:mm"),
    },
    {
      title: "截止日期",
      dataIndex: "deadline",
      key: "deadline",
      width: 130,
      render: (t: string) => dayjs(t).format("YYYY-MM-DD"),
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 170,
      render: (t: string) => dayjs(t).format("YYYY-MM-DD HH:mm"),
    },
  ];

  return (
    <Table
      rowKey="id"
      columns={columns}
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
