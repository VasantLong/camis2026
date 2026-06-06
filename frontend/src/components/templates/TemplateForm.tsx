import { useState, useEffect, useCallback } from "react";
import {
  Form,
  Input,
  InputNumber,
  DatePicker,
  Select,
  Checkbox,
  Button,
  Space,
  Upload,
  App,
} from "antd";
import { PlusOutlined, DeleteOutlined, UploadOutlined } from "@ant-design/icons";
import type { SchemaResponse, FieldDef } from "@/types/template";
import { documentsApi } from "@/api/documents";
import dayjs from "dayjs";

interface Props {
  activityId: string;
  schema: SchemaResponse;
  loading?: boolean;
  onSaveDraft: (data: Record<string, unknown>) => Promise<void>;
  onSubmit: (data: Record<string, unknown>) => Promise<void>;
}

export default function TemplateForm({ activityId, schema, loading, onSaveDraft, onSubmit }: Props) {
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const { message } = App.useApp();

  useEffect(() => {
    if (schema.has_draft && schema.draft_data) {
      const draft: Record<string, unknown> = {};
      for (const f of schema.fields) {
        const val = schema.draft_data[f.name];
        if (val !== undefined) {
          draft[f.name] = f.ui_type === "date" && typeof val === "string" ? dayjs(val) : val;
        }
      }
      form.setFieldsValue(draft);
    }
  }, [schema, form]);

  const visibleFields = useCallback(
    (fields: FieldDef[]) => {
      const formValues = form.getFieldsValue();
      return fields.filter((f) => {
        if (!f.condition) return true;
        // simple condition: "risk_level == '大型'" or "has_media != '无'"
        const parts = f.condition.split(/\s*(==|!=)\s*/);
        if (parts.length === 3) {
          const key = parts[0].trim();
          const op = parts[1].trim();
          const val = parts[2].trim().replace(/['"]/g, "");
          const current = formValues[key] || schema.risk_level || "";
          if (op === "==") return current === val;
          if (op === "!=") return current !== val;
        }
        return true;
      });
    },
    [form, schema.risk_level]
  );

  const renderField = (field: FieldDef) => {
    const common = {
      key: field.name,
      name: field.name,
      label: field.ui_label,
      rules: field.required
        ? [{ required: true, message: `请填写${field.ui_label}` }]
        : undefined,
    };

    switch (field.ui_type) {
      case "text":
        return (
          <Form.Item {...common}>
            <Input placeholder={field.ui_label} />
          </Form.Item>
        );
      case "textarea":
        return (
          <Form.Item {...common}>
            <Input.TextArea rows={4} placeholder={field.ui_label} />
          </Form.Item>
        );
      case "number":
        return (
          <Form.Item {...common}>
            <InputNumber
              min={field.min ?? 0}
              style={{ width: "100%" }}
              placeholder={field.ui_label}
            />
          </Form.Item>
        );
      case "date":
        return (
          <Form.Item {...common}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
        );
      case "select":
        return (
          <Form.Item {...common}>
            <Select
              placeholder={field.ui_label}
              options={(field.options || []).map((o) => ({ label: o, value: o }))}
            />
          </Form.Item>
        );
      case "checkbox":
        return (
          <Form.Item {...common} valuePropName="checked">
            <Checkbox>{field.ui_label}</Checkbox>
          </Form.Item>
        );
      case "repeater":
        return (
          <Form.List key={field.name} name={field.name}>
            {(items, { add, remove }) => (
              <>
                <Form.Item label={field.ui_label}>
                  <Button type="dashed" onClick={() => add("")} icon={<PlusOutlined />} block>
                    添加
                  </Button>
                </Form.Item>
                {items.map(({ key, name, ...rest }) => (
                  <Space key={key} style={{ display: "flex", marginBottom: 8 }} align="baseline">
                    <Form.Item {...rest} name={name} rules={[{ required: true, message: "必填" }]}>
                      <Input placeholder={`${field.ui_label} #${name + 1}`} />
                    </Form.Item>
                    <DeleteOutlined onClick={() => remove(name)} style={{ color: "#ff4d4f" }} />
                  </Space>
                ))}
              </>
            )}
          </Form.List>
        );
      case "signature":
        return (
          <Form.Item {...common}>
            <Upload
              accept="image/*"
              maxCount={1}
              customRequest={async ({ file, onSuccess, onError }) => {
                try {
                  const res = await documentsApi.upload(activityId, file as File, ["signature"]);
                  const doc = res.data;
                  form.setFieldValue(field.name, doc.minio_path);
                  onSuccess?.(doc);
                  message.success(`已上传签名图片`);
                } catch {
                  onError?.(new Error("上传失败"));
                  message.error("签名上传失败");
                }
              }}
            >
              <Button icon={<UploadOutlined />}>上传签名图片</Button>
            </Upload>
          </Form.Item>
        );
      default:
        return null;
    }
  };

  const handleSaveDraft = async () => {
    setSaving(true);
    try {
      const values = form.getFieldsValue();
      const data = serializeFormData(values, schema.fields);
      await onSaveDraft(data);
      message.success("草稿已保存");
    } catch {
      message.error("保存草稿失败");
    } finally {
      setSaving(false);
    }
  };

  const handleSubmit = async () => {
    try {
      await form.validateFields();
    } catch {
      return;
    }
    setSubmitting(true);
    try {
      const values = form.getFieldsValue();
      const data = serializeFormData(values, schema.fields);
      await onSubmit(data);
      message.success(`已生成 v${(schema.current_version ?? 0) + 1}`);
    } catch {
      message.error("生成失败");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Form form={form} layout="vertical" disabled={loading || submitting}>
      {visibleFields(schema.fields).map(renderField)}
      <Form.Item>
        <Space>
          <Button onClick={handleSaveDraft} loading={saving}>
            保存草稿
          </Button>
          <Button type="primary" onClick={handleSubmit} loading={submitting}>
            提交生成
          </Button>
        </Space>
      </Form.Item>
    </Form>
  );
}

function serializeFormData(values: Record<string, unknown>, fields: FieldDef[]): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const f of fields) {
    const v = values[f.name];
    if (v === undefined || v === null || v === "") {
      out[f.name] = f.ui_type === "repeater" ? [] : f.ui_type === "number" ? 0 : "";
      continue;
    }
    if (f.ui_type === "date") {
      out[f.name] = dayjs.isDayjs(v) ? (v as dayjs.Dayjs).format("YYYY-MM-DD") : String(v);
    } else if (f.ui_type === "number") {
      out[f.name] = typeof v === "number" ? v : Number(v) || 0;
    } else {
      out[f.name] = v;
    }
  }
  return out;
}
