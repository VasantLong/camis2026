import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Descriptions, Tabs, Button, Tag, Spin, Typography } from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { useQuery } from "@tanstack/react-query";
import { useActivity, useActivityHistory, useActivityDocuments } from "@/hooks/useActivityQueries";
import StatusTimeline from "@/components/activities/StatusTimeline";
import DocumentUpload from "@/components/documents/DocumentUpload";
import DocumentList from "@/components/documents/DocumentList";
import WorkflowActions from "@/components/workflows/WorkflowActions";
import FilingValidatePanel from "@/components/filings/FilingValidatePanel";
import FilingPackModal from "@/components/filings/FilingPackModal";
import HandoverConfirm from "@/components/filings/HandoverConfirm";
import { filingsApi } from "@/api/filings";
import { useAuthStore } from "@/stores/authStore";
import { STATUS_COLOR_MAP } from "@/utils/constants";

export default function ActivityDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: activity, isLoading } = useActivity(id!);
  const { data: history = [], isLoading: historyLoading } =
    useActivityHistory(id!);
  const { data: documents = [], isLoading: docsLoading } =
    useActivityDocuments(id!);
  const [filingModal, setFilingModal] = useState<"pack" | "handover" | null>(
    null
  );
  const userPermissions = useAuthStore((s) => s.user?.permissions);
  const permissions = userPermissions ?? [];
  const showFiling =
    permissions.includes("pack_filing") &&
    activity?.status === "待备案申请";

  const { data: validation = [], isLoading: validationLoading } = useQuery({
    queryKey: ["activities", id, "filing", "validate"],
    queryFn: () => filingsApi.validate(id!).then((r) => r.data),
    enabled: showFiling,
  });

  if (isLoading) {
    return (
      <div style={{ textAlign: "center", padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!activity) {
    return (
      <div style={{ padding: 24 }}>
        <Typography.Text type="secondary">活动不存在</Typography.Text>
      </div>
    );
  }

  return (
    <div style={{ padding: 24 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 16,
          marginBottom: 24,
        }}
      >
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate("/activities")}
        />
        <Typography.Title level={3} style={{ margin: 0 }}>
          {activity.name}
        </Typography.Title>
        <Tag color={STATUS_COLOR_MAP[activity.status] || "default"}>
          {activity.status}
        </Tag>
      </div>

      <WorkflowActions
        activityId={id!}
        currentStatus={activity.status}
      />

      <Tabs
        defaultActiveKey="detail"
        items={[
          {
            key: "detail",
            label: "基本信息",
            children: (
              <Descriptions bordered column={2}>
                <Descriptions.Item label="活动名称">
                  {activity.name}
                </Descriptions.Item>
                <Descriptions.Item label="活动类型">
                  {activity.type}
                </Descriptions.Item>
                <Descriptions.Item label="活动地点">
                  {activity.location}
                </Descriptions.Item>
                <Descriptions.Item label="主办方">
                  {activity.sponsor}
                </Descriptions.Item>
                <Descriptions.Item label="预计时间">
                  {dayjs(activity.estimated_time).format("YYYY-MM-DD HH:mm")}
                </Descriptions.Item>
                <Descriptions.Item label="截止日期">
                  {dayjs(activity.deadline).format("YYYY-MM-DD HH:mm")}
                </Descriptions.Item>
                <Descriptions.Item label="创建时间">
                  {dayjs(activity.created_at).format("YYYY-MM-DD HH:mm")}
                </Descriptions.Item>
                <Descriptions.Item label="更新时间">
                  {dayjs(activity.updated_at).format("YYYY-MM-DD HH:mm")}
                </Descriptions.Item>
              </Descriptions>
            ),
          },
          {
            key: "history",
            label: "状态历史",
            children: historyLoading ? (
              <Spin />
            ) : (
              <StatusTimeline history={history} />
            ),
          },
          {
            key: "documents",
            label: "文档",
            children: (
              <div>
                <DocumentUpload activityId={id!} />
                <div style={{ marginTop: 16 }}>
                  <DocumentList documents={documents} loading={docsLoading} />
                </div>
              </div>
            ),
          },
          ...(showFiling
            ? [
                {
                  key: "filing" as string,
                  label: "备案",
                  children: (
                    <div>
                      {validationLoading ? (
                        <Spin />
                      ) : (
                        <FilingValidatePanel data={validation} />
                      )}
                      <div style={{ marginTop: 16 }}>
                        <Button
                          type="primary"
                          onClick={() => setFilingModal("pack")}
                          style={{ marginRight: 8 }}
                        >
                          打包备案材料
                        </Button>
                        <Button onClick={() => setFilingModal("handover")}>
                          确认纸质交接
                        </Button>
                      </div>
                      <FilingPackModal
                        open={filingModal === "pack"}
                        activityId={id!}
                        onClose={() => setFilingModal(null)}
                      />
                      <HandoverConfirm
                        open={filingModal === "handover"}
                        activityId={id!}
                        onClose={() => setFilingModal(null)}
                      />
                    </div>
                  ),
                },
              ]
            : []),
        ]}
      />
    </div>
  );
}
