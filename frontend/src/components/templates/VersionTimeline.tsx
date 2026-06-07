import { useState } from "react";
import { Tag, Button, Modal, Descriptions, Space, Typography } from "antd";
import type { VersionItem, VersionDetail, VersionDiff } from "@/types/template";

const { Text } = Typography;

interface Props {
  versions: VersionItem[];
  onViewDetail: (version: number) => Promise<VersionDetail | null>;
  onDiff: (v1: number, v2: number) => Promise<VersionDiff[]>;
  onPreview?: (version: number) => Promise<string | null>;
}

export default function VersionTimeline({ versions, onViewDetail, onDiff, onPreview }: Props) {
  const [detailVisible, setDetailVisible] = useState(false);
  const [diffVisible, setDiffVisible] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [detail, setDetail] = useState<VersionDetail | null>(null);
  const [diffs, setDiffs] = useState<VersionDiff[]>([]);
  const [selectedV1, setSelectedV1] = useState<number | null>(null);
  const [selectedV2, setSelectedV2] = useState<number | null>(null);

  const handleViewDetail = async (v: number) => {
    const d = await onViewDetail(v);
    if (d) {
      setDetail(d);
      setDetailVisible(true);
    }
  };

  const handleDiff = async () => {
    if (selectedV1 !== null && selectedV2 !== null) {
      const d = await onDiff(selectedV1, selectedV2);
      setDiffs(d);
      setDiffVisible(true);
    }
  };

  const toggleSelect = (v: number) => {
    if (selectedV1 === v) {
      setSelectedV1(null);
    } else if (selectedV2 === v) {
      setSelectedV2(null);
    } else if (selectedV1 === null) {
      setSelectedV1(v);
    } else if (selectedV2 === null) {
      setSelectedV2(v);
    } else {
      setSelectedV1(v);
      setSelectedV2(null);
    }
  };

  if (versions.length === 0) {
    return <Text type="secondary">暂无版本记录</Text>;
  }

  return (
    <>
      <Space style={{ marginBottom: 16 }}>
        <Text strong>版本历史</Text>
        {selectedV1 !== null && selectedV2 !== null && (
          <Button size="small" type="primary" onClick={handleDiff}>
            对比 v{selectedV1} vs v{selectedV2}
          </Button>
        )}
      </Space>

      <Space orientation="vertical" size="small">
        {versions.map((v) => (
          <Space key={v.id}>
            <Button
              size="small"
              type={selectedV1 === v.version_number || selectedV2 === v.version_number ? "primary" : "default"}
              onClick={() => toggleSelect(v.version_number)}
            >
              v{v.version_number}
            </Button>
            {v.is_current && <Tag color="green">当前</Tag>}
            <Text type="secondary" style={{ fontSize: 12 }}>
              {v.created_at?.slice(0, 10)}
            </Text>
            <Button size="small" type="link" onClick={() => handleViewDetail(v.version_number)}>
              详情
            </Button>
            {onPreview && v.pdf_ready && (
              <Button size="small" type="link" onClick={async () => {
                const url = await onPreview(v.version_number);
                if (url) setPreviewUrl(url);
              }}>
                预览
              </Button>
            )}
            {onPreview && !v.pdf_ready && (
              <Tag>生成中</Tag>
            )}
          </Space>
        ))}
      </Space>

      {/* detail modal */}
      <Modal
        title={`版本 ${detail?.version_number} 详情`}
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={600}
      >
        {detail && (
          <Descriptions column={1} size="small" bordered>
            {Object.entries(detail.data_snapshot).map(([k, v]) => (
              <Descriptions.Item key={k} label={k}>
                {Array.isArray(v) ? v.join(" / ") : String(v ?? "-")}
              </Descriptions.Item>
            ))}
          </Descriptions>
        )}
      </Modal>

      {/* diff modal */}
      <Modal
        title={`版本对比 v${selectedV1} vs v${selectedV2}`}
        open={diffVisible}
        onCancel={() => setDiffVisible(false)}
        footer={null}
        width={700}
      >
        {diffs.length === 0 ? (
          <Text type="secondary">所选版本无差异</Text>
        ) : (
          diffs.map((d) => (
            <Descriptions key={d.field} column={1} size="small" bordered style={{ marginBottom: 8 }}>
              <Descriptions.Item label="字段">{d.field}</Descriptions.Item>
              <Descriptions.Item label="旧值">
                <Text delete type="danger">
                  {Array.isArray(d.old) ? d.old.join(" / ") : String(d.old ?? "-")}
                </Text>
              </Descriptions.Item>
              <Descriptions.Item label="新值">
                <Text style={{ color: "#52c41a" }}>
                  {Array.isArray(d.new) ? d.new.join(" / ") : String(d.new ?? "-")}
                </Text>
              </Descriptions.Item>
            </Descriptions>
          ))
        )}
      </Modal>

      {/* pdf preview modal */}
      <Modal
        title="PDF 预览"
        open={!!previewUrl}
        onCancel={() => setPreviewUrl(null)}
        footer={null}
        width="90%"
        style={{ top: 20 }}
        destroyOnHidden
      >
        {previewUrl && (
          <iframe
            src={previewUrl}
            style={{ width: "100%", height: "75vh", border: "none" }}
            title="PDF 预览"
          />
        )}
      </Modal>
    </>
  );
}
