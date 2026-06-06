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
  Modal,
  App,
} from "antd";
import { PlusOutlined, DeleteOutlined, UploadOutlined } from "@ant-design/icons";
import type { SchemaResponse, FieldDef, GenerateResponse } from "@/types/template";
import { documentsApi } from "@/api/documents";
import dayjs from "dayjs";

interface Props {
  activityId: string;
  schema: SchemaResponse;
  loading?: boolean;
  onSaveDraft: (data: Record<string, unknown>) => Promise<void>;
  onSubmit: (data: Record<string, unknown>) => Promise<GenerateResponse>;
}

export default function TemplateForm({ activityId, schema, loading, onSaveDraft, onSubmit }: Props) {
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const { message } = App.useApp();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [changedFields, setChangedFields] = useState<Set<string>>(new Set());
  const [isDirty, setIsDirty] = useState(false);

  // Track changed fields vs snapshot
  const handleValuesChange = (_changed: Record<string, unknown>, allValues: Record<string, unknown>) => {
    let hasAnyChange = false;
    const diff = new Set<string>();
    for (const f of schema.fields) {
      const cur = serializeFieldValue(allValues[f.name], f);
      const snap = snapshot ? snapshot[f.name] : undefined;
      if (snap !== undefined && cur !== snap && cur !== "") {
        diff.add(f.name);
        hasAnyChange = true;
      }
    }
    setChangedFields(diff);
    setIsDirty(hasAnyChange || schema.has_draft === true);
  };

  function serializeFieldValue(v: unknown, f: FieldDef): unknown {
    if (v === undefined || v === null || v === "") return f.ui_type === "repeater" ? undefined : f.ui_type === "number" ? undefined : "";
    if (f.ui_type === "date") return dayjs.isDayjs(v) ? (v as dayjs.Dayjs).format("YYYY-MM-DD") : String(v);
    if (f.ui_type === "number") return typeof v === "number" ? v : Number(v) || 0;
    if (f.ui_type === "repeater") return JSON.stringify(v);
    return v;
  }

  // pre-fill: draft first, then snapshot
  const prefillData = schema.has_draft && schema.draft_data
    ? schema.draft_data
    : schema.snapshot_data;
  const snapshot = schema.snapshot_data;
  const hasDraft = schema.has_draft === true;

  useEffect(() => {
    if (prefillData) {
      const vals: Record<string, unknown> = {};
      for (const f of schema.fields) {
        const val = prefillData[f.name];
        if (val !== undefined) {
          vals[f.name] = f.ui_type === "date" && typeof val === "string" ? dayjs(val) : val;
        }
      }
      form.setFieldsValue(vals);
    }
    setIsDirty(hasDraft);
  }, [schema, form]);  // eslint-disable-line react-hooks/exhaustive-deps

  const buttonsEnabled = !loading && !submitting && (isDirty || !snapshot);

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

  const renderField = (field: FieldDef, changed: boolean) => {
    const common: Record<string, unknown> = {
      key: field.name,
      name: field.name,
      label: field.ui_label,
      rules: field.required
        ? [{ required: true, message: `请填写${field.ui_label}` }]
        : undefined,
    };
    if (changed) {
      common.style = { background: "#fffbe6", padding: 8, borderRadius: 4 };
    }

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

  const doGenerate = async () => {
    setConfirmOpen(false);
    setSubmitting(true);
    const nextVersion = (schema.current_version ?? 0) + 1;
    try {
      const values = form.getFieldsValue();
      const data = serializeFormData(values, schema.fields);
      await onSubmit(data);
      message.success(`已生成 v${nextVersion}，可在版本历史中查看预览`);
    } catch {
      message.error("生成失败");
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmit = () => {
    form.validateFields().then(() => setConfirmOpen(true)).catch(() => {});
  };

  const nextVersion = (schema.current_version ?? 0) + 1;

  return (
    <>
      <Form form={form} layout="vertical" disabled={loading || submitting} onValuesChange={handleValuesChange}>
        {visibleFields(schema.fields).map((f) => renderField(f, changedFields.has(f.name)))}
        <Form.Item>
          <Space>
            <Button onClick={handleSaveDraft} loading={saving} disabled={!buttonsEnabled}>
              保存草稿
            </Button>
            <Button type="primary" onClick={handleSubmit} loading={submitting} disabled={!buttonsEnabled}>
              提交生成
            </Button>
          </Space>
        </Form.Item>
      </Form>
      <Modal
        title="确认生成"
        open={confirmOpen}
        onOk={doGenerate}
        onCancel={() => setConfirmOpen(false)}
        okText="确认生成"
        cancelText="取消"
        confirmLoading={submitting}
      >
        将生成 v{nextVersion} 版本，生成后不可撤销。确认继续？
      </Modal>
    </>
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
