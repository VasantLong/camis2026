import { Descriptions, Empty, Tag, Typography } from "antd";
import dayjs from "dayjs";
import type { SchemaResponse, FieldDef } from "@/types/template";

interface Props {
  schema: SchemaResponse;
}

function formatValue(v: unknown, field: FieldDef): string {
  if (v === null || v === undefined || v === "") return "—";
  if (field.ui_type === "date") {
    const d = dayjs(v as string);
    return d.isValid() ? d.format("YYYY-MM-DD") : String(v);
  }
  if (field.ui_type === "number") return String(v);
  if (field.ui_type === "repeater") {
    try {
      const arr = typeof v === "string" ? JSON.parse(v) : v;
      return Array.isArray(arr) ? arr.join("、") : String(v);
    } catch {
      return String(v);
    }
  }
  return String(v);
}

export default function VersionSnapshot({ schema }: Props) {
  const { snapshot_data, current_version, fields, display_name } = schema;

  if (!snapshot_data || current_version === null) {
    return <Empty description={`暂无已生成的${display_name}`} />;
  }

  return (
    <div>
      <Typography.Text type="secondary" style={{ marginBottom: 12, display: "block" }}>
        当前版本：<Tag color="blue">v{current_version}</Tag>
      </Typography.Text>
      <Descriptions bordered column={2} size="small">
        {fields.map((f) => (
          <Descriptions.Item key={f.name} label={f.ui_label}>
            {formatValue(snapshot_data[f.name], f)}
          </Descriptions.Item>
        ))}
      </Descriptions>
    </div>
  );
}
