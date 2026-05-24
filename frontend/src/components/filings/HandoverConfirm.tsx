import { useState } from "react";
import { Modal, Checkbox, message } from "antd";
import { useQueryClient } from "@tanstack/react-query";
import { filingsApi } from "@/api/filings";

interface Props {
  open: boolean;
  activityId: string;
  onClose: () => void;
}

export default function HandoverConfirm({ open, activityId, onClose }: Props) {
  const [loading, setLoading] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const qc = useQueryClient();

  const handleHandover = async () => {
    setLoading(true);
    try {
      await filingsApi.handover(activityId);
      message.success("交接确认成功");
      qc.invalidateQueries({ queryKey: ["activities", activityId] });
      qc.invalidateQueries({ queryKey: ["activities", activityId, "history"] });
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
      title="确认纸质交接"
      open={open}
      onCancel={() => {
        setConfirmed(false);
        onClose();
      }}
      onOk={handleHandover}
      confirmLoading={loading}
      okText="确认"
      okButtonProps={{ disabled: !confirmed }}
    >
      <p>请确认已将备案材料纸质版线下交接给政府对接人员。</p>
      <p style={{ color: "#ff4d4f" }}>此操作不可撤销。</p>
      <Checkbox
        checked={confirmed}
        onChange={(e) => setConfirmed(e.target.checked)}
      >
        我已知晓此操作不可撤销
      </Checkbox>
    </Modal>
  );
}
