import { useState } from "react";
import { Modal, Form, Input, Alert, Checkbox, message } from "antd";
import { workflowsApi } from "@/api/workflows";

interface Props {
  open: boolean;
  mode: "cancel" | "postpone";
  activityId: string;
  onClose: () => void;
  onSuccess: () => void;
}

export default function ForceChangeModal({
  open,
  mode,
  activityId,
  onClose,
  onSuccess,
}: Props) {
  const [loading, setLoading] = useState(false);
  const [confirmed, setConfirmed] = useState(false);

  const title = mode === "cancel" ? "强制取消" : "强制延期";
  const warningMsg =
    mode === "cancel"
      ? "此操作将使活动进入「已取消」终态，后续所有操作将被锁定，不可撤销。"
      : "此操作将使活动进入「已延期」终态，后续所有操作将被锁定，不可撤销。";

  const handleSubmit = async (values: { reason: string }) => {
    setLoading(true);
    try {
      if (mode === "cancel") {
        await workflowsApi.forceCancel(activityId, values);
      } else {
        await workflowsApi.forcePostpone(activityId, values);
      }
      message.success("操作成功");
      setConfirmed(false);
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const detail = (err as { detail?: string })?.detail || "操作失败";
      message.error(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title={title}
      open={open}
      onCancel={() => {
        setConfirmed(false);
        onClose();
      }}
      onOk={() => {
        const form = document.querySelector<HTMLFormElement>(
          "#force-form form"
        );
        form?.requestSubmit();
      }}
      confirmLoading={loading}
      okText="确认"
      okButtonProps={{ danger: true, disabled: !confirmed }}
    >
      <Alert type="warning" title={warningMsg} showIcon style={{ marginBottom: 16 }} />
      <Checkbox checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)}>
        我已知晓此操作不可撤销
      </Checkbox>
      <div id="force-form" style={{ marginTop: 16 }}>
        <Form layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="reason"
            label="原因"
            rules={[{ required: true, message: "请输入原因" }]}
          >
            <Input.TextArea maxLength={2000} rows={3} />
          </Form.Item>
        </Form>
      </div>
    </Modal>
  );
}
