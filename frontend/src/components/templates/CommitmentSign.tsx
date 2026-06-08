import { useState, useEffect } from "react";
import { Button, Card, Descriptions, Typography, Space, message, Image } from "antd";
import { FileProtectOutlined } from "@ant-design/icons";
import { templatesApi } from "@/api/templates";
import { documentsApi } from "@/api/documents";

interface Props {
  activityId: string;
  activityName: string;
  sponsor: string;
  estimatedTime: string;
  location: string;
  crowdScale: string;
  securityStaffCount: string;
  signatureUrl: string | null;
  signaturePath: string | null;
  onSigned: () => void;
  loading?: boolean;
}

export default function CommitmentSign({
  activityId, activityName, sponsor, estimatedTime,
  location, crowdScale, securityStaffCount, signatureUrl, signaturePath, onSigned, loading,
}: Props) {
  const [signing, setSigning] = useState(false);
  const [loadedSigUrl, setLoadedSigUrl] = useState<string | null>(null);
  const displaySigUrl = signatureUrl || loadedSigUrl;

  // Load persistent signature from MinIO when blob URL is unavailable
  useEffect(() => {
    if (signatureUrl || !signaturePath) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await documentsApi.getPresignedByPath(signaturePath);
        if (!cancelled && res.data?.url) setLoadedSigUrl(res.data.url);
      } catch { /* presign may fail */ }
    })();
    return () => { cancelled = true; };
  }, [signatureUrl, signaturePath]);

  const handleSign = async () => {
    setSigning(true);
    try {
      await templatesApi.signCommitment(activityId);
      message.success("备案承诺书已签署，活动已提交备案");
      onSigned();
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "签署失败");
    } finally {
      setSigning(false);
    }
  };

  return (
    <Card
      title={<><FileProtectOutlined /> 签署备案承诺书</>}
      style={{ marginTop: 16, border: "1px solid #52c41a" }}
    >
      <Descriptions column={2} size="small" style={{ marginBottom: 16 }}>
        <Descriptions.Item label="活动名称">{activityName || "-"}</Descriptions.Item>
        <Descriptions.Item label="主办方">{sponsor || "-"}</Descriptions.Item>
        <Descriptions.Item label="预计举办时间">{estimatedTime || "-"}</Descriptions.Item>
        <Descriptions.Item label="活动地点">{location || "-"}</Descriptions.Item>
        <Descriptions.Item label="预计参与人数">{crowdScale || "-"}</Descriptions.Item>
        <Descriptions.Item label="安保人员数量">{securityStaffCount || "-"}</Descriptions.Item>
      </Descriptions>

      {displaySigUrl && (
        <div style={{ marginBottom: 16 }}>
          <Typography.Text type="secondary">安全负责人签名：</Typography.Text>
          <br />
          <Image src={displaySigUrl} alt="签名" style={{ maxWidth: 200, maxHeight: 80, borderRadius: 4, border: "1px solid #d9d9d9" }} />
        </div>
      )}

      <Space>
        <Button type="primary" onClick={handleSign} loading={signing || loading} disabled={!displaySigUrl}>
          确认签署承诺书并提交备案
        </Button>
        <Typography.Text type="secondary">签署后活动将提交备案申请</Typography.Text>
      </Space>
    </Card>
  );
}
