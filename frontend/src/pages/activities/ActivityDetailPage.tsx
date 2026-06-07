import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Descriptions, Tabs, Button, Tag, Spin, Typography, Space, Modal, Input, message, List, Select, Upload, Checkbox } from "antd";
import { ArrowLeftOutlined, CheckOutlined, CloseOutlined, EditOutlined, UploadOutlined } from "@ant-design/icons";
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
import TemplateForm from "@/components/templates/TemplateForm";
import VersionTimeline from "@/components/templates/VersionTimeline";
import VersionSnapshot from "@/components/templates/VersionSnapshot";
import { validateActivityPlan, validateSecurityPlan, type ValidationError } from "@/utils/templateValidation";
import { filingsApi } from "@/api/filings";
import { documentsApi } from "@/api/documents";
import { activitiesApi } from "@/api/activities";
import { materialsApi } from "@/api/materials";
import { templatesApi } from "@/api/templates";
import { useAuthStore } from "@/stores/authStore";
import { STATUS_COLOR_MAP } from "@/utils/constants";
import type { VersionItem, VersionDetail, VersionDiff, SchemaResponse } from "@/types/template";

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

  // ── template queries ──
  const canViewPlan = permissions.includes("submit_plan") || permissions.includes("view_owned_activity");
  const canViewSecurity = permissions.includes("manage_security") || permissions.includes("view_owned_activity");
  const canEditPlan = permissions.includes("submit_plan");
  const canEditSecurity = permissions.includes("manage_security");
  const isManager = permissions.includes("review_security_plan");
  const isAdmin = permissions.includes("view_dashboard") && !canEditPlan && !canEditSecurity;

  const { data: planSchema, refetch: refetchPlanSchema } = useQuery({
    queryKey: ["activities", id, "templates", "plan-schema"],
    queryFn: () => templatesApi.getPlanSchema(id!).then((r) => r.data),
    enabled: canViewPlan,
  });

  const { data: planVersions = [], refetch: refetchPlanVersions } = useQuery({
    queryKey: ["activities", id, "templates", "plan-versions"],
    queryFn: () => templatesApi.getPlanVersions(id!).then((r) => r.data),
    enabled: canViewPlan,
  });

  const { data: securityPlanSchema, refetch: refetchSecuritySchema } = useQuery({
    queryKey: ["activities", id, "templates", "security-schema"],
    queryFn: () => templatesApi.getSecurityPlanSchema(id!).then((r) => r.data),
    enabled: canViewSecurity,
  });

  const { data: securityPlanVersions = [], refetch: refetchSecurityVersions } = useQuery({
    queryKey: ["activities", id, "templates", "security-versions"],
    queryFn: () => templatesApi.getSecurityPlanVersions(id!).then((r) => r.data),
    enabled: canViewSecurity,
  });

  const queryClient = useQueryClient();
  const [auditTarget, setAuditTarget] = useState<{ id: string; name: string } | null>(null);
  const [auditConclusion, setAuditConclusion] = useState<string>("qualified");
  const [auditOpinion, setAuditOpinion] = useState("");
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);
  const [validationModalOpen, setValidationModalOpen] = useState(false);
  const [highlightFields, setHighlightFields] = useState<string[] | undefined>(undefined);
  const [planFinalizeOpen, setPlanFinalizeOpen] = useState(false);
  const [securitySubmitOpen, setSecuritySubmitOpen] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [managerSignaturePath, setManagerSignaturePath] = useState<string | null>(null);
  const [signaturePreview, setSignaturePreview] = useState<string | null>(null);
  const [signatureUploadTime, setSignatureUploadTime] = useState<string | null>(null);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReasons, setRejectReasons] = useState<string[]>([]);
  const [rejectComment, setRejectComment] = useState("");
  const [rejecting, setRejecting] = useState(false);

  const REJECT_PRESETS = [
    "安保人员配置不足或不当",
    "动线设计不合理",
    "设备清单不完善",
    "应急预案不充分",
    "医疗救护措施不完善",
    "消防措施不充分",
    "人流管控方案不合理",
    "其他（需补充说明）",
  ];

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
                <Descriptions.Item label="主办方联系人">
                  {activity.sponsor_contact || "—"}
                </Descriptions.Item>
                <Descriptions.Item label="主办方联系方式">
                  {activity.sponsor_phone || "—"}
                </Descriptions.Item>
                <Descriptions.Item label="编制人">
                  {activity.designer_name || "—"}
                </Descriptions.Item>
                <Descriptions.Item label="编制人联系方式">
                  {activity.designer_phone || "—"}
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
          ...(canViewPlan
            ? [
                {
                  key: "plan" as string,
                  label: "活动方案",
                  children: planSchema ? (
                    <div>
                      {canEditPlan ? (
                        <>
                          <TemplateForm
                            activityId={id!}
                            schema={planSchema}
                            highlightFields={highlightFields}
                            onSaveDraft={async (data) => {
                              await templatesApi.savePlanDraft(id!, data);
                            }}
                            onSubmit={async (data) => {
                              const res = await templatesApi.generatePlan(id!, data);
                              const result = res.data;
                              queryClient.setQueryData<VersionItem[]>(
                                ["activities", id, "templates", "plan-versions"],
                                (old) => {
                                  const prev = (old || []).map((v) => ({ ...v, is_current: false }));
                                  return [
                                    {
                                      id: result.id,
                                      version_number: result.version_number,
                                      generated_by: "",
                                      created_at: result.created_at,
                                      is_current: true,
                                      pdf_ready: result.pdf_ready,
                                    },
                                    ...prev,
                                  ];
                                },
                              );
                              queryClient.setQueryData<SchemaResponse>(
                                ["activities", id, "templates", "plan-schema"],
                                (old) => old ? { ...old, current_version: result.version_number, has_draft: false, draft_data: null, snapshot_data: data } : old as any,
                              );
                              return result;
                            }}
                          />
                          <VersionTimeline
                            versions={planVersions}
                            onViewDetail={(v) =>
                              templatesApi.getPlanVersionDetail(id!, v).then((r) => r.data)
                            }
                            onDiff={(v1, v2) =>
                              templatesApi.getPlanVersionDiff(id!, v1, v2).then((r) => r.data)
                            }
                            onPreview={async (v) => {
                              const r = await templatesApi.getPlanVersionPreview(id!, v);
                              return r.data.url;
                            }}
                          />
                          {planVersions.length > 0 && activity?.status === "待设计方案" && (
                            <Button
                              type="primary"
                              style={{ marginTop: 16 }}
                              onClick={() => {
                                const errs = validateActivityPlan(planSchema?.snapshot_data);
                                if (errs.length > 0) {
                                  setValidationErrors(errs);
                                  setValidationModalOpen(true);
                                } else {
                                  setPlanFinalizeOpen(true);
                                }
                              }}
                            >
                              最终确定方案
                            </Button>
                          )}
                          <Modal
                            title="确认最终确定方案"
                            open={planFinalizeOpen}
                            onOk={async () => {
                              setFinalizing(true);
                              try {
                                await templatesApi.finalizePlan(id!);
                                message.success("方案已最终确定，已提交至安保方案设计");
                                queryClient.invalidateQueries({ queryKey: ["activities", id] });
                                setPlanFinalizeOpen(false);
                              } catch (e: any) {
                                message.error(e?.response?.data?.detail || "提交失败");
                              } finally {
                                setFinalizing(false);
                              }
                            }}
                            onCancel={() => setPlanFinalizeOpen(false)}
                            okText="确认提交"
                            cancelText="取消"
                            confirmLoading={finalizing}
                          >
                            方案将提交至安保方案设计阶段，提交后不可修改。确认继续？
                          </Modal>
                        </>
                      ) : isAdmin ? (
                        <VersionTimeline
                          versions={planVersions}
                          onViewDetail={(v) =>
                            templatesApi.getPlanVersionDetail(id!, v).then((r) => r.data)
                          }
                          onDiff={(v1, v2) =>
                            templatesApi.getPlanVersionDiff(id!, v1, v2).then((r) => r.data)
                          }
                          onPreview={async (v) => {
                            const r = await templatesApi.getPlanVersionPreview(id!, v);
                            return r.data.url;
                          }}
                        />
                      ) : (
                        <VersionSnapshot schema={planSchema} />
                      )}
                    </div>
                  ) : (
                    <Spin />
                  ),
                },
              ]
            : []),
          ...(canViewSecurity
            ? [
                {
                  key: "security-plan" as string,
                  label: "安保方案",
                  children: securityPlanSchema ? (
                    <div>
                      {isManager && securityPlan?.audit_status === "待签署" ? (
                        <>
                          <div style={{ padding: 16, border: "1px solid #1677ff", borderRadius: 8 }}>
                            <Typography.Title level={5}>安保负责人签署确认</Typography.Title>
                            <VersionSnapshot schema={securityPlanSchema} />
                          <div style={{ marginTop: 16 }}>
                            <Space>
                              <Upload
                                accept="image/*"
                                maxCount={1}
                                showUploadList={false}
                                customRequest={async ({ file, onSuccess, onError }) => {
                                  try {
                                    const f = file as File;
                                    const ext = f.name.split(".").pop() || "png";
                                    const ts = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 14);
                                    const renamed = new File([f], `manager_sign_${ts}.${ext}`, { type: f.type });
                                    const res = await documentsApi.upload(id!, renamed, ["signature"]);
                                    const doc = res.data;
                                    setManagerSignaturePath(doc.minio_path);
                                    setSignaturePreview(URL.createObjectURL(f));
                                    setSignatureUploadTime(new Date().toLocaleString("zh-CN"));
                                    onSuccess?.(doc);
                                    message.success("已上传签名图片");
                                  } catch {
                                    onError?.(new Error("上传失败"));
                                    message.error("签名上传失败");
                                  }
                                }}
                              >
                                <Button icon={<UploadOutlined />}>上传签名图片</Button>
                              </Upload>
                              {signaturePreview && (
                                <div>
                                  <img src={signaturePreview} alt="签名预览" style={{ maxWidth: 200, maxHeight: 80, borderRadius: 4, border: "1px solid #d9d9d9", display: "block" }} />
                                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>上传时间：{signatureUploadTime}</Typography.Text>
                                </div>
                              )}
                              <Button
                                type="primary"
                                disabled={!managerSignaturePath}
                                onClick={async () => {
                                  setFinalizing(true);
                                  try {
                                    await templatesApi.signSecurityPlan(id!, managerSignaturePath!);
                                    message.success("已签署确认，方案已提交至备案申请");
                                    setManagerSignaturePath(null);
                                    queryClient.invalidateQueries({ queryKey: ["activities", id] });
                                    queryClient.invalidateQueries({ queryKey: ["activities", id, "security-plan"] });
                                    refetchSecuritySchema();
                                  } catch (e: any) {
                                    message.error(e?.response?.data?.detail || "签署失败");
                                  } finally {
                                    setFinalizing(false);
                                  }
                                }}
                                loading={finalizing}
                              >
                                确认签署并提交备案
                              </Button>
                              <Button
                                danger
                                onClick={() => {
                                  setRejectReasons([]);
                                  setRejectComment("");
                                  setRejectOpen(true);
                                }}
                              >
                                驳回
                              </Button>
                            </Space>
                          </div>
                        </div>
                        <Modal
                          title="驳回安保方案"
                          open={rejectOpen}
                          onCancel={() => setRejectOpen(false)}
                          onOk={async () => {
                            if (rejectReasons.length === 0 && !rejectComment) return;
                            setRejecting(true);
                            try {
                              await templatesApi.rejectSecurityPlan(id!, rejectReasons, rejectComment || undefined);
                              message.success("已驳回");
                              setRejectOpen(false);
                              queryClient.invalidateQueries({ queryKey: ["activities", id] });
                              queryClient.invalidateQueries({ queryKey: ["activities", id, "security-plan"] });
                              refetchSecuritySchema();
                            } catch (e: any) {
                              message.error(e?.response?.data?.detail || "驳回失败");
                            } finally {
                              setRejecting(false);
                            }
                          }}
                          okText="确认驳回"
                          okButtonProps={{ danger: true, loading: rejecting }}
                          cancelText="取消"
                        >
                          <div style={{ marginBottom: 12 }}>
                            <Typography.Text strong>驳回原因</Typography.Text>
                          </div>
                          <Checkbox.Group
                            options={REJECT_PRESETS}
                            value={rejectReasons}
                            onChange={(v) => setRejectReasons(v as string[])}
                            style={{ display: "flex", flexDirection: "column", gap: 8 }}
                          />
                          <div style={{ marginTop: 12 }}>
                            <Input.TextArea
                              placeholder="补充说明（可选）"
                              rows={2}
                              value={rejectComment}
                              onChange={(e) => setRejectComment(e.target.value)}
                            />
                          </div>
                        </Modal>
                        </>
                      ) : isManager && securityPlan?.audit_status === "已签署" ? (
                        <div>
                          <div style={{ marginBottom: 16, padding: "8px 16px", background: "#f6ffed", borderRadius: 4, border: "1px solid #b7eb8f" }}>
                            <Typography.Text strong style={{ color: "#52c41a" }}>已签署确认</Typography.Text>
                            <Typography.Text type="secondary" style={{ marginLeft: 8 }}>
                              {securityPlan?.sign_time ? new Date(securityPlan.sign_time).toLocaleString("zh-CN") : ""}
                            </Typography.Text>
                          </div>
                          <VersionSnapshot schema={securityPlanSchema} />
                          <VersionTimeline
                            versions={securityPlanVersions}
                            onViewDetail={(v) =>
                              templatesApi.getSecurityPlanVersionDetail(id!, v).then((r) => r.data)
                            }
                            onDiff={(v1, v2) =>
                              templatesApi.getSecurityPlanVersionDiff(id!, v1, v2).then((r) => r.data)
                            }
                          />
                        </div>
                      ) : isManager ? (
                        <VersionTimeline
                          versions={securityPlanVersions}
                          onViewDetail={(v) =>
                            templatesApi.getSecurityPlanVersionDetail(id!, v).then((r) => r.data)
                          }
                          onDiff={(v1, v2) =>
                            templatesApi.getSecurityPlanVersionDiff(id!, v1, v2).then((r) => r.data)
                          }
                        />
                      ) : canEditSecurity ? (
                        <>
                          {securityPlan?.last_reject_reason && (
                            <div style={{ marginBottom: 16, padding: "8px 16px", background: "#fff2f0", borderRadius: 4, border: "1px solid #ffccc7" }}>
                              <Typography.Text strong style={{ color: "#ff4d4f" }}>
                                被驳回（第{securityPlan.reject_count || 1}次）
                              </Typography.Text>
                              <Typography.Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                                {securityPlan.rejected_at ? new Date(securityPlan.rejected_at).toLocaleString("zh-CN") : ""}
                              </Typography.Text>
                              <div style={{ marginTop: 4 }}>
                                <Typography.Text>{securityPlan.last_reject_reason}</Typography.Text>
                              </div>
                            </div>
                          )}
                          <div style={{ marginBottom: 16 }}>
                            <Typography.Text strong>风险等级</Typography.Text>
                            <Select
                              style={{ width: 200, marginLeft: 12 }}
                              placeholder="选择风险等级"
                              value={securityPlanSchema.risk_level || undefined}
                              disabled={!!(securityPlan?.audit_status && securityPlan.audit_status !== "待编制")}
                              options={[
                                { label: "大型", value: "大型" },
                                { label: "中型", value: "中型" },
                                { label: "高风险", value: "高风险" },
                              ]}
                              onChange={async (val) => {
                                await activitiesApi.updateSecurityPlan(id!, { risk_level: val });
                                refetchSecuritySchema();
                              }}
                            />
                          </div>
                          <TemplateForm
                            activityId={id!}
                            schema={securityPlanSchema}
                            disabled={!!(securityPlan?.audit_status && securityPlan.audit_status !== "待编制")}
                            onSaveDraft={async (data) => {
                              await templatesApi.saveSecurityPlanDraft(id!, data);
                            }}
                            onSubmit={async (data) => {
                              const res = await templatesApi.generateSecurityPlan(id!, data);
                              const result = res.data;
                              queryClient.setQueryData<VersionItem[]>(
                                ["activities", id, "templates", "security-versions"],
                                (old = []) => [
                                  {
                                    id: result.id,
                                    version_number: result.version_number,
                                    generated_by: "",
                                    created_at: result.created_at,
                                    is_current: true,
                                    pdf_ready: result.pdf_ready,
                                  },
                                  ...old.map((v) => ({ ...v, is_current: false })),
                                ],
                              );
                              refetchSecuritySchema();
                              return result;
                            }}
                          />
                          <VersionTimeline
                            versions={securityPlanVersions}
                            onViewDetail={(v) =>
                              templatesApi.getSecurityPlanVersionDetail(id!, v).then((r) => r.data)
                            }
                            onDiff={(v1, v2) =>
                              templatesApi.getSecurityPlanVersionDiff(id!, v1, v2).then((r) => r.data)
                            }
                          />
                          {(() => {
                            const auditStatus = securityPlan?.audit_status;
                            const submitted = auditStatus && auditStatus !== "待编制";
                            const btnLabel = submitted ? (
                              auditStatus === "待签署" ? "已提交审核，等待负责人签署" : "负责人已签署"
                            ) : "提交审核";

                            return securityPlanVersions.length > 0 && activity?.status === "待安保方案设计" && (
                              <Button
                                type="primary"
                                style={{ marginTop: 16 }}
                                disabled={submitted}
                                onClick={() => {
                                  const errs = validateSecurityPlan(securityPlanSchema?.snapshot_data, securityPlanSchema?.risk_level);
                                  if (errs.length > 0) {
                                    setValidationErrors(errs);
                                    setValidationModalOpen(true);
                                  } else {
                                    setSecuritySubmitOpen(true);
                                  }
                                }}
                              >
                                {btnLabel}
                              </Button>
                            );
                          })()}
                          <Modal
                            title="确认提交审核"
                            open={securitySubmitOpen}
                            onOk={async () => {
                              setFinalizing(true);
                              try {
                                await templatesApi.submitSecurityPlanReview(id!);
                                message.success("安保方案已提交审核，等待负责人签署");
                                queryClient.invalidateQueries({ queryKey: ["activities", id, "security-plan"] });
                                setSecuritySubmitOpen(false);
                                queryClient.invalidateQueries({ queryKey: ["activities", id] });
                                refetchSecuritySchema();
                              } catch (e: any) {
                                message.error(e?.response?.data?.detail || "提交失败");
                              } finally {
                                setFinalizing(false);
                              }
                            }}
                            onCancel={() => setSecuritySubmitOpen(false)}
                            okText="确认提交"
                            cancelText="取消"
                            confirmLoading={finalizing}
                          >
                            方案将提交给安保负责人审核签署，提交后不可修改。确认继续？
                          </Modal>
                        </>
                      ) : isAdmin ? (
                        <VersionTimeline
                          versions={securityPlanVersions}
                          onViewDetail={(v) =>
                            templatesApi.getSecurityPlanVersionDetail(id!, v).then((r) => r.data)
                          }
                          onDiff={(v1, v2) =>
                            templatesApi.getSecurityPlanVersionDiff(id!, v1, v2).then((r) => r.data)
                          }
                        />
                      ) : (
                        <VersionSnapshot schema={securityPlanSchema} />
                      )}
                    </div>
                  ) : (
                    <Spin />
                  ),
                },
              ]
            : []),
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
      <Modal
        title="以下字段需要完善后才能最终确定"
        open={validationModalOpen}
        onCancel={() => setValidationModalOpen(false)}
        footer={
          <Button type="primary" onClick={() => {
            setHighlightFields(validationErrors.filter(e => e.field).map(e => e.field));
            setValidationModalOpen(false);
          }}>
            修改方案
          </Button>
        }
      >
        <ul style={{ paddingLeft: 20, margin: 0 }}>
          {validationErrors.map((e, i) => (
            <li key={i} style={{ marginBottom: 6 }}>
              <strong>{e.label}</strong>：{e.reason}
            </li>
          ))}
        </ul>
      </Modal>
    </div>
  );
}
