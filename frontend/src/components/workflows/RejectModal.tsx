import { useState } from "react";
import { Modal, Form, Input, message } from "antd";
import { workflowsApi } from "@/api/workflows";

interface Props {
  open: boolean;
  activityId: string;
  isReverseFlow: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function RejectModal({
  open,
  activityId,
  isReverseFlow,
  onClose,
  onSuccess,
}: Props) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (values: { reason: string }) => {
    setLoading(true);
    try {
      await workflowsApi.reject(activityId, values);
      message.success("驳回成功");
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
      title={isReverseFlow ? "驳回（逆向流转）" : "驳回"}
      open={open}
      onCancel={onClose}
      onOk={() => form.submit()}
      confirmLoading={loading}
      okText="确认驳回"
      okButtonProps={{ danger: true }}
    >
      {isReverseFlow && (
        <p style={{ marginBottom: 16 }}>
          审批通过后驳回将退回至「待安保方案设计」状态，需安保部重新出具方案。
        </p>
      )}
      <Form form={form} layout="vertical" onFinish={handleSubmit}>
        <Form.Item
          name="reason"
          label="驳回原因"
          rules={[{ required: true, message: "请输入驳回原因" }]}
        >
          <Input.TextArea maxLength={2000} rows={4} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
