import { Progress, Card, Row, Col } from "antd";
import { STATUS_COLOR_MAP } from "@/utils/constants";

interface Props {
  byStatus: Record<string, number>;
  total: number;
}

export default function StatusDistribution({ byStatus, total }: Props) {
  return (
    <Card title="状态分布" style={{ marginBottom: 16 }}>
      <Row gutter={[16, 16]}>
        {Object.entries(byStatus).map(([status, count]) => {
          const pct = total > 0 ? Math.round((count / total) * 100) : 0;
          const color = STATUS_COLOR_MAP[status] || "default";
          return (
            <Col key={status} xs={24} sm={12} md={8}>
              <div style={{ marginBottom: 4 }}>
                {status} ({count})
              </div>
              <Progress
                percent={pct}
                strokeColor={
                  color === "blue" ? "#1677ff" :
                  color === "cyan" ? "#13c2c2" :
                  color === "green" ? "#52c41a" :
                  color === "gold" ? "#faad14" :
                  color === "red" ? "#ff4d4f" :
                  color === "orange" ? "#fa8c16" :
                  color === "purple" ? "#722ed1" :
                  color === "geekblue" ? "#2f54eb" :
                  color === "warning" ? "#faad14" :
                  "#d9d9d9"
                }
                size="small"
              />
            </Col>
          );
        })}
      </Row>
    </Card>
  );
}
