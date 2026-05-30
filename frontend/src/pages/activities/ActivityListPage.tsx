import { useSearchParams } from "react-router-dom";
import { Button, Typography } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { useActivities } from "@/hooks/useActivityQueries";
import ActivityFilters from "@/components/activities/ActivityFilters";
import ActivityTable from "@/components/activities/ActivityTable";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";

export default function ActivityListPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const userPermissions = useAuthStore((s) => s.user?.permissions);
  const permissions = userPermissions ?? [];

  const params = {
    status: searchParams.get("status") || undefined,
    keyword: searchParams.get("keyword") || undefined,
    date_from: searchParams.get("date_from") || undefined,
    date_to: searchParams.get("date_to") || undefined,
    page: Number(searchParams.get("page") || "1"),
    size: Number(searchParams.get("size") || "20"),
  };

  const { data: paginated, isLoading } = useActivities(params);
  const data = paginated?.items ?? [];
  const total = paginated?.total ?? 0;

  return (
    <div style={{ padding: 24 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <Typography.Title level={3} style={{ margin: 0 }}>
          活动列表
        </Typography.Title>
        {permissions.includes("create_activity") && (
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate("/activities/new")}
          >
            新建活动
          </Button>
        )}
      </div>
      <ActivityFilters />
      <ActivityTable data={data} total={total} loading={isLoading} />
    </div>
  );
}
