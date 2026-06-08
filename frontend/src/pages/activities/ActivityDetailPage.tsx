import { useState, useEffect, useMemo } from "react";
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
import CommitmentSign from "@/components/templates/CommitmentSign";
import { useMaterialSchema } from "@/hooks/useMaterialSchema";
import { validateAllFieldsFilled, validateActivityPlan, validateSecurityPlan, validateRiskAssessment, validateResponsibilityLetter, type ValidationError } from "@/utils/templateValidation";
import { filingsApi } from "@/api/filings";
import { documentsApi } from "@/api/documents";
import { activitiesApi } from "@/api/activities";
import { materialsApi } from "@/api/materials";
import { workflowsApi } from "@/api/workflows";
import { templatesApi } from "@/api/templates";
import { useAuthStore } from "@/stores/authStore";
import { STATUS_COLOR_MAP } from "@/utils/constants";
import type { GenerateResponse, VersionItem, SchemaResponse } from "@/types/template";

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
  const [activeTab, setActiveTab] = useState("detail");
  const [templateTab, setTemplateTab] = useState<"security_plan" | "risk_assessment" | "responsibility_letter">("security_plan");
  // GovLiaison approval
  const [approvalDocPath, setApprovalDocPath] = useState<string | null>(null);
  const [approvalAction, setApprovalAction] = useState<"approve" | "revise" | "reject" | null>(null);
  const [approvalModalOpen, setApprovalModalOpen] = useState(false);
  const [approvalComment, setApprovalComment] = useState("");
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
    showFiling && (activity?.status === "待备案申请" || activity?.status === "待补充备案材料") && permissions.includes("pack_filing");

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
  const canEditPlan = permissions.includes("submit_plan") && activity?.status === "待设计方案";
  const canEditSecurity = permissions.includes("manage_security");
  const isManager = permissions.includes("review_security_plan");
  const isAdmin = permissions.includes("view_dashboard") && !canEditPlan && !canEditSecurity;
  const isGovLiaison = permissions.includes("audit_material") && !canEditPlan && !canEditSecurity && !isManager;

  const { data: planSchema } = useQuery({
    queryKey: ["activities", id, "templates", "plan-schema"],
    queryFn: () => templatesApi.getPlanSchema(id!).then((r) => r.data),
    enabled: canViewPlan,
  });

  const { data: planVersions = [] } = useQuery({
    queryKey: ["activities", id, "templates", "plan-versions"],
    queryFn: () => templatesApi.getPlanVersions(id!).then((r) => r.data),
    enabled: canViewPlan,
  });

  const { data: securityPlanSchema, refetch: refetchSecuritySchema } = useQuery({
    queryKey: ["activities", id, "templates", "security-schema"],
    queryFn: () => templatesApi.getSecurityPlanSchema(id!).then((r) => r.data),
    enabled: canViewSecurity,
  });

  const { data: securityPlanVersions = [] } = useQuery({
    queryKey: ["activities", id, "templates", "security-versions"],
    queryFn: () => templatesApi.getSecurityPlanVersions(id!).then((r) => r.data),
    enabled: canViewSecurity,
  });

  const canViewTemplates = (canEditSecurity || isManager) && !!activity?.status && ["待安保方案设计", "待备案申请"].includes(activity.status);
  const riskMaterial = useMaterialSchema(id!, "risk_assessment", !!canViewTemplates);
  const respMaterial = useMaterialSchema(id!, "responsibility_letter", !!canViewTemplates);

  // Inject security_staff_count from security plan into risk assessment autofill
  const riskSchema = useMemo(() => {
    const raw = riskMaterial.schema;
    if (!raw) return raw;
    const secStaffCount =
      securityPlanSchema?.draft_data?.security_staff_count
      ?? securityPlanSchema?.snapshot_data?.security_staff_count;
    if (secStaffCount == null) return raw;
    return {
      ...raw,
      autofill_data: {
        ...(raw.autofill_data || {}),
        security_count: secStaffCount,
      },
    };
  }, [riskMaterial.schema, securityPlanSchema?.draft_data?.security_staff_count, securityPlanSchema?.snapshot_data?.security_staff_count]);

  const { data: riskVersions = [] } = useQuery({
    queryKey: ["activities", id, "templates", "risk-versions"],
    queryFn: () => templatesApi.getMaterialVersions(id!, riskMaterial.materialId!).then((r) => r.data),
    enabled: !!riskMaterial.materialId,
  });

  const { data: respVersions = [] } = useQuery({
    queryKey: ["activities", id, "templates", "resp-versions"],
    queryFn: () => templatesApi.getMaterialVersions(id!, respMaterial.materialId!).then((r) => r.data),
    enabled: !!respMaterial.materialId,
  });

  const queryClient = useQueryClient();
  const [auditTarget, setAuditTarget] = useState<{ id: string; name: string } | null>(null);
  const [auditConclusion, setAuditConclusion] = useState<string>("qualified");
  const [auditOpinion, setAuditOpinion] = useState("");
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);
  const [validationModalOpen, setValidationModalOpen] = useState(false);
  const [validationContext, setValidationContext] = useState<"finalize" | "submit">("finalize");
  const [highlightFields, setHighlightFields] = useState<string[] | undefined>(undefined);
  const [planFinalizeOpen, setPlanFinalizeOpen] = useState(false);
  const [securitySubmitOpen, setSecuritySubmitOpen] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [managerSignaturePath, setManagerSignaturePath] = useState<string | null>(null);
  const [signaturePreview, setSignaturePreview] = useState<string | null>(null);
  const [signatureUploadTime, setSignatureUploadTime] = useState<string | null>(null);
  const [step1Done, setStep1Done] = useState(false);
  const [crossSyncOpen, setCrossSyncOpen] = useState(false);
  const [crossSyncData, setCrossSyncData] = useState<{
    data: Record<string, unknown>;
    resolve: (value: GenerateResponse) => void;
    reject: (err: Error) => void;
    oldCount: unknown;
    newCount: unknown;
  } | null>(null);
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

  const REJECT_FIELD_MAP: Record<string, string[]> = {
    "安保人员配置不足或不当": ["security_staff_config", "security_staff_count"],
    "动线设计不合理": ["movement_plan"],
    "设备清单不完善": ["equipment_list"],
    "应急预案不充分": ["emergency_plan"],
    "医疗救护措施不完善": ["medical_plan"],
    "消防措施不充分": ["fire_plan"],
    "人流管控方案不合理": ["crowd_control"],
  };

  useEffect(() => {
    if (securityPlan?.last_reject_reason && !isManager) {
      const reason = securityPlan.last_reject_reason;
      const fields: string[] = [];
      for (const [preset, fieldNames] of Object.entries(REJECT_FIELD_MAP)) {
        if (reason.includes(preset)) fields.push(...fieldNames);
      }
      if (fields.length > 0) setHighlightFields(fields);
    }
  }, [securityPlan?.last_reject_reason, securityPlan]);  // eslint-disable-line react-hooks/exhaustive-deps

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

      {/* UC6: SecurityManager approval confirmation banner */}
      {isManager && activity?.status === "审批通过" && (
        <div style={{ marginBottom: 16, padding: 16, border: "1px solid #1677ff", borderRadius: 8, background: "#e6f7ff" }}>
          <Typography.Title level={5} style={{ marginTop: 0 }}>批文确认</Typography.Title>
          <Typography.Paragraph>
            政府对接人已上传批文并审批通过。请确认审批结果，或驳回至安保方案设计。
          </Typography.Paragraph>
          <Space>
            <Button
              type="primary"
              onClick={async () => {
                try {
                  await workflowsApi.transition(id!, { to_status: "审批通过-待举办", comment: "安保部已确认" });
                  message.success("已确认，活动即将举办");
                  queryClient.invalidateQueries({ queryKey: ["activities", id] });
                } catch (e: any) {
                  message.error(e?.response?.data?.detail || "确认失败");
                }
              }}
            >
              确认审批通过
            </Button>
            <Button
              danger
              onClick={async () => {
                try {
                  await workflowsApi.reject(id!, { reason: "安保部驳回审批结果，需整改" });
                  message.success("已驳回至安保方案设计");
                  queryClient.invalidateQueries({ queryKey: ["activities", id] });
                  queryClient.invalidateQueries({ queryKey: ["activities", id, "security-plan"] });
                } catch (e: any) {
                  message.error(e?.response?.data?.detail || "驳回失败");
                }
              }}
            >
              驳回至安保方案设计
            </Button>
          </Space>
        </div>
      )}

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
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
                                  setValidationContext("finalize");
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
                      {securityPlan?.last_reject_reason && (
                        <div style={{ marginBottom: 16, padding: "8px 16px", background: "#fff2f0", borderRadius: 4, border: "1px solid #ffccc7" }}>
                          <Typography.Text strong style={{ color: "#ff4d4f" }}>
                            {isManager ? "已驳回" : "被驳回"}（第{securityPlan.reject_count || 1}次）
                          </Typography.Text>
                          <Typography.Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                            {securityPlan.rejected_at ? new Date(securityPlan.rejected_at).toLocaleString("zh-CN") : ""}
                          </Typography.Text>
                          <div style={{ marginTop: 4 }}>
                            <Typography.Text>{securityPlan.last_reject_reason}</Typography.Text>
                          </div>
                        </div>
                      )}
                      {isManager && securityPlan?.audit_status === "待签署" ? (
                        <>
                          <div style={{ padding: 16, border: "1px solid #1677ff", borderRadius: 8 }}>
                            <Typography.Title level={5}>安保负责人签署确认</Typography.Title>
                            {/* Read-only preview: 安保方案 + 双表 */}
                            {(() => {
                              const items: any[] = [
                                { key: "security_plan", label: "安保方案", children: <VersionSnapshot schema={securityPlanSchema} /> },
                              ];
                              if (riskSchema) items.push({ key: "risk_assessment", label: "风险评估表", children: <VersionSnapshot schema={riskSchema} /> });
                              if (respMaterial.schema) items.push({ key: "responsibility_letter", label: "责任确认书", children: <VersionSnapshot schema={respMaterial.schema} /> });
                              return <Tabs size="small" type="card" items={items} style={{ marginBottom: 16 }} />;
                            })()}
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
                                    message.success("已签署三份安保文件，请继续签署备案承诺书");
                                    setStep1Done(true);
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
                                确认签署
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
                        {step1Done && (
                          <CommitmentSign
                            activityId={id!}
                            activityName={activity?.name || ""}
                            sponsor={activity?.sponsor || ""}
                            estimatedTime={activity?.estimated_time ? dayjs(activity.estimated_time).format("YYYY年MM月DD日") : ""}
                            location={activity?.location || ""}
                            crowdScale={String(planSchema?.snapshot_data?.opening_crowd || planSchema?.snapshot_data?.regular_crowd || "")}
                            securityStaffCount={String(securityPlanSchema?.snapshot_data?.security_staff_count || "")}
                            signatureUrl={signaturePreview}
                            onSigned={() => {
                              setStep1Done(false);
                              setSignaturePreview(null);
                              setManagerSignaturePath(null);
                              setSignatureUploadTime(null);
                              queryClient.invalidateQueries({ queryKey: ["activities", id] });
                              queryClient.invalidateQueries({ queryKey: ["activities", id, "security-plan"] });
                              queryClient.invalidateQueries({ queryKey: ["activities", id, "filing", "status"] });
                              refetchSecuritySchema();
                            }}
                          />
                        )}
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
                      ) : isManager && securityPlan?.audit_status === "已签署" && activity?.status !== "待安保方案设计" ? (
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
                      ) : isManager && securityPlan?.audit_status === "已签署" && activity?.status === "待安保方案设计" ? (
                        <CommitmentSign
                          activityId={id!}
                          activityName={activity?.name || ""}
                          sponsor={activity?.sponsor || ""}
                          estimatedTime={activity?.estimated_time ? dayjs(activity.estimated_time).format("YYYY年MM月DD日") : ""}
                          location={activity?.location || ""}
                          crowdScale={String(planSchema?.snapshot_data?.opening_crowd || planSchema?.snapshot_data?.regular_crowd || "")}
                          securityStaffCount={String(securityPlanSchema?.snapshot_data?.security_staff_count || "")}
                          signatureUrl={signaturePreview}
                          onSigned={() => {
                            setSignaturePreview(null);
                            setManagerSignaturePath(null);
                            setSignatureUploadTime(null);
                            queryClient.invalidateQueries({ queryKey: ["activities", id] });
                            queryClient.invalidateQueries({ queryKey: ["activities", id, "security-plan"] });
                            queryClient.invalidateQueries({ queryKey: ["activities", id, "filing", "status"] });
                            refetchSecuritySchema();
                          }}
                        />
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
                      ) : canEditSecurity && securityPlan?.audit_status === "已签署" ? (
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
                          <Button
                            type="primary"
                            style={{ marginTop: 16 }}
                            onClick={() => setActiveTab("filing")}
                          >
                            前往备案材料打包
                          </Button>
                        </div>
                      ) : canEditSecurity ? (
                        <>
                          {activity?.status === "待安保方案设计" ? (
                            <>
                              {(() => {
                                const auditStatus = securityPlan?.audit_status;
                                const submitted = !!(auditStatus && auditStatus !== "待编制");
                                const rejectedAt = securityPlan?.rejected_at ? new Date(securityPlan.rejected_at).getTime() : 0;
                                const latestVersionAfterReject = rejectedAt
                                  ? securityPlanVersions.some((v) => v.created_at && new Date(v.created_at).getTime() > rejectedAt)
                                  : true;
                                const blockedByReject = !!rejectedAt && !latestVersionAfterReject;
                                const allThreeReady = securityPlanVersions.length > 0 && riskVersions.length > 0 && respVersions.length > 0;
                                return (
                                  <div style={{ marginTop: 8, marginBottom: 8, padding: "4px 12px", background: "#fafafa", borderRadius: 4, display: "flex", alignItems: "center", gap: 8 }}>
                                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>完成进度：</Typography.Text>
                                    <Tag color={securityPlanVersions.length > 0 ? "green" : "default"} style={{ margin: 0 }}>安保方案</Tag>
                                    <Tag color={riskVersions.length > 0 ? "green" : "default"} style={{ margin: 0 }}>风险评估表</Tag>
                                    <Tag color={respVersions.length > 0 ? "green" : "default"} style={{ margin: 0 }}>责任确认书</Tag>
                                    <span style={{ flex: 1 }} />
                                    {submitted ? (
                                      <Tag color="blue" style={{ margin: 0 }}>已提交审核</Tag>
                                    ) : blockedByReject ? (
                                      <Button size="small" disabled style={{ marginLeft: "auto" }}>被驳回，请先生成新版本</Button>
                                    ) : allThreeReady ? (
                                      <Button type="primary" size="small" style={{ marginLeft: "auto" }}
                                        onClick={() => {
                                          const allErrs: ValidationError[] = [];
                                          // business-logic validation
                                          const spRL = securityPlanSchema?.risk_level;
                                          allErrs.push(...validateSecurityPlan(securityPlanSchema?.snapshot_data, spRL));
                                          if (securityPlanSchema?.fields) allErrs.push(...validateAllFieldsFilled(securityPlanSchema?.snapshot_data, securityPlanSchema.fields, "安保方案", spRL));
                                          if (riskSchema?.fields) allErrs.push(...validateAllFieldsFilled(riskSchema?.snapshot_data, riskSchema.fields, "风险评估表", null));
                                          if (respMaterial.schema?.fields) allErrs.push(...validateAllFieldsFilled(respMaterial.schema?.snapshot_data, respMaterial.schema.fields, "责任确认书", null));
                                          if (allErrs.length > 0) { setValidationContext("submit"); setValidationErrors(allErrs); setValidationModalOpen(true); }
                                          else { setSecuritySubmitOpen(true); }
                                        }}>
                                        提交审核
                                      </Button>
                                    ) : (
                                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>请完成安保方案及双表</Typography.Text>
                                    )}
                                  </div>
                                );
                              })()}
                              <Tabs size="small" type="card" activeKey={templateTab} onChange={(key) => {
                                setTemplateTab(key as typeof templateTab);
                                if (key === "risk_assessment") riskMaterial.refetch();
                                if (key === "responsibility_letter") respMaterial.refetch();
                              }} items={[
                              {
                                key: "security_plan",
                                label: "安保方案",
                                children: (
                                  <>
                                    <div style={{ marginBottom: 16 }}>
                                      <Typography.Text strong>风险等级</Typography.Text>
                                      <Select
                                        style={{ width: 200, marginLeft: 12 }}
                                        placeholder="选择风险等级"
                                        value={securityPlanSchema.risk_level || undefined}
                                        disabled={!!(securityPlan?.audit_status && securityPlan.audit_status !== "待编制")}
                                        options={[
                                          { label: "高风险", value: "高风险" },
                                          { label: "中低风险", value: "中低风险" },
                                          { label: "低风险", value: "低风险" },
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
                                      highlightFields={highlightFields}
                                      onSaveDraft={async (data) => {
                                        await templatesApi.saveSecurityPlanDraft(id!, data);
                                      }}
                                      onSubmit={async (data) => {
                                        const oldCount = securityPlanSchema?.snapshot_data?.security_staff_count;
                                        const newCount = data.security_staff_count;
                                        // Check if security_staff_count changed and risk assessment has a version
                                        if (oldCount != null && String(newCount) !== String(oldCount)
                                            && riskMaterial.schema?.current_version != null) {
                                          return new Promise<GenerateResponse>((resolve, reject) => {
                                            setCrossSyncData({ data, resolve, reject, oldCount, newCount });
                                            setCrossSyncOpen(true);
                                          });
                                        }
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
                                        queryClient.invalidateQueries({ queryKey: ["activities", id, "templates", "security-versions"] });
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
                                  </>
                                ),
                              },
                              {
                                key: "risk_assessment",
                                label: "风险评估表",
                                children: riskMaterial.isLoading ? (
                                  <Spin />
                                ) : riskSchema ? (
                                  <>
                                    <TemplateForm
                                      activityId={id!}
                                      schema={riskSchema}
                                      disabled={!!(securityPlan?.audit_status && securityPlan.audit_status !== "待编制")}
                                      highlightFields={highlightFields}
                                      onSaveDraft={async (data) => {
                                        await templatesApi.saveMaterialDraft(id!, riskMaterial.materialId!, data);
                                      }}
                                      onSubmit={async (data) => {
                                        const res = await templatesApi.generateMaterial(id!, riskMaterial.materialId!, data);
                                        const result = res.data;
                                        queryClient.setQueryData<VersionItem[]>(
                                          ["activities", id, "templates", "risk-versions"],
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
                                        riskMaterial.refetch();
                                        queryClient.invalidateQueries({ queryKey: ["activities", id, "templates", "risk-versions"] });
                                        return result;
                                      }}
                                      onValidate={(data) => validateRiskAssessment(data)}
                                    />
                                    <VersionTimeline
                                      versions={riskVersions}
                                      onViewDetail={(v) =>
                                        templatesApi.getMaterialVersionDetail(id!, riskMaterial.materialId!, v).then((r) => r.data)
                                      }
                                      onDiff={(v1, v2) =>
                                        templatesApi.getMaterialVersionDiff(id!, riskMaterial.materialId!, v1, v2).then((r) => r.data)
                                      }
                                    />
                                  </>
                                ) : null,
                              },
                              {
                                key: "responsibility_letter",
                                label: "责任确认书",
                                children: respMaterial.isLoading ? (
                                  <Spin />
                                ) : respMaterial.schema ? (
                                  <>
                                    <TemplateForm
                                      activityId={id!}
                                      schema={respMaterial.schema}
                                      disabled={!!(securityPlan?.audit_status && securityPlan.audit_status !== "待编制")}
                                      highlightFields={highlightFields}
                                      onSaveDraft={async (data) => {
                                        await templatesApi.saveMaterialDraft(id!, respMaterial.materialId!, data);
                                      }}
                                      onSubmit={async (data) => {
                                        const res = await templatesApi.generateMaterial(id!, respMaterial.materialId!, data);
                                        const result = res.data;
                                        queryClient.setQueryData<VersionItem[]>(
                                          ["activities", id, "templates", "resp-versions"],
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
                                        respMaterial.refetch();
                                        queryClient.invalidateQueries({ queryKey: ["activities", id, "templates", "resp-versions"] });
                                        return result;
                                      }}
                                      onValidate={(data) => validateResponsibilityLetter(data)}
                                    />
                                    <VersionTimeline
                                      versions={respVersions}
                                      onViewDetail={(v) =>
                                        templatesApi.getMaterialVersionDetail(id!, respMaterial.materialId!, v).then((r) => r.data)
                                      }
                                      onDiff={(v1, v2) =>
                                        templatesApi.getMaterialVersionDiff(id!, respMaterial.materialId!, v1, v2).then((r) => r.data)
                                      }
                                    />
                                  </>
                                ) : null,
                              },
                            ]} />
                            </>
                          ) : (
                            <>
                              <div style={{ marginBottom: 16 }}>
                                <Typography.Text strong>风险等级</Typography.Text>
                                <Select
                                  style={{ width: 200, marginLeft: 12 }}
                                  placeholder="选择风险等级"
                                  value={securityPlanSchema.risk_level || undefined}
                                  disabled
                                  options={[
                                    { label: "高风险", value: "高风险" },
                                    { label: "中低风险", value: "中低风险" },
                                    { label: "低风险", value: "低风险" },
                                  ]}
                                />
                              </div>
                              <TemplateForm
                                activityId={id!}
                                schema={securityPlanSchema}
                                disabled
                                onSaveDraft={async () => {}}
                                onSubmit={async () => ({ id: "", template_type: "", version_number: 0, minio_path: null, pdf_ready: false, created_at: "" } as GenerateResponse)}
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
                            </>
                          )}
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

                      {/* GovLiaison review panel */}
                      {isGovLiaison && activity?.status === "备案材料已交接" && (() => {
                        const auditedCount = materials.filter(m => m.audit_round > 0).length;
                        const allAudited = materials.length > 0 && auditedCount === materials.length;
                        const targetStatus = approvalAction === "approve" ? "审批通过" : approvalAction === "revise" ? "待补充备案材料" : "不通过/已终止";
                        return (
                          <div style={{ marginTop: 24, padding: 16, border: "1px solid #1677ff", borderRadius: 8 }}>
                            <Typography.Title level={5}>政府对接 — 审批决策</Typography.Title>
                            <div style={{ marginBottom: 16 }}>
                              <Typography.Text strong>材料审查状态：</Typography.Text>
                              {allAudited ? (
                                <Tag color="green">全部材料已审查（{materials.length}项）</Tag>
                              ) : (
                                <Tag color="orange">尚有 {materials.length - auditedCount} 项材料待审查</Tag>
                              )}
                            </div>
                            <div style={{ marginBottom: 16 }}>
                              <Typography.Text strong>上传政府批文（可选）：</Typography.Text>
                              <Upload
                                accept=".pdf,.jpg,.png,.doc,.docx"
                                maxCount={1}
                                showUploadList={false}
                                customRequest={async ({ file, onSuccess, onError }) => {
                                  try {
                                    const res = await documentsApi.upload(id!, file as File, ["approval"]);
                                    setApprovalDocPath(res.data.minio_path);
                                    onSuccess?.(res.data);
                                    message.success("批文已上传");
                                  } catch {
                                    onError?.(new Error("上传失败"));
                                    message.error("批文上传失败");
                                  }
                                }}
                              >
                                <Button icon={<UploadOutlined />}>选择批文文件</Button>
                              </Upload>
                              {approvalDocPath && <Tag color="blue" style={{ marginTop: 8 }}>已上传</Tag>}
                            </div>
                            <Space>
                              <Button type="primary" disabled={!allAudited}
                                onClick={() => { setApprovalAction("approve"); setApprovalComment(""); setApprovalModalOpen(true); }}>
                                审批通过
                              </Button>
                              <Button disabled={!allAudited}
                                onClick={() => { setApprovalAction("revise"); setApprovalComment(""); setApprovalModalOpen(true); }}>
                                要求补件
                              </Button>
                              <Button danger
                                onClick={() => { setApprovalAction("reject"); setApprovalComment(""); setApprovalModalOpen(true); }}>
                                驳回—不通过
                              </Button>
                            </Space>
                            <Modal
                              title={approvalAction === "approve" ? "确认审批通过" : approvalAction === "revise" ? "要求补充材料" : "确认驳回"}
                              open={approvalModalOpen}
                              onOk={async () => {
                                try {
                                  await filingsApi.createApproval(id!, {
                                    approval_status: targetStatus,
                                    attachment_url: approvalDocPath || undefined,
                                    rectification_opinion: approvalComment || undefined,
                                  });
                                  message.success("审批结果已提交");
                                  queryClient.invalidateQueries({ queryKey: ["activities", id] });
                                  queryClient.invalidateQueries({ queryKey: ["activities", id, "filing", "status"] });
                                  setApprovalModalOpen(false);
                                  setApprovalDocPath(null);
                                } catch (e: any) {
                                  message.error(e?.response?.data?.detail || "操作失败");
                                }
                              }}
                              onCancel={() => setApprovalModalOpen(false)}
                              okText="确认"
                              cancelText="取消"
                            >
                              {approvalAction === "approve" && "确认该活动审批通过？活动将进入「审批通过」状态。"}
                              {approvalAction === "revise" && (
                                <>
                                  <Typography.Paragraph type="secondary">请输入补件说明，告知需要补充哪些材料：</Typography.Paragraph>
                                  <Input.TextArea rows={3} value={approvalComment}
                                    onChange={(e) => setApprovalComment(e.target.value)}
                                    placeholder="说明需要补充的材料..." />
                                </>
                              )}
                              {approvalAction === "reject" && (
                                <>
                                  <Typography.Paragraph type="secondary">确认驳回该活动？活动将进入「不通过/已终止」状态。请填写驳回原因：</Typography.Paragraph>
                                  <Input.TextArea rows={3} value={approvalComment}
                                    onChange={(e) => setApprovalComment(e.target.value)}
                                    placeholder="驳回原因..." />
                                </>
                              )}
                            </Modal>
                          </div>
                        );
                      })()}
                    </div>
                  ),
                },
              ]
            : []),
        ]}
      />
      <Modal
        title="同步更新风险评估表"
        open={crossSyncOpen}
        onOk={async () => {
          if (!crossSyncData) return;
          setCrossSyncOpen(false);
          const res = await templatesApi.generateSecurityPlan(id!, crossSyncData.data as Record<string, unknown>);
          const result = res.data;
          queryClient.setQueryData<VersionItem[]>(
            ["activities", id, "templates", "security-versions"],
            (old = []) => [{ id: result.id, version_number: result.version_number, generated_by: "", created_at: result.created_at, is_current: true, pdf_ready: result.pdf_ready }, ...old.map((v) => ({ ...v, is_current: false }))],
          );
          refetchSecuritySchema();
          queryClient.invalidateQueries({ queryKey: ["activities", id, "templates", "security-versions"] });
          riskMaterial.refetch();
          respMaterial.refetch();
          message.success("安保方案已生成，风险评估表已同步更新");
          crossSyncData.resolve(result);
          setCrossSyncData(null);
        }}
        onCancel={() => {
          crossSyncData?.reject(new Error("用户取消"));
          setCrossSyncData(null);
          setCrossSyncOpen(false);
        }}
        okText="确认同步"
        cancelText="取消"
      >
        <Typography.Paragraph>
          安保人员数量从 <Typography.Text strong>{String(crossSyncData?.oldCount ?? "")}</Typography.Text> 变更为 <Typography.Text strong>{String(crossSyncData?.newCount ?? "")}</Typography.Text>。
        </Typography.Paragraph>
        <Typography.Paragraph type="secondary">
          此变更将同步更新风险评估表和备案承诺书的对应字段，以上文件将自动生成新版本。是否确认？
        </Typography.Paragraph>
      </Modal>
      <Modal
        title={validationContext === "finalize" ? "以下字段需要完善后才能最终确定" : "以下字段需要完善后才能提交审核"}
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
            <li key={i} style={{ marginBottom: 6, cursor: e.field ? "pointer" : "default", color: e.field ? "#1677ff" : "inherit" }}
              onClick={() => {
                if (!e.field) return;
                setHighlightFields([e.field]);
                setValidationModalOpen(false);
                // switch to correct sub-tab before scrolling
                if (securityPlanSchema?.fields?.some((f: any) => f.name === e.field)) setTemplateTab("security_plan");
                else if (riskSchema?.fields?.some((f: any) => f.name === e.field)) setTemplateTab("risk_assessment");
                else if (respMaterial.schema?.fields?.some((f: any) => f.name === e.field)) setTemplateTab("responsibility_letter");
                setTimeout(() => {
                  document.getElementById(e.field)?.scrollIntoView({ behavior: "smooth", block: "center" });
                }, 200);
              }}>
              <strong>{e.label}</strong>：{e.reason}
            </li>
          ))}
        </ul>
      </Modal>
    </div>
  );
}
