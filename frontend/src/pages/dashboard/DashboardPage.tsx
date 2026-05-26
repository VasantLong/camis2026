import { Spin, Card, Statistic, Typography } from "antd";
import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "@/api/dashboard";
import StatusDistribution from "@/components/dashboard/StatusDistribution";
import AnomalyList from "@/components/dashboard/AnomalyList";
import ReportExport from "@/components/dashboard/ReportExport";

export default function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => dashboardApi.getPanel().then((r) => r.data),
  });

  if (isLoading) {
    return (
      <div style={{ textAlign: "center", padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!data) return null;

  const cancelledCount = data.by_status["已取消"] || 0;
  const postponedCount = data.by_status["已延期"] || 0;

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={3}>活动实施面板</Typography.Title>
      <div style={{ display: "flex", gap: 16, marginBottom: 16 }}>
        <Card style={{ flex: 1 }}>
          <Statistic title="活动总数" value={data.total} />
        </Card>
        <Card style={{ flex: 1 }}>
          <Statistic
            title="合规率"
            value={data.compliance_rate * 100}
            suffix="%"
            precision={1}
          />
        </Card>
        <Card style={{ flex: 1 }}>
          <Statistic title="已取消" value={cancelledCount} styles={{ content: { color: "#ff4d4f" } }} />
        </Card>
        <Card style={{ flex: 1 }}>
          <Statistic title="已延期" value={postponedCount} styles={{ content: { color: "#faad14" } }} />
        </Card>
      </div>
      <StatusDistribution byStatus={data.by_status} total={data.total} />
      <AnomalyList anomalies={data.recent_anomalies} />
      <ReportExport />
    </div>
  );
}
