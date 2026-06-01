import { useState } from "react";
import { Button, Card, DatePicker, Space, message } from "antd";
import dayjs from "dayjs";
import { dashboardApi } from "@/api/dashboard";

const THIS_MONTH = dayjs().format("YYYY-MM");
const LAST_MONTH = dayjs().subtract(1, "month").format("YYYY-MM");

export default function ReportExport() {
  const [month, setMonth] = useState<string>(THIS_MONTH);
  const [loading, setLoading] = useState(false);

  const handleExport = async () => {
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
      <Space size={12} wrap>
        <Button onClick={() => setMonth(THIS_MONTH)} type={month === THIS_MONTH ? "primary" : "default"}>
          本月 ({THIS_MONTH})
        </Button>
        <Button onClick={() => setMonth(LAST_MONTH)} type={month === LAST_MONTH ? "primary" : "default"}>
          上月 ({LAST_MONTH})
        </Button>
        <DatePicker
          picker="month"
          value={dayjs(month)}
          onChange={(d) => setMonth(d ? d.format("YYYY-MM") : THIS_MONTH)}
          disabledDate={(d) => d && d.isAfter(dayjs().endOf("month"))}
          allowClear={false}
        />
        <Button type="primary" loading={loading} onClick={handleExport}>
          导出月报
        </Button>
      </Space>
    </Card>
  );
}
