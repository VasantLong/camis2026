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
  Typography,
  Tooltip,
  App,
} from "antd";
import { PlusOutlined, DeleteOutlined, UploadOutlined, QuestionCircleOutlined } from "@ant-design/icons";
import type { SchemaResponse, FieldDef, GenerateResponse } from "@/types/template";
import { documentsApi } from "@/api/documents";
import dayjs from "dayjs";

interface Props {
  activityId: string;
  schema: SchemaResponse;
  loading?: boolean;
  disabled?: boolean;
  highlightFields?: string[];
  onSaveDraft: (data: Record<string, unknown>) => Promise<void>;
  onSubmit: (data: Record<string, unknown>) => Promise<GenerateResponse>;
}

export default function TemplateForm({ activityId, schema, loading, disabled, highlightFields, onSaveDraft, onSubmit }: Props) {
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const { message } = App.useApp();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [changedFields, setChangedFields] = useState<Set<string>>(new Set());
  const [isDirty, setIsDirty] = useState(false);
  const [highlightSet, setHighlightSet] = useState<Set<string>>(new Set());

  // Sync highlightFields prop
  useEffect(() => {
    if (highlightFields && highlightFields.length > 0) {
      setHighlightSet(new Set(highlightFields));
    }
  }, [highlightFields]);

  // Clear highlights when form values change (user started editing)
  const clearHighlights = () => {
    if (highlightSet.size > 0) setHighlightSet(new Set());
  };

  // Track changed fields vs snapshot
  const handleValuesChange = (_changed: Record<string, unknown>, allValues: Record<string, unknown>) => {
    clearHighlights();

    // auto_calc: total_days from start_time/end_time
    for (const f of schema.fields) {
      if (f.auto_calc === "end_time - start_time") {
        const s = allValues["start_time"];
        const e = allValues["end_time"];
        if (s && e && dayjs.isDayjs(s) && dayjs.isDayjs(e)) {
          const days = (e as dayjs.Dayjs).diff(s as dayjs.Dayjs, "day") + 1;
          if (days > 0 && (allValues as any)["total_days"] !== days) {
            form.setFieldValue("total_days", days);
          }
        }
      }
    }
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
    const vals: Record<string, unknown> = {};
    // prefill from draft or snapshot
    if (prefillData) {
      for (const f of schema.fields) {
        const val = prefillData[f.name];
        if (val !== undefined) {
          if (f.ui_type === "date" && typeof val === "string") {
            if (val) vals[f.name] = dayjs(val);
          } else if (f.ui_type === "signature" && typeof val === "string" && val) {
            vals[f.name] = [{ uid: "-1", name: "signature", status: "done" as const, url: val }];
          } else if (f.ui_type === "signature" && Array.isArray(val)) {
            vals[f.name] = val;
          } else {
            vals[f.name] = val;
          }
        }
      }
    }
    // autofill from Activity/Plan data (for empty fields of any type)
    if (schema.autofill_data) {
      for (const f of schema.fields) {
        if (vals[f.name] === undefined) {
          const autoVal = schema.autofill_data[f.name];
          if (autoVal !== undefined && autoVal !== null && autoVal !== "") {
            if (f.ui_type === "date" && typeof autoVal === "string") {
              vals[f.name] = dayjs(autoVal);
            } else {
              vals[f.name] = autoVal;
            }
          }
        }
      }
    }
    if (Object.keys(vals).length > 0) form.setFieldsValue(vals);
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
    const isHighlighted = highlightSet.has(field.name);
    const itemStyle = isHighlighted
      ? { background: "#fff2f0", padding: 8, borderRadius: 4, border: "1px solid #ff4d4f" }
      : changed ? { background: "#fffbe6", padding: 8, borderRadius: 4 } : undefined;
    const rules = field.required
      ? [{ required: true, message: `请填写${field.ui_label}` }]
      : undefined;

    switch (field.ui_type) {
      case "text": {{
        const extraRules = field.validate
          ? [{ pattern: new RegExp(field.validate.pattern), message: field.validate.message }]
          : [];
        return (
          <Form.Item key={field.name} name={field.name} label={field.ui_label} rules={[...(rules || []), ...extraRules]} style={itemStyle}>
            <Input placeholder={field.ui_label} />
          </Form.Item>
        );
      }}
      case "textarea":
        return (
          <Form.Item key={field.name} name={field.name} label={field.ui_label} rules={rules} style={itemStyle}>
            <Input.TextArea rows={4} placeholder={field.ui_label} />
          </Form.Item>
        );
      case "number": {{
        if (field.auto_calc) {
          return (
            <Form.Item key={field.name} name={field.name} label={field.ui_label} style={itemStyle}>
              <InputNumber disabled style={{ width: "100%" }} />
            </Form.Item>
          );
        }
        return (
          <Form.Item key={field.name} name={field.name} label={field.ui_label} rules={rules} style={itemStyle}>
            <InputNumber
              min={field.min ?? 0}
              style={{ width: "100%" }}
              placeholder={field.ui_label}
            />
          </Form.Item>
        );
      }}
      case "date":
        return (
          <Form.Item key={field.name} name={field.name} label={field.ui_label} rules={rules} style={itemStyle}>
            <DatePicker
              style={{ width: "100%" }}
              disabledDate={field.name === "end_time" ? (d) => d && d.isBefore(dayjs(form.getFieldValue("start_time"))) : undefined}
            />
          </Form.Item>
        );
      case "select":
        return (
          <Form.Item key={field.name} name={field.name} label={field.ui_label} rules={rules} style={itemStyle}>
            <Select
              placeholder={field.ui_label}
              options={(field.options || []).map((o) => ({ label: o, value: o }))}
            />
          </Form.Item>
        );
      case "checkbox":
        return (
          <Form.Item key={field.name} name={field.name} label={field.ui_label} rules={rules} style={itemStyle} valuePropName="checked">
            <Checkbox>{field.ui_label}</Checkbox>
          </Form.Item>
        );
      case "repeater":
        return (
          <Form.List key={field.name} name={field.name}>
            {(items, { add, remove }) => (
              <>
                <Form.Item label={
                  <span>
                    {field.ui_label}
                    {(field as any).hint && (
                      <Tooltip title={(field as any).hint}>
                        <QuestionCircleOutlined style={{ marginLeft: 6, color: "#999", cursor: "help" }} />
                      </Tooltip>
                    )}
                  </span>
                }>
                  <Button type="dashed" onClick={() => add("")} icon={<PlusOutlined />} block>
                    添加
                  </Button>
                </Form.Item>
                {(items as any[]).map(({ key, name, ...rest }) => {
                  // eslint-disable-next-line @typescript-eslint/no-unused-vars
                  const { key: _k, ...fieldProps } = rest as any;
                  return (
                    <Space key={key} style={{ display: "flex", marginBottom: 8 }} align="baseline">
                      <Form.Item {...fieldProps} name={name} rules={[{ required: true, message: "必填" }]}>
                        <Input placeholder={`${field.ui_label} #${(name as number) + 1}`} />
                      </Form.Item>
                      <DeleteOutlined onClick={() => remove(name as number)} style={{ color: "#ff4d4f" }} />
                    </Space>
                  );
                })}
              </>
            )}
          </Form.List>
        );
      case "signature":
        return (
          <Form.Item
            key={field.name}
            name={field.name}
            label={field.ui_label}
            rules={rules}
            style={itemStyle}
            valuePropName="fileList"
            normalize={(val) => (Array.isArray(val) ? val : [])}
            getValueFromEvent={(e) => (Array.isArray(e) ? e : e?.fileList || [])}
          >
            <Upload
              accept="image/*"
              maxCount={1}
              listType="picture-card"
              customRequest={async ({ file, onSuccess, onError }) => {
                try {
                  const res = await documentsApi.upload(activityId, file as File, ["signature"]);
                  const doc = res.data;
                  const previewUrl = URL.createObjectURL(file as File);
                  form.setFieldValue(field.name, [{ uid: "-1", name: (file as File).name, status: "done", url: doc.minio_path, thumbUrl: previewUrl }]);
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
      case "autofill":
        return (
          <Form.Item key={field.name} name={field.name} label={field.ui_label} rules={rules} style={itemStyle}>
            <Input disabled style={{ backgroundColor: "#f5f5f5" }} />
          </Form.Item>
        );
      case "declarations": {
        const items = (field as any).declaration_items as string[] | undefined;
        const hint = (field as any).hint as string | undefined;
        return (
          <div key={field.name} style={{ ...itemStyle, marginBottom: 16, padding: 12, border: "1px solid #d9d9d9", borderRadius: 6, background: "#fafafa" }}>
            <Typography.Text strong>{field.ui_label}</Typography.Text>
            {hint && (
              <Typography.Paragraph type="secondary" style={{ marginTop: 4, marginBottom: 8, fontSize: 12 }}>
                {hint}
              </Typography.Paragraph>
            )}
            <ol style={{ marginTop: 8, paddingLeft: 20, fontSize: 13, lineHeight: 1.8 }}>
              {(items || []).map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ol>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              以上声明内容属实，由主办单位公章及安全负责人签字确认，依法承担相应法律责任。
            </Typography.Text>
          </div>
        );
      }
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
    setSubmitting(true);
    const nextVersion = (schema.current_version ?? 0) + 1;
    try {
      const values = form.getFieldsValue();
      const data = serializeFormData(values, schema.fields);
      await onSubmit(data);
      message.success(`已生成 v${nextVersion}`);
    } catch {
      message.error("生成失败");
    } finally {
      setSubmitting(false);
      setConfirmOpen(false);
    }
  };

  const handleSubmit = () => {
    form.validateFields().then(() => setConfirmOpen(true)).catch(() => {});
  };

  const nextVersion = (schema.current_version ?? 0) + 1;

  return (
    <>
      <Form form={form} layout="vertical" disabled={loading || submitting || disabled} onValuesChange={handleValuesChange}>
        {visibleFields(schema.fields).map((f) => renderField(f, changedFields.has(f.name)))}
        {!disabled && (
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
        )}
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
    if (f.ui_type === "declarations") continue;  // fixed content, not user data
    const v = values[f.name];
    if (v === undefined || v === null || v === "") {
      out[f.name] = f.ui_type === "repeater" ? [] : f.ui_type === "number" ? 0 : "";
      continue;
    }
    if (f.ui_type === "date") {
      out[f.name] = dayjs.isDayjs(v) ? (v as dayjs.Dayjs).format("YYYY-MM-DD") : String(v);
    } else if (f.ui_type === "number") {
      out[f.name] = typeof v === "number" ? v : Number(v) || 0;
    } else if (f.ui_type === "signature") {
      // stored as fileList array; extract URL string for backend DOCX rendering
      const files = Array.isArray(v) ? v : [];
      out[f.name] = files.length > 0 ? (files[0].url || "") : "";
    } else {
      out[f.name] = v;
    }
  }
  return out;
}
