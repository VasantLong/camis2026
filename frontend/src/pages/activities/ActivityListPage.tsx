import { useSearchParams } from "react-router-dom";
import { Button, Tabs, Typography } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { useActivities } from "@/hooks/useActivityQueries";
import ActivityFilters from "@/components/activities/ActivityFilters";
import ActivityTable from "@/components/activities/ActivityTable";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";

const OPERATIONAL_PERMS = ["create_activity", "manage_security", "audit_material", "submit_plan", "pack_filing"];

export default function ActivityListPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const userPermissions = useAuthStore((s) => s.user?.permissions);
  const permissions = userPermissions ?? [];

  const hasOperational = permissions.some((p) => OPERATIONAL_PERMS.includes(p));
  const tab = hasOperational ? (searchParams.get("tab") || "pending") : "all";
  const params = {
    status: searchParams.get("status") || undefined,
    keyword: searchParams.get("keyword") || undefined,
    date_from: searchParams.get("date_from") || undefined,
    date_to: searchParams.get("date_to") || undefined,
    sort: searchParams.get("sort") || "created",
    page: Number(searchParams.get("page") || "1"),
    size: Number(searchParams.get("size") || "20"),
    tab,
  };

  const { data: paginated, isLoading } = useActivities(params);
  const data = paginated?.items ?? [];
  const total = paginated?.total ?? 0;

  const setTab = (key: string) => {
    const next = new URLSearchParams(searchParams);
    next.set("tab", key);
    next.delete("page");
    setSearchParams(next);
  };

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
      {hasOperational && (
        <Tabs
          activeKey={tab}
          onChange={setTab}
          items={[
            { key: "pending", label: "待操作" },
            { key: "completed", label: "已完成" },
          ]}
        />
      )}
      <ActivityFilters />
      <ActivityTable data={data} total={total} loading={isLoading} />
    </div>
  );
}
