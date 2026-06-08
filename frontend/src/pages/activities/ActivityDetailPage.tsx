import { useState, useEffect, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Descriptions, Tabs, Button, Tag, Spin, Typography, Space, Modal, Input, message, Table, Select, Upload, Checkbox, Empty, Alert, Timeline } from "antd";
import { ArrowLeftOutlined, UploadOutlined, EyeOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useActivity, useActivityHistory, useActivityDocuments } from "@/hooks/useActivityQueries";
import StatusTimeline from "@/components/activities/StatusTimeline";
import DocumentUpload from "@/components/documents/DocumentUpload";
import DocumentList from "@/components/documents/DocumentList";
import WorkflowActions from "@/components/workflows/WorkflowActions";
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
  const isOfficerFilingPhase = activity?.status === "待备案申请" || activity?.status === "待补充备案材料";
  const isGovLiaisonFilingPhase = activity?.status === "备案材料已交接";

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
  useEffect(() => {
    if (materials.length > 0) console.table(materials.map((m: any) => ({
      name: m.name, material_type: m.material_type, sign_status: m.sign_status,
      pdf_path: (m as any).pdf_path?.substring(0, 40) || "✗", version: m.current_version,
    })));
  }, [materials]);

  const { data: auditHistory = [] } = useQuery({
    queryKey: ["activities", id, "materials", "audit-history"],
    queryFn: () => materialsApi.getAuditHistory(id!).then((r) => r.data),
    enabled: showFiling,
  });

  const { data: approvalRecord } = useQuery({
    queryKey: ["activities", id, "filing", "approval"],
    queryFn: () => filingsApi.getApproval(id!).then(r => r.data),
    enabled: showFiling && activity?.status === "待补充备案材料",
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

  const canViewTemplates = (canEditSecurity || isManager) && !!activity?.status && ["待安保方案设计", "待备案申请", "待补充备案材料"].includes(activity.status);
  const riskMaterial = useMaterialSchema(id!, "risk_assessment", !!canViewTemplates);
  const respMaterial = useMaterialSchema(id!, "responsibility_letter", !!canViewTemplates);

  // Filing commitment location: risk assessment's specific address, fallback to activity.location
  const filingLocation = useMemo(() => {
    const raLoc = (riskMaterial.schema as any)?.snapshot_data?.activity_location
      || (riskMaterial.schema as any)?.draft_data?.activity_location
      || (riskMaterial.schema as any)?.autofill_data?.activity_location;
    return raLoc || activity?.location || "";
  }, [riskMaterial.schema, activity?.location]);

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
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [batchUnqualOpen, setBatchUnqualOpen] = useState(false);
  const [batchUnqualReason, setBatchUnqualReason] = useState("");
  const [showAllAudit, setShowAllAudit] = useState(false);
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

  const ALL_REJECT_PRESETS = [
    "安保人员配置不足或不当",
    "动线设计不合理",
    "设备清单不完善",
    "应急预案不充分",
    "医疗救护措施不完善",
    "消防措施不充分",
    "人流管控方案不合理",
    "其他（需补充说明）",
  ];

  const REJECT_PRESETS = useMemo(() => {
    const rl = securityPlan?.risk_level || securityPlanSchema?.risk_level;
    if (rl === "低风险") return ALL_REJECT_PRESETS.filter(p =>
      !["医疗救护措施不完善", "消防措施不充分", "人流管控方案不合理"].includes(p));
    if (rl === "中低风险") return ALL_REJECT_PRESETS.filter(p =>
      !["医疗救护措施不完善", "人流管控方案不合理"].includes(p));
    return ALL_REJECT_PRESETS;
  }, [securityPlan?.risk_level, securityPlanSchema?.risk_level]);

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

  const canSign = permissions.includes("sign_document");
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

      {!isGovLiaison && (
        <WorkflowActions
          activityId={id!}
          currentStatus={activity.status}
        />
      )}

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
                      securityPlan.risk_level === "高风险" ? "red"
                      : securityPlan.risk_level === "低风险" ? "green"
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
                        <>
                          <VersionSnapshot schema={planSchema} />
                          {permissions.includes("submit_plan") && (
                            <VersionTimeline
                              versions={planVersions}
                              onViewDetail={(v) => templatesApi.getPlanVersionDetail(id!, v).then((r) => r.data)}
                              onDiff={(v1, v2) => templatesApi.getPlanVersionDiff(id!, v1, v2).then((r) => r.data)}
                              onPreview={async (v) => { const r = await templatesApi.getPlanVersionPreview(id!, v); return r.data.url; }}
                            />
                          )}
                        </>
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
                      {securityPlan?.risk_level && (
                        <div style={{ marginBottom: 16 }}>
                          <Typography.Text strong>风险等级：</Typography.Text>
                          <Tag color={securityPlan.risk_level === "高风险" ? "red" : securityPlan.risk_level === "低风险" ? "green" : "orange"}>
                            {securityPlan.risk_level}
                          </Tag>
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
                                disabled={!managerSignaturePath && !(securityPlan as any)?.manager_id}
                                onClick={async () => {
                                  setFinalizing(true);
                                  try {
                                    await templatesApi.signSecurityPlan(id!, managerSignaturePath || "");
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
                              {!managerSignaturePath && (securityPlan as any)?.manager_id && (
                                <Typography.Text type="secondary" style={{ fontSize: 12, display: "block", marginTop: 4 }}>
                                  将复用已上传的签名
                                </Typography.Text>
                              )}
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
                          <>
                            <CommitmentSign
                              activityId={id!}
                              activityName={activity?.name || ""}
                              sponsor={activity?.sponsor || ""}
                              estimatedTime={activity?.estimated_time ? dayjs(activity.estimated_time).format("YYYY年MM月DD日") : ""}
                              location={filingLocation}
                              crowdScale={String(planSchema?.snapshot_data?.opening_crowd || planSchema?.snapshot_data?.regular_crowd || "")}
                              securityStaffCount={String(securityPlanSchema?.snapshot_data?.security_staff_count || "")}
                              signatureUrl={signaturePreview} signaturePath={managerSignaturePath || (securityPlanSchema?.snapshot_data as any)?.manager_signature || null}
                              onSigned={() => {
                                setStep1Done(false);
                                setSignaturePreview(null);
                                setManagerSignaturePath(null);
                                setSignatureUploadTime(null);
                                queryClient.invalidateQueries({ queryKey: ["activities", id] });
                                queryClient.invalidateQueries({ queryKey: ["activities", id, "security-plan"] });
                                queryClient.invalidateQueries({ queryKey: ["activities", id, "filing", "status"] });
                                queryClient.invalidateQueries({ queryKey: ["activities", id, "materials"] });
                                refetchSecuritySchema();
                              }}
                            />
                            <Tabs size="small" type="card" style={{ marginTop: 16 }} items={[
                              { key: "sec", label: "安保方案", children: <VersionSnapshot schema={securityPlanSchema} /> },
                              riskSchema ? { key: "risk", label: "风险评估表", children: <VersionSnapshot schema={riskSchema} /> } : null,
                              respMaterial.schema ? { key: "resp", label: "责任确认书", children: <VersionSnapshot schema={respMaterial.schema} /> } : null,
                            ].filter(Boolean) as any} />
                          </>
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
                        <>
                          <CommitmentSign
                            activityId={id!}
                            activityName={activity?.name || ""}
                            sponsor={activity?.sponsor || ""}
                            estimatedTime={activity?.estimated_time ? dayjs(activity.estimated_time).format("YYYY年MM月DD日") : ""}
                            location={filingLocation}
                            crowdScale={String(planSchema?.snapshot_data?.opening_crowd || planSchema?.snapshot_data?.regular_crowd || "")}
                            securityStaffCount={String(securityPlanSchema?.snapshot_data?.security_staff_count || "")}
                            signatureUrl={signaturePreview} signaturePath={managerSignaturePath || (securityPlanSchema?.snapshot_data as any)?.manager_signature || null}
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
                          <Tabs size="small" type="card" style={{ marginTop: 16 }} items={[
                            { key: "sec", label: "安保方案", children: <VersionSnapshot schema={securityPlanSchema} /> },
                            riskSchema ? { key: "risk", label: "风险评估表", children: <VersionSnapshot schema={riskSchema} /> } : null,
                            respMaterial.schema ? { key: "resp", label: "责任确认书", children: <VersionSnapshot schema={respMaterial.schema} /> } : null,
                          ].filter(Boolean) as any} />
                        </>
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
                      ) : (() => { console.log("[sec-tab] canEditSecurity:", canEditSecurity, "audit_status:", securityPlan?.audit_status, "activity.status:", activity?.status); return null; })()}
                      {canEditSecurity && securityPlan?.audit_status === "已签署" ? (
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
                          {(activity?.status === "待安保方案设计" || activity?.status === "待补充备案材料") ? (
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
                                        onClick={async () => {
                                          const allErrs: ValidationError[] = [];
                                          const spRL = securityPlanSchema?.risk_level;
                                          const currentSnap = securityPlanSchema?.snapshot_data || {};
                                          allErrs.push(...validateSecurityPlan(currentSnap, spRL));
                                          if (securityPlanSchema?.fields) allErrs.push(...validateAllFieldsFilled(currentSnap, securityPlanSchema.fields, "安保方案", spRL));
                                          if (riskSchema?.fields) allErrs.push(...validateAllFieldsFilled(riskSchema?.snapshot_data, riskSchema.fields, "风险评估表", null));
                                          if (respMaterial.schema?.fields) allErrs.push(...validateAllFieldsFilled(respMaterial.schema?.snapshot_data, respMaterial.schema.fields, "责任确认书", null));

                                          // If rejected, ensure highlighted fields actually changed vs the rejected version
                                          if (highlightFields && highlightFields.length > 0 && securityPlan?.rejected_at) {
                                            const rejectedAt = new Date(securityPlan.rejected_at).getTime();
                                            const rejectedVer = [...securityPlanVersions]
                                              .sort((a, b) => new Date(b.created_at || "").getTime() - new Date(a.created_at || "").getTime())
                                              .find(v => v.created_at && new Date(v.created_at).getTime() <= rejectedAt);
                                            if (rejectedVer) {
                                              try {
                                                const detail = await templatesApi.getSecurityPlanVersionDetail(id!, rejectedVer.version_number);
                                                const rejectedSnap = detail.data.data_snapshot || {};
                                                for (const f of highlightFields) {
                                                  if (currentSnap[f] != null && rejectedSnap[f] != null
                                                      && String(currentSnap[f]) === String(rejectedSnap[f])) {
                                                    const label = securityPlanSchema?.fields?.find((sf: any) => sf.name === f)?.ui_label || f;
                                                    allErrs.push({ field: f, label, reason: "与被驳回版本一致，请修改后重新生成" });
                                                  }
                                                }
                                              } catch { /* version detail fetch may fail; skip check */ }
                                            }
                                          }

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
                      {activity?.status === "待补充备案材料" && (
                        <Tag color="orange" style={{ marginLeft: 8 }}>需补充</Tag>
                      )}
                      {filingStatus?.handed_over && activity?.status !== "待补充备案材料" && (
                        <Tag color="green" style={{ marginLeft: 8 }}>已交接</Tag>
                      )}
                      {filingStatus?.packed && !filingStatus?.handed_over && (
                        <Tag color="blue" style={{ marginLeft: 8 }}>已打包</Tag>
                      )}
                    </span>
                  ),
                  children: (
                    <div>
                      {/* Phase banner */}
                      {isOfficerFilingPhase && (
                        <Alert type="info" showIcon title="备案材料打包" description="请确认所有材料已签署，然后打包备案材料并确认纸质交接。" style={{ marginBottom: 16 }} />
                      )}
                      {isGovLiaisonFilingPhase && isGovLiaison && (
                        <Alert type="info" showIcon title="政府审查" description="请逐项审查备案材料，全部审查完毕后做出审批决定。" style={{ marginBottom: 16 }} />
                      )}
                      {/* GovLiaison review panel — right below alert */}
                      {isGovLiaison && (activity?.status === "备案材料已交接" || activity?.status === "待补充备案材料") && (() => {
                        const isActive = activity?.status === "备案材料已交接";
                        const auditedCount = materials.filter(m => m.audit_round > 0).length;
                        const allAudited = materials.length > 0 && auditedCount === materials.length;
                        const allQualified = allAudited && materials.every(m => m.is_qualified);
                        const targetStatus = approvalAction === "approve" ? "审批通过" : approvalAction === "revise" ? "待补充备案材料" : "不通过/已终止";
                        return (
                          <div style={{ marginBottom: 16, padding: 16, border: "1px solid #1677ff", borderRadius: 8 }}>
                            <Typography.Title level={5}>政府对接 — 审批决策</Typography.Title>
                            <div style={{ marginBottom: 16 }}>
                              <Typography.Text strong>材料审查状态：</Typography.Text>
                              {allQualified ? (
                                <Tag color="green">全部材料合格 — 可审批通过</Tag>
                              ) : allAudited ? (
                                <Tag color="orange">有不合格材料 — 可要求补件或驳回</Tag>
                              ) : (
                                <Tag color="default">尚有 {materials.length - auditedCount} 项材料待审查</Tag>
                              )}
                            </div>
                            <div style={{ marginBottom: 16 }}>
                              <Typography.Text strong>上传政府批文（必传）：</Typography.Text>
                              <Upload accept=".pdf,.jpg,.jpeg,.png" maxCount={1} showUploadList={false} disabled={!isActive}
                                customRequest={async ({ file, onSuccess, onError }) => {
                                  try {
                                    const res = await documentsApi.upload(id!, file as File, ["approval"]);
                                    setApprovalDocPath(res.data.minio_path);
                                    onSuccess?.(res.data);
                                    message.success("批文已上传");
                                  } catch { onError?.(new Error("上传失败")); message.error("批文上传失败"); }
                                }}>
                                <Button icon={<UploadOutlined />}>选择批文文件</Button>
                              </Upload>
                              {approvalDocPath && <Tag color="blue" style={{ marginTop: 8 }}>已上传</Tag>}
                            </div>
                            {/* materials audit table inside review card */}
                            {materials.length > 0 && (
                              <Table
                                dataSource={materials} rowKey="id" size="small" style={{ marginBottom: 12 }} pagination={false}
                                locale={{ emptyText: <Empty description="暂无备案材料" /> }}
                                rowSelection={isActive ? { selectedRowKeys, onChange: (keys) => setSelectedRowKeys(keys as string[]) } : undefined}
                                columns={[
                                  { title: "材料名称", dataIndex: "name", key: "name" },
                                  { title: "签署状态", key: "sign", width: 80, render: (_: unknown, m: any) => (
                                    <Tag color={m.sign_status === "signed" ? "green" : "default"}>{m.sign_status === "signed" ? "已签" : "未签"}</Tag>
                                  )},
                                  { title: "合规", key: "qual", width: 80, render: (_: unknown, m: any) => (
                                    m.audit_round > 0 ? <Tag color={m.is_qualified ? "green" : "red"}>{m.is_qualified ? "合格" : "不合格"}</Tag> : <Tag color="default">待审查</Tag>
                                  )},
                                  { title: "审查轮次", key: "audit", width: 70, render: (_: unknown, m: any) => (
                                    m.audit_round > 0 ? <Tag>{m.audit_round} 轮</Tag> : <Typography.Text type="secondary">—</Typography.Text>
                                  )},
                                  { title: "操作", key: "actions", width: 120, render: (_: unknown, m: any) => (
                                    <Space size={4}>
                                      <Button size="small" type="link" icon={<EyeOutlined />}
                                        onClick={async () => {
                                          try {
                                            const mAny = m as any;
                                            const path = mAny.pdf_path || mAny.minio_path;
                                            if (path) { const r = await documentsApi.getPresignedByPath(path); if (r.data.url) { setPreviewUrl(r.data.url); return; } }
                                            message.warning("暂无预览文件");
                                          } catch { message.error("预览失败"); }
                                        }}>预览</Button>
                                    </Space>
                                  )},
                                ]}
                              />
                            )}
                            {/* action bar: batch audit left, approval right — only when active */}
                            {isActive && (
                              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                <Space>
                                  {selectedRowKeys.length > 0 && (
                                    <>
                                      <Typography.Text>已选 {selectedRowKeys.length} 项：</Typography.Text>
                                      <Button size="small" type="primary"
                                        onClick={async () => { for (const mid of selectedRowKeys) { await materialsApi.audit(id!, mid, "qualified"); } message.success(`已批量标记 ${selectedRowKeys.length} 项为合格`); setSelectedRowKeys([]); refetchMaterials(); }}>批量合格</Button>
                                      <Button size="small" danger
                                        onClick={() => { setBatchUnqualReason(""); setBatchUnqualOpen(true); }}>批量不合格</Button>
                                    </>
                                  )}
                                </Space>
                                <Space>
                                  <Button type="primary" disabled={!allQualified || !approvalDocPath}
                                    onClick={() => { setApprovalAction("approve"); setApprovalComment(""); setApprovalModalOpen(true); }}>审批通过</Button>
                                  <Button disabled={!allAudited || allQualified}
                                    onClick={() => {
                                      setApprovalAction("revise");
                                      const unqual = materials.filter(m => m.audit_round > 0 && !m.is_qualified).map(m => m.name);
                                      setApprovalComment(unqual.length > 0 ? `以下材料不合格需整改：${unqual.join("、")}` : "");
                                      setApprovalModalOpen(true);
                                    }}>要求补件</Button>
                                  <Button danger
                                    onClick={() => { setApprovalAction("reject"); setApprovalComment(""); setApprovalModalOpen(true); }}>驳回—不通过</Button>
                                </Space>
                              </div>
                            )}
                            {!isActive && (
                              <div style={{ padding: "8px 12px", background: "#fffbe6", borderRadius: 4, border: "1px solid #ffe58f" }}>
                                <Typography.Text type="warning">已要求补件，等待安保部重新提交备案材料</Typography.Text>
                              </div>
                            )}
                            <Modal
                              title={approvalAction === "approve" ? "确认审批通过" : approvalAction === "revise" ? "要求补充材料" : "确认驳回"}
                              open={approvalModalOpen}
                              onOk={async () => {
                                try {
                                  await filingsApi.createApproval(id!, { approval_status: targetStatus, attachment_url: approvalDocPath || undefined, rectification_opinion: approvalComment || undefined });
                                  message.success("审批结果已提交");
                                  queryClient.invalidateQueries({ queryKey: ["activities", id] });
                                  queryClient.invalidateQueries({ queryKey: ["activities", id, "filing", "status"] });
                                  queryClient.invalidateQueries({ queryKey: ["activities", id, "security-plan"] });
                                  setApprovalModalOpen(false); setApprovalDocPath(null);
                                } catch (e: any) { message.error(e?.response?.data?.detail || "操作失败"); }
                              }}
                              onCancel={() => setApprovalModalOpen(false)} okText="确认" cancelText="取消">
                              {approvalAction === "approve" && "确认该活动审批通过？活动将进入「审批通过」状态。"}
                              {approvalAction === "revise" && <><Typography.Paragraph type="secondary">请输入补件说明：</Typography.Paragraph>
                                <Input.TextArea rows={3} value={approvalComment} onChange={(e) => setApprovalComment(e.target.value)} placeholder="说明需要补充的材料..." /></>}
                              {approvalAction === "reject" && <><Typography.Paragraph type="secondary">确认驳回该活动？活动将进入「不通过/已终止」状态。请填写驳回原因：</Typography.Paragraph>
                                <Input.TextArea rows={3} value={approvalComment} onChange={(e) => setApprovalComment(e.target.value)} placeholder="驳回原因..." /></>}
                            </Modal>
                          </div>
                        );
                      })()}
                      {/* materials table for non-GovLiaison roles */}
                      {materials.length > 0 && !(isGovLiaison && (activity?.status === "备案材料已交接" || activity?.status === "待补充备案材料")) && (
                        <>
                          {activity?.status === "待补充备案材料" && (
                            <div style={{ marginTop: 16, marginBottom: 8 }}>
                              <Alert type="warning" showIcon title="需补充材料"
                                description={
                                  <div>
                                    {approvalRecord?.rectification_opinion && (
                                      <Typography.Paragraph style={{ marginBottom: 4 }}>
                                        <Typography.Text strong>补件说明：</Typography.Text>
                                        {approvalRecord.rectification_opinion}
                                      </Typography.Paragraph>
                                    )}
                                    <Typography.Text strong>需修改的材料：</Typography.Text>
                                    {materials.filter(m => m.audit_round > 0 && !m.is_qualified).map(m => (
                                      <div key={m.id} style={{ marginTop: 4 }}>
                                        <Tag color="red" style={{ cursor: "pointer" }}
                                          onClick={() => { setActiveTab("security-plan"); (document.activeElement as HTMLElement)?.blur(); }}>{m.name}</Tag>
                                        {m.opinion && (
                                          <Typography.Text type="secondary" style={{ fontSize: 12, marginLeft: 4 }}>
                                            — {m.opinion}
                                          </Typography.Text>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                } />
                            </div>
                          )}
                          <Table
                            dataSource={materials}
                            rowKey="id"
                            size="small"
                            style={{ marginTop: 16 }}
                            pagination={false}
                            locale={{ emptyText: <Empty description="暂无备案材料" /> }}
                            columns={[
                              { title: "材料名称", dataIndex: "name", key: "name" },
                              { title: "签署状态", key: "sign", width: 100, render: (_: unknown, m: any) => (
                                <Tag color={m.sign_status === "signed" ? "green" : "default"}>
                                  {m.sign_status === "signed" ? "已签署" : "未签署"}
                                </Tag>
                              )},
                              ...(activity?.status === "待补充备案材料" ? [
                                { title: "合规", key: "qual", width: 80, render: (_: unknown, m: any) => (
                                  m.audit_round > 0
                                    ? <Tag color={m.is_qualified ? "green" : "red"}>{m.is_qualified ? "合格" : "不合格"}</Tag>
                                    : <Tag color="default">待审查</Tag>
                                )},
                                { title: "审查轮次", key: "audit", width: 80, render: (_: unknown, m: any) => (
                                  m.audit_round > 0 ? <Tag>{m.audit_round} 轮</Tag> : <Typography.Text type="secondary">—</Typography.Text>
                                )},
                              ] : []),
                              { title: "操作", key: "actions", width: 160, render: (_: unknown, m: any) => (
                                <Space size={4}>
                                  <Button size="small" type="link" icon={<EyeOutlined />}
                                    onClick={async () => {
                                      try {
                                        const mAny = m as any;
                                        const path = mAny.pdf_path || mAny.minio_path;
                                        if (path) { const r = await documentsApi.getPresignedByPath(path); if (r.data.url) { setPreviewUrl(r.data.url); return; } }
                                        message.warning("暂无预览文件");
                                      } catch { message.error("预览失败"); }
                                    }}>预览</Button>
                                  {isOfficerFilingPhase && canSign && m.sign_status !== "signed" && (
                                    <Button size="small" onClick={() => signMutation.mutate(m.id)} loading={signMutation.isPending}>签署</Button>
                                  )}
                                </Space>
                              )},
                            ]}
                          />
                        </>
                      )}

                      {/* audit history */}
                      {auditHistory.length > 0 && isGovLiaison && (() => {
                        const grouped = new Map<string, typeof auditHistory>();
                        for (const h of auditHistory) {
                          const key = h.created_at.slice(0, 16);
                          if (!grouped.has(key)) grouped.set(key, []);
                          grouped.get(key)!.push(h);
                        }
                        const all = [...grouped.values()];
                        const visible = showAllAudit ? all : all.slice(0, 3);
                        return (
                          <div style={{ marginTop: 16 }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                              <Typography.Text strong>审核记录</Typography.Text>
                              {all.length > 3 && (
                                <Button size="small" type="link" onClick={() => setShowAllAudit(!showAllAudit)}>
                                  {showAllAudit ? "收起" : `展开全部（${all.length}）`}
                                </Button>
                              )}
                            </div>
                            <Timeline
                              items={visible.map((items) => {
                                const h = items[0];
                                const hasUnqual = items.some(i => i.conclusion === "unqualified");
                                const color = h.action === "sign" ? "blue" : hasUnqual ? "red" : "green";
                                return {
                                  color,
                                  content: (
                                    <div>
                                      <Typography.Text style={{ fontSize: 12, color: "#888" }}>
                                        {new Date(h.created_at).toLocaleString("zh-CN")}
                                      </Typography.Text>
                                      <br />
                                      <Typography.Text strong>{h.user_name}</Typography.Text>
                                      <Tag color={h.action === "sign" ? "blue" : "orange"} style={{ marginLeft: 8 }}>
                                        {h.action === "sign" ? "签署" : "审查"}
                                      </Tag>
                                      <Typography.Text> — {items.length} 项</Typography.Text>
                                      <div style={{ marginTop: 4 }}>
                                        {items.map((i) => (
                                          <div key={i.id} style={{ marginBottom: 2, display: "flex", alignItems: "center", gap: 4, flexWrap: "wrap" }}>
                                            <Typography.Text style={{ fontSize: 12 }}>{i.material_name}</Typography.Text>
                                            {i.conclusion && (
                                              <Tag color={i.conclusion === "qualified" ? "green" : "red"} style={{ fontSize: 11, lineHeight: "18px" }}>
                                                {i.conclusion === "qualified" ? "合格" : "不合格"}
                                              </Tag>
                                            )}
                                            {i.opinion && (
                                              <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                                                — {i.opinion}
                                              </Typography.Text>
                                            )}
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  ),
                                };
                              })}
                            />
                          </div>
                        );
                      })()}

                      {canOperateFiling && filingStatus && (
                        <div style={{ marginTop: 16 }}>
                          {canPack && (
                            <Button type="primary" onClick={() => setFilingModal("pack")}>
                              打包备案材料
                            </Button>
                          )}
                          {!allSigned && materials.length > 0 && (
                            <Typography.Text type="secondary" style={{ display: "block", marginTop: 4 }}>
                              需全部材料签署后方可打包
                            </Typography.Text>
                          )}
                          {(filingStatus.packed || activity?.status === "待补充备案材料") && (
                            <div style={{ marginTop: 8 }}>
                              <Tag color="blue" style={{ marginRight: 8 }}>已打包</Tag>
                              {(filingStatus as any).pack_url && (
                                <Button size="small" type="link" style={{ marginRight: 8 }}
                                  onClick={async () => {
                                    const r = await documentsApi.getPresignedByPath((filingStatus as any).pack_url);
                                    if (r.data.url) window.open(r.data.url, "_blank");
                                  }}>下载打包文件</Button>
                              )}
                              <Button size="small" style={{ marginRight: 8 }}
                                onClick={() => setFilingModal("pack")}>重新打包</Button>
                              <Button onClick={() => setFilingModal("handover")}>
                                确认纸质交接
                              </Button>
                            </div>
                          )}
                          {filingStatus.handed_over && activity?.status !== "待补充备案材料" && (
                            <Tag color="green">已交接 ✓</Tag>
                          )}
                        </div>
                      )}

                      {/* batch unqual reason modal */}
                      <Modal
                        title="批量标记不合格"
                        open={batchUnqualOpen}
                        onOk={async () => {
                          for (const mid of selectedRowKeys) {
                            await materialsApi.audit(id!, mid, "unqualified", batchUnqualReason || undefined);
                          }
                          message.success(`已批量标记 ${selectedRowKeys.length} 项为不合格`);
                          setSelectedRowKeys([]); setBatchUnqualOpen(false);
                          refetchMaterials();
                        }}
                        onCancel={() => setBatchUnqualOpen(false)}
                        okText="确认"
                        cancelText="取消"
                      >
                        <Typography.Paragraph type="secondary">
                          将 {selectedRowKeys.length} 项材料标记为不合格，请输入原因：
                        </Typography.Paragraph>
                        <Input.TextArea rows={3} value={batchUnqualReason}
                          onChange={(e) => setBatchUnqualReason(e.target.value)}
                          placeholder="不合格原因..." />
                      </Modal>
                      {/* PDF preview modal */}
                      <Modal
                        title="文档预览"
                        open={!!previewUrl}
                        onCancel={() => setPreviewUrl(null)}
                        footer={null}
                        width="90%"
                        style={{ top: 20 }}
                        destroyOnHidden
                      >
                        {previewUrl && (
                          <iframe src={previewUrl}
                            style={{ width: "100%", height: "75vh", border: "none" }}
                            title="文档预览" />
                        )}
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
          queryClient.invalidateQueries({ queryKey: ["activities", id, "templates", "risk-versions"] });
          queryClient.invalidateQueries({ queryKey: ["activities", id, "templates", "resp-versions"] });
          queryClient.invalidateQueries({ queryKey: ["activities", id, "material", "risk_assessment", "schema"] });
          queryClient.invalidateQueries({ queryKey: ["activities", id, "material", "responsibility_letter", "schema"] });
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
