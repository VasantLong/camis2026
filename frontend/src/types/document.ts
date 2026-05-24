export interface DocumentResponse {
  id: string;
  activity_id: string | null;
  uploader_id: string;
  filename: string;
  minio_path: string;
  file_size: number;
  content_type: string;
  tags: string[] | null;
}
