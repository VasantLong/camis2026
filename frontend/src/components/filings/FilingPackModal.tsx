import { useState } from "react";
import { Modal, Result, Button, message } from "antd";
import { useQueryClient } from "@tanstack/react-query";
import { filingsApi } from "@/api/filings";

interface Props {
  open: boolean;
  activityId: string;
  onClose: () => void;
}

export default function FilingPackModal({ open, activityId, onClose }: Props) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    ready: boolean;
    missing: string[];
  } | null>(null);
  const qc = useQueryClient();

  const handlePack = async () => {
    setLoading(true);
    try {
      const { data } = await filingsApi.pack(activityId);
      if (data.ready) {
        message.success("打包成功");
        qc.invalidateQueries({ queryKey: ["activities", activityId] });
        onClose();
      } else {
        setResult({ ready: false, missing: data.missing_signatures });
      }
    } catch (err: unknown) {
      const detail = (err as { detail?: string })?.detail || "打包失败";
      message.error(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="打包备案材料"
      open={open}
      onCancel={onClose}
      footer={
        result?.ready === false
          ? [
              <Button key="close" onClick={onClose}>关闭</Button>,
              <Button key="retry" type="primary" onClick={() => setResult(null)}>
                重新打包
              </Button>,
            ]
          : [
              <Button key="cancel" onClick={onClose}>取消</Button>,
              <Button
                key="pack"
                type="primary"
                loading={loading}
                onClick={handlePack}
              >
                确认打包
              </Button>,
            ]
      }
    >
      {result?.ready === false ? (
        <Result
          status="warning"
          title="材料不齐全"
          subTitle={`以下材料缺少电子签名: ${result.missing.join(", ")}`}
        />
      ) : (
        <p>确认打包该活动的所有备案材料？打包后将生成 PDF 集合。</p>
      )}
    </Modal>
  );
}
