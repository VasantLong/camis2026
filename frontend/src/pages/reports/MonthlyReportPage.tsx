import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { Button, Card, Col, Row, Statistic, Table, Typography, Spin, Empty, Result, Space } from "antd";
import { DownloadOutlined } from "@ant-design/icons";
import { Pie, Column, Line } from "@ant-design/charts";
import { useAuthStore } from "@/stores/authStore";
import { dashboardApi } from "@/api/dashboard";
import client from "@/api/client";

const { Title, Text } = Typography;

interface ReportData {
  month: string;
  generated_at: string;
  total: number;
  by_status: Record<string, number>;
  by_type: Record<string, number>;
  daily_creation: { date: string; count: number }[];
  compliance_rate: number;
  anomalies: { id: string; name: string; status: string; reason: string | null; changed_at: string }[];
}

export default function MonthlyReportPage() {
  const { month } = useParams<{ month: string }>();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const dataKey = searchParams.get("data_key");
  const setAccessToken = useAuthStore((s) => s.setAccessToken);
  const isPlaywright = !!(token && dataKey);

  const [data, setData] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chartsReady, setChartsReady] = useState(false);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!month) {
      setError("缺少必要参数");
      setLoading(false);
      return;
    }

    if (isPlaywright) {
      setAccessToken(token!);
      client
        .get<ReportData>(`/dashboard/reports/${month}/data`, {
          params: { data_key: dataKey },
        })
        .then((res) => setData(res.data))
        .catch((err) => setError(err?.response?.data?.detail || "获取报表数据失败"))
        .finally(() => setLoading(false));
    } else {
      client
        .get<ReportData>(`/dashboard/reports/${month}/view`)
        .then((res) => setData(res.data))
        .catch((err) => setError(err?.response?.data?.detail || "获取报表数据失败"))
        .finally(() => setLoading(false));
    }
  }, [month, token, dataKey, isPlaywright, setAccessToken]);

  useEffect(() => {
    if (data) {
      const t = setTimeout(() => setChartsReady(true), 2000);
      return () => clearTimeout(t);
    }
  }, [data]);

  const handleDownload = async () => {
    if (!month) return;
    setDownloading(true);
    try {
      await dashboardApi.downloadReport(month);
    } catch (err: unknown) {
      const detail = (err as { detail?: string })?.detail || "下载失败";
      if (!detail.includes("不存在")) throw err;
    } finally {
      setDownloading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return <Result status="error" title="报表获取失败" subTitle={error} />;
  }

  if (!data) return null;

  const statusPieData = Object.entries(data.by_status).map(([status, value]) => ({
    type: status,
    value,
  }));

  const typeBarData = Object.entries(data.by_type).map(([type, value]) => ({
    type,
    value,
  }));

  const trendData = data.daily_creation.map((d) => ({
    date: d.date,
    count: d.count,
  }));

  const anomalyColumns = [
    { title: "活动名称", dataIndex: "name", key: "name", ellipsis: true },
    { title: "变更状态", dataIndex: "status", key: "status", width: 120 },
    { title: "变更原因", dataIndex: "reason", key: "reason", width: 200, ellipsis: true,
      render: (v: string | null) => v || "-" },
    { title: "变更时间", dataIndex: "changed_at", key: "changed_at", width: 170,
      render: (v: string) => v?.slice(0, 10) },
  ];

  return (
    <div style={{ padding: 24, maxWidth: 1000, margin: "0 auto" }}>
      {isPlaywright && chartsReady && <div className="chart-ready" />}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
        <div>
          <Title level={3} style={{ marginBottom: 4 }}>
            CAMIS 月度合规报告
          </Title>
          <Text type="secondary">
            {month} · 生成时间 {data.generated_at?.slice(0, 19).replace("T", " ")}
          </Text>
        </div>
        {!isPlaywright && (
          <Button
            type="primary"
            icon={<DownloadOutlined />}
            loading={downloading}
            onClick={handleDownload}
          >
            下载 PDF
          </Button>
        )}
      </div>

      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic title="本月新增活动" value={data.total} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="合规率"
              value={data.compliance_rate * 100}
              suffix="%"
              precision={1}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="状态种类"
              value={Object.keys(data.by_status).length}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="异常活动"
              value={data.anomalies.length}
              valueStyle={data.anomalies.length > 0 ? { color: "#cf1322" } : undefined}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={12}>
          <Card title="活动状态分布" style={{ height: 380 }}>
            {statusPieData.length > 0 ? (
              <Pie
                data={statusPieData}
                angleField="value"
                colorField="type"
                radius={0.8}
                innerRadius={0.5}
                label={{ text: (d: { type: string; value: number }) => d.type, position: "outside" }}
                height={280}
                legend={{ position: "bottom" }}
              />
            ) : (
              <Empty description="暂无数据" />
            )}
          </Card>
        </Col>
        <Col span={12}>
          <Card title="活动类型分布" style={{ height: 380 }}>
            {typeBarData.length > 0 ? (
              <Column
                data={typeBarData}
                xField="type"
                yField="value"
                height={280}
                label={{ position: "top" }}
              />
            ) : (
              <Empty description="暂无数据" />
            )}
          </Card>
        </Col>
      </Row>

      <Row style={{ marginTop: 24 }}>
        <Col span={24}>
          <Card title="每日新增趋势">
            {trendData.length > 0 ? (
              <Line
                data={trendData}
                xField="date"
                yField="count"
                height={250}
                point={{ size: 4 }}
                smooth
              />
            ) : (
              <Empty description="暂无数据" />
            )}
          </Card>
        </Col>
      </Row>

      {data.anomalies.length > 0 && (
        <Row style={{ marginTop: 24 }}>
          <Col span={24}>
            <Card title="异常活动">
              <Table
                columns={anomalyColumns}
                dataSource={data.anomalies}
                rowKey="id"
                pagination={false}
                size="small"
              />
            </Card>
          </Col>
        </Row>
      )}

      <div style={{ textAlign: "center", marginTop: 32 }}>
        <Text type="secondary">CAMIS 合规管理系统</Text>
      </div>
    </div>
  );
}
