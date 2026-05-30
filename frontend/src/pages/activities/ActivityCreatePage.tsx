import { useNavigate } from "react-router-dom";
import { Typography, message } from "antd";
import ActivityForm from "@/components/activities/ActivityForm";
import { useCreateActivity } from "@/hooks/useActivityQueries";
import type { ActivityCreate } from "@/types/activity";
import type { ApiErrorResponse } from "@/types/api";

export default function ActivityCreatePage() {
  const navigate = useNavigate();
  const createMutation = useCreateActivity();

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
      <ActivityForm onSubmit={handleSubmit} loading={createMutation.isPending} />
    </div>
  );
}
