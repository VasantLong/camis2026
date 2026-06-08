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

function isFieldVisible(field: FieldDef, snapshot: Record<string, unknown> | null): boolean {
  if (!field.condition) return true;
  const parts = field.condition.split(/\s*(==|!=)\s*/);
  if (parts.length === 3) {
    const key = parts[0].trim();
    const op = parts[1].trim();
    const val = parts[2].trim().replace(/['"]/g, "");
    const cur = snapshot?.[key];
    if (op === "==") return cur === val;
    if (op === "!=") return cur !== val;
  }
  return true;
}

export default function VersionSnapshot({ schema }: Props) {
  const { snapshot_data, current_version, fields, display_name } = schema;

  if (!snapshot_data || current_version === null) {
    return <Empty description={`暂无已生成的${display_name}`} />;
  }

  const visibleFields = fields.filter(f => isFieldVisible(f, snapshot_data));

  return (
    <div>
      <Typography.Text type="secondary" style={{ marginBottom: 12, display: "block" }}>
        当前版本：<Tag color="blue">v{current_version}</Tag>
      </Typography.Text>
      <Descriptions bordered column={2} size="small">
        {visibleFields.map((f) => (
          <Descriptions.Item key={f.name} label={f.ui_label}>
            {formatValue(snapshot_data[f.name], f)}
          </Descriptions.Item>
        ))}
      </Descriptions>
    </div>
  );
}
