import { useNavigate } from "react-router-dom";
import { Alert, Typography, message } from "antd";
import ActivityForm from "@/components/activities/ActivityForm";
import { useCreateActivity } from "@/hooks/useActivityQueries";
import { useAuthStore } from "@/stores/authStore";
import type { ActivityCreate } from "@/types/activity";
import type { ApiErrorResponse } from "@/types/api";

export default function ActivityCreatePage() {
  const navigate = useNavigate();
  const createMutation = useCreateActivity();
  const contactPhone = useAuthStore((s) => s.user?.contact_phone);

  const handleSubmit = async (values: ActivityCreate) => {
    try {
      const activity = await createMutation.mutateAsync(values);
      message.success("活动创建成功");
      navigate(`/activities/${activity.id}`);
    } catch (err: unknown) {
      const apiErr = err as ApiErrorResponse;
      if (apiErr.code === "CONFLICT" && apiErr.fields?.location) {
        message.error(apiErr.fields.location);
      } else {
        message.error(apiErr.detail || "创建失败");
      }
    }
  };

  return (
    <div style={{ padding: 24, maxWidth: 600 }}>
      <Typography.Title level={3}>新建活动</Typography.Title>
      {!contactPhone && (
        <Alert
          type="warning"
          title="请先补充联系方式"
          description="您需要填写联系方式后才能新建活动。"
          showIcon
          closable
          style={{ marginBottom: 16 }}
        />
      )}
      <ActivityForm onSubmit={handleSubmit} loading={createMutation.isPending} />
    </div>
  );
}
