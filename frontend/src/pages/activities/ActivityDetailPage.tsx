import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Descriptions, Tabs, Button, Tag, Spin, Typography, Space, Modal, Input, message, List } from "antd";
import { ArrowLeftOutlined, CheckOutlined, CloseOutlined, EditOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useActivity, useActivityHistory, useActivityDocuments } from "@/hooks/useActivityQueries";
import StatusTimeline from "@/components/activities/StatusTimeline";
import DocumentUpload from "@/components/documents/DocumentUpload";
import DocumentList from "@/components/documents/DocumentList";
import WorkflowActions from "@/components/workflows/WorkflowActions";
import FilingValidatePanel from "@/components/filings/FilingValidatePanel";
import FilingPackModal from "@/components/filings/FilingPackModal";
import HandoverConfirm from "@/components/filings/HandoverConfirm";
import { filingsApi } from "@/api/filings";
import { activitiesApi } from "@/api/activities";
import { materialsApi } from "@/api/materials";
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

  const FILING_STATUSES = [
    "待备案申请", "备案材料已交接", "审批通过", "审批通过-待举办",
    "举办中", "已结束", "待补充备案材料", "不通过/已终止",
  ];
  const showFiling = activity?.status
    ? FILING_STATUSES.includes(activity.status)
    : false;
  const canOperateFiling =
    showFiling && activity?.status === "待备案申请" && permissions.includes("pack_filing");

  const { data: validation = [], isLoading: validationLoading } = useQuery({
    queryKey: ["activities", id, "filing", "validate"],
    queryFn: () => filingsApi.validate(id!).then((r) => r.data),
    enabled: showFiling,
  });

  const { data: securityPlan } = useQuery({
    queryKey: ["activities", id, "security-plan"],
    queryFn: () => activitiesApi.getSecurityPlan(id!).then((r) => r.data),
    enabled: !!id,
  });

  const { data: filingStatus, refetch: refetchFilingStatus } = useQuery({
    queryKey: ["activities", id, "filing", "status"],
    queryFn: () => filingsApi.getStatus(id!).then((r) => r.data),
    enabled: showFiling,
  });

  const { data: materials = [], refetch: refetchMaterials } = useQuery({
    queryKey: ["activities", id, "materials"],
    queryFn: () => materialsApi.list(id!).then((r) => r.data),
    enabled: showFiling,
  });

  const { data: auditHistory = [] } = useQuery({
    queryKey: ["activities", id, "materials", "audit-history"],
    queryFn: () => materialsApi.getAuditHistory(id!).then((r) => r.data),
    enabled: showFiling,
  });

  const queryClient = useQueryClient();
  const [auditTarget, setAuditTarget] = useState<{ id: string; name: string } | null>(null);
  const [auditConclusion, setAuditConclusion] = useState<string>("qualified");
  const [auditOpinion, setAuditOpinion] = useState("");

  const signMutation = useMutation({
    mutationFn: (matId: string) => materialsApi.sign(id!, matId),
    onSuccess: () => {
      message.success("签署成功");
      refetchMaterials();
    },
    onError: (err: any) => message.error(err?.detail || "签署失败"),
  });

  const auditMutation = useMutation({
    mutationFn: ({ matId, conclusion, opinion }: { matId: string; conclusion: string; opinion?: string }) =>
      materialsApi.audit(id!, matId, conclusion, opinion),
    onSuccess: () => {
      message.success("审核完成");
      setAuditTarget(null);
      refetchMaterials();
      queryClient.invalidateQueries({ queryKey: ["activities", id, "materials", "audit-history"] });
    },
    onError: (err: any) => message.error(err?.detail || "审核失败"),
  });

  const canSign = permissions.includes("sign_document");
  const canAudit = permissions.includes("audit_material");
  const allSigned = materials.length > 0 && materials.every(m => m.sign_status === "signed");
  const allQualified = materials.length > 0 && materials.every(m => m.is_qualified);
  const canPack = canOperateFiling && allSigned && !filingStatus?.packed;

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
                <Descriptions.Item label="联系人">
                  {activity.sponsor_contact || "—"}
                </Descriptions.Item>
                <Descriptions.Item label="联系方式">
                  {activity.sponsor_phone || "—"}
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
                {securityPlan?.risk_level && (
                  <Descriptions.Item label="风险等级">
                    <Tag color={
                      securityPlan.risk_level === "高" ? "red"
                      : securityPlan.risk_level === "低" ? "green"
                      : "orange"
                    }>
                      {securityPlan.risk_level}
                    </Tag>
                  </Descriptions.Item>
                )}
                {securityPlan?.audit_status && (
                  <Descriptions.Item label="安保审核">
                    {securityPlan.audit_status}
                  </Descriptions.Item>
                )}
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
                  label: (
                    <span>
                      备案
                      {filingStatus?.handed_over && (
                        <Tag color="green" style={{ marginLeft: 8 }}>已交接</Tag>
                      )}
                      {filingStatus?.packed && !filingStatus?.handed_over && (
                        <Tag color="blue" style={{ marginLeft: 8 }}>已打包</Tag>
                      )}
                    </span>
                  ),
                  children: (
                    <div>
                      {validationLoading ? (
                        <Spin />
                      ) : (
                        <FilingValidatePanel data={validation} />
                      )}
                      {/* materials with sign/audit */}
                      {materials.length > 0 && (
                        <div style={{ marginTop: 16 }}>
                          <Typography.Text strong>关键材料</Typography.Text>
                          <List
                            size="small"
                            dataSource={materials}
                            renderItem={(m) => (
                              <List.Item
                                actions={[
                                  canSign && m.sign_status !== "signed" && (
                                    <Button
                                      size="small"
                                      icon={<EditOutlined />}
                                      onClick={() => signMutation.mutate(m.id)}
                                      loading={signMutation.isPending}
                                    >
                                      签署
                                    </Button>
                                  ),
                                  canAudit && (
                                    <Button
                                      size="small"
                                      icon={m.is_qualified ? <CheckOutlined /> : <CloseOutlined />}
                                      onClick={() => {
                                        setAuditTarget({ id: m.id, name: m.name });
                                        setAuditConclusion(m.is_qualified ? "qualified" : "unqualified");
                                        setAuditOpinion("");
                                      }}
                                    >
                                      审查
                                    </Button>
                                  ),
                                ].filter(Boolean)}
                              >
                                <List.Item.Meta
                                  title={m.name}
                                  description={
                                    <Space size={4} wrap>
                                      <Tag color={m.sign_status === "signed" ? "green" : "default"}>
                                        {m.sign_status === "signed" ? "已签署" : "未签署"}
                                      </Tag>
                                      <Tag color={m.is_qualified ? "green" : "red"}>
                                        {m.is_qualified ? "合格" : "不合格"}
                                      </Tag>
                                      {m.audit_round > 0 && (
                                        <Tag>审核 {m.audit_round} 轮</Tag>
                                      )}
                                    </Space>
                                  }
                                />
                              </List.Item>
                            )}
                          />
                        </div>
                      )}

                      {/* audit history */}
                      {auditHistory.length > 0 && (
                        <div style={{ marginTop: 16 }}>
                          <Typography.Text strong>审核记录</Typography.Text>
                          <List
                            size="small"
                            dataSource={auditHistory}
                            renderItem={(h) => (
                              <List.Item>
                                <List.Item.Meta
                                  title={`${h.user_name} · ${h.action === "sign" ? "签署" : "审查"}`}
                                  description={h.opinion || h.conclusion || "-"}
                                />
                                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                                  {new Date(h.created_at).toLocaleString("zh-CN")}
                                </Typography.Text>
                              </List.Item>
                            )}
                          />
                        </div>
                      )}

                      {canOperateFiling && filingStatus && (
                        <div style={{ marginTop: 16 }}>
                          {canPack && (
                            <Button
                              type="primary"
                              onClick={() => setFilingModal("pack")}
                            >
                              打包备案材料
                            </Button>
                          )}
                          {!allSigned && materials.length > 0 && (
                            <Typography.Text type="secondary" style={{ display: "block", marginTop: 4 }}>
                              需全部材料签署后方可打包
                            </Typography.Text>
                          )}
                          {filingStatus.packed && !filingStatus.handed_over && (
                            <>
                              <Tag color="blue" style={{ marginRight: 8 }}>已打包 ✓</Tag>
                              <Button onClick={() => setFilingModal("handover")}>
                                确认纸质交接
                              </Button>
                            </>
                          )}
                          {filingStatus.handed_over && (
                            <Tag color="green">已交接 ✓</Tag>
                          )}
                        </div>
                      )}

                      {/* audit modal */}
                      <Modal
                        title={`审查: ${auditTarget?.name}`}
                        open={!!auditTarget}
                        onCancel={() => setAuditTarget(null)}
                        onOk={() => {
                          if (auditTarget) {
                            auditMutation.mutate({
                              matId: auditTarget.id,
                              conclusion: auditConclusion,
                              opinion: auditOpinion || undefined,
                            });
                          }
                        }}
                        confirmLoading={auditMutation.isPending}
                        okText="提交审查"
                        cancelText="取消"
                      >
                        <div style={{ marginBottom: 8 }}>
                          <Tag
                            color={auditConclusion === "qualified" ? "green" : "red"}
                            style={{ cursor: "pointer" }}
                            onClick={() => setAuditConclusion(
                              auditConclusion === "qualified" ? "unqualified" : "qualified"
                            )}
                          >
                            {auditConclusion === "qualified" ? "合格" : "不合格"}
                          </Tag>
                          <Typography.Text type="secondary" style={{ marginLeft: 8 }}>
                            点击切换结论
                          </Typography.Text>
                        </div>
                        <Input.TextArea
                          placeholder="审查意见（可选）"
                          rows={2}
                          value={auditOpinion}
                          onChange={(e) => setAuditOpinion(e.target.value)}
                        />
                      </Modal>
                      <FilingPackModal
                        open={filingModal === "pack"}
                        activityId={id!}
                        onClose={() => {
                          setFilingModal(null);
                          refetchFilingStatus();
                        }}
                      />
                      <HandoverConfirm
                        open={filingModal === "handover"}
                        activityId={id!}
                        onClose={() => {
                          setFilingModal(null);
                          refetchFilingStatus();
                        }}
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
