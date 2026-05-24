import { Table, Button, Empty, Spin } from "antd";
import { DownloadOutlined } from "@ant-design/icons";
import { documentsApi } from "@/api/documents";
import type { DocumentResponse } from "@/types/document";

interface Props {
  documents: DocumentResponse[];
  loading: boolean;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocumentList({ documents, loading }: Props) {
  if (loading) return <Spin />;
  if (documents.length === 0) {
    return <Empty description="暂无上传文档" />;
  }

  const columns = [
    { title: "文件名", dataIndex: "filename", key: "filename" },
    {
      title: "大小",
      dataIndex: "file_size",
      key: "file_size",
      width: 100,
      render: (s: number) => formatSize(s),
    },
    { title: "类型", dataIndex: "content_type", key: "content_type", width: 150 },
    {
      title: "标签",
      dataIndex: "tags",
      key: "tags",
      width: 200,
      render: (tags: string[] | null) =>
        tags?.length ? tags.join(", ") : "—",
    },
    {
      title: "操作",
      key: "action",
      width: 100,
      render: (_: unknown, record: DocumentResponse) => (
        <Button
          icon={<DownloadOutlined />}
          onClick={() => documentsApi.download(record.id)}
        >
          下载
        </Button>
      ),
    },
  ];

  return <Table rowKey="id" columns={columns} dataSource={documents} />;
}
