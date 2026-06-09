import { useState } from "react";
import { Modal, Form, Input, Tag, message } from "antd";
import { workflowsApi } from "@/api/workflows";
import { STATUS_COLOR_MAP } from "@/utils/constants";

interface Props {
  open: boolean;
  activityId: string;
  toStatus: string;
  onClose: () => void;
  onSuccess: () => void;
}

export default function StatusTransitionModal({
  open,
  activityId,
  toStatus,
  onClose,
  onSuccess,
}: Props) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (values: { comment?: string }) => {
    setLoading(true);
    try {
      await workflowsApi.transition(activityId, {
        to_status: toStatus,
        comment: values.comment,
      });
      message.success("状态变更成功");
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const detail = (err as { detail?: string })?.detail || "操作失败";
      if (detail.includes("已被他人修改") || detail.includes("已被变更")) {
        message.warning("该活动已被他人修改，请刷新后重试");
      } else {
        message.error(detail);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="状态变更"
      open={open}
      onCancel={onClose}
      onOk={() => form.submit()}
      confirmLoading={loading}
    >
      <p>
        目标状态:{" "}
        <Tag color={STATUS_COLOR_MAP[toStatus] || "blue"}>{toStatus}</Tag>
      </p>
      <Form form={form} layout="vertical" onFinish={handleSubmit}>
        <Form.Item
          name="comment"
          label={toStatus === "已结束" ? "结束原因" : "备注（可选）"}
          rules={toStatus === "已结束" ? [{ required: true, message: "请填写结束原因" }] : undefined}
        >
          <Input.TextArea
            maxLength={2000}
            rows={3}
            placeholder={toStatus === "已结束" ? "如：活动已于X月X日顺利举办完成" : undefined}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}
