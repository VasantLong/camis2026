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

  download: (docId: string) => {
    window.open(`/api/documents/${docId}`, "_blank");
  },
};
