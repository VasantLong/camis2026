import { useState } from "react";
import { Card, DatePicker, Button, message } from "antd";
import { dashboardApi } from "@/api/dashboard";

export default function ReportExport() {
  const [month, setMonth] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleExport = async () => {
    if (!month) {
      message.warning("请选择月份");
      return;
    }
    setLoading(true);
    try {
      const { data } = await dashboardApi.exportMonthlyReport(month);
      message.success(data.message || "报表生成中，生成完毕后将推送至消息中心");
    } catch (err: unknown) {
      const detail = (err as { detail?: string })?.detail || "导出失败";
      message.error(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="月报导出">
      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <DatePicker
          picker="month"
          onChange={(d) => setMonth(d ? d.format("YYYY-MM") : null)}
          placeholder="选择月份"
        />
        <Button type="primary" loading={loading} onClick={handleExport}>
          导出月报
        </Button>
      </div>
    </Card>
  );
}
