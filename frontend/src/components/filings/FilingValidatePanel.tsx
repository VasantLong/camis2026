import { Table, Tag } from "antd";
import { CheckCircleOutlined, CloseCircleOutlined } from "@ant-design/icons";
import type { MaterialValidation } from "@/types/filing";

interface Props {
  data: MaterialValidation[];
}

export default function FilingValidatePanel({ data }: Props) {
  const columns = [
    { title: "材料名称", dataIndex: "name", key: "name" },
    {
      title: "合规状态",
      dataIndex: "is_qualified",
      key: "is_qualified",
      width: 120,
      render: (v: boolean) =>
        v ? (
          <Tag icon={<CheckCircleOutlined />} color="success">合格</Tag>
        ) : (
          <Tag icon={<CloseCircleOutlined />} color="error">不合格</Tag>
        ),
    },
    {
      title: "电子签名",
      dataIndex: "has_signature",
      key: "has_signature",
      width: 120,
      render: (v: boolean) =>
        v ? (
          <Tag icon={<CheckCircleOutlined />} color="success">已签署</Tag>
        ) : (
          <Tag icon={<CloseCircleOutlined />} color="warning">未签署</Tag>
        ),
    },
    {
      title: "问题",
      dataIndex: "issues",
      key: "issues",
      render: (issues: string[]) =>
        issues.length > 0
          ? issues.map((i) => <Tag key={i} color="error">{i}</Tag>)
          : "—",
    },
  ];

  return <Table rowKey="material_id" columns={columns} dataSource={data} />;
}
