import { Table, Tag, Card } from "antd";
import dayjs from "dayjs";
import { useNavigate } from "react-router-dom";
import { STATUS_COLOR_MAP } from "@/utils/constants";
import type { AnomalyEntry } from "@/types/dashboard";

interface Props {
  anomalies: AnomalyEntry[];
}

export default function AnomalyList({ anomalies }: Props) {
  const navigate = useNavigate();

  const columns = [
    {
      title: "活动名称",
      dataIndex: "name",
      key: "name",
      render: (text: string, record: AnomalyEntry) => (
        <a onClick={() => navigate(`/activities/${record.activity_id}`)}>
          {text}
        </a>
      ),
    },
    {
      title: "变更状态",
      dataIndex: "change_status",
      key: "change_status",
      width: 120,
      render: (s: string) => (
        <Tag color={STATUS_COLOR_MAP[s] || "default"}>{s}</Tag>
      ),
    },
    {
      title: "原因",
      dataIndex: "change_reason",
      key: "change_reason",
      ellipsis: true,
    },
    {
      title: "变更时间",
      dataIndex: "changed_at",
      key: "changed_at",
      width: 170,
      render: (t: string) => dayjs(t).format("YYYY-MM-DD HH:mm"),
    },
  ];

  return (
    <Card title="最近异常" style={{ marginBottom: 16 }}>
      <Table
        rowKey="activity_id"
        columns={columns}
        dataSource={anomalies}
        pagination={false}
      />
    </Card>
  );
}
