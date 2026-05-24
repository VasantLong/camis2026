import { Upload, Button, Input, Space, message } from "antd";
import { UploadOutlined } from "@ant-design/icons";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { documentsApi } from "@/api/documents";

const ALLOWED_TYPES = [
  "application/pdf",
  "image/jpeg",
  "image/png",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];
const ALLOWED_EXTENSIONS = ".pdf,.jpg,.jpeg,.png,.doc,.docx";
const MAX_SIZE = 50 * 1024 * 1024; // 50MB

interface Props {
  activityId: string;
}

export default function DocumentUpload({ activityId }: Props) {
  const [tags, setTags] = useState("");
  const [uploading, setUploading] = useState(false);
  const qc = useQueryClient();

  const beforeUpload = (file: File) => {
    if (file.size > MAX_SIZE) {
      message.error(`文件 ${file.name} 超过 50MB 限制`);
      return Upload.LIST_IGNORE;
    }
    if (!ALLOWED_TYPES.includes(file.type)) {
      message.error(`不支持的文件格式: ${file.type}`);
      return Upload.LIST_IGNORE;
    }
    return true;
  };

  const customRequest = async (options: {
    file: File;
    onSuccess?: () => void;
    onError?: (err: Error) => void;
  }) => {
    setUploading(true);
    try {
      const tagList = tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      await documentsApi.upload(activityId, options.file as File, tagList);
      message.success(`文件 ${options.file.name} 上传成功`);
      qc.invalidateQueries({ queryKey: ["activities", activityId, "documents"] });
      setTags("");
      options.onSuccess?.();
    } catch (err: unknown) {
      const detail =
        (err as { detail?: string })?.detail || "上传失败";
      message.error(detail);
      options.onError?.(new Error(detail));
    } finally {
      setUploading(false);
    }
  };

  return (
    <Space direction="vertical" style={{ width: "100%" }}>
      <Input
        placeholder="标签（可选，逗号分隔）"
        value={tags}
        onChange={(e) => setTags(e.target.value)}
        style={{ maxWidth: 300 }}
      />
      <Upload
        accept={ALLOWED_EXTENSIONS}
        showUploadList={{ showPreviewIcon: false }}
        beforeUpload={beforeUpload as never}
        customRequest={customRequest as never}
      >
        <Button icon={<UploadOutlined />} loading={uploading}>
          选择文件上传
        </Button>
      </Upload>
    </Space>
  );
}
