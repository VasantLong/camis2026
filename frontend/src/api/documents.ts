import client from "./client";
import type { DocumentResponse } from "@/types/document";

export const documentsApi = {
  upload: (activityId: string, file: File, tags?: string[]) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("activity_id", activityId);
    if (tags?.length) formData.append("tags", tags.join(","));
    return client.post<DocumentResponse>("/documents/upload", formData);
  },

  getPresignedUrl: (docId: string) =>
    client.get<{ url: string }>(`/documents/${docId}/url?inline=1`),

  getPresignedByPath: (minioPath: string) =>
    client.get<{ url: string }>(`/documents/presign/by-path?path=${encodeURIComponent(minioPath)}`),

  _getUrl: async (docId: string, inline: boolean) => {
    const res = await client.get<{ url: string }>(
      `/documents/${docId}/url?inline=${inline ? "1" : "0"}`
    );
    window.open(res.data.url, "_blank");
  },

  download: (docId: string) => documentsApi._getUrl(docId, false),

  preview: (docId: string) => documentsApi._getUrl(docId, true),
};
