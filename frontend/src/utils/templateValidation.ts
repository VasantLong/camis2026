export interface ValidationError {
  field: string;
  label: string;
  reason: string;
}

export function validateActivityPlan(
  snapshot: Record<string, unknown> | null | undefined,
): ValidationError[] {
  const errors: ValidationError[] = [];
  if (!snapshot) return [{ field: "", label: "活动方案", reason: "尚未生成任何版本" }];

  if (!snapshot.activity_content)
    errors.push({ field: "activity_content", label: "活动主要内容", reason: "不能为空" });
  if (!snapshot.start_time)
    errors.push({ field: "start_time", label: "开始时间", reason: "未填写" });
  if (!snapshot.end_time)
    errors.push({ field: "end_time", label: "结束时间", reason: "未填写" });
  if (
    snapshot.start_time &&
    snapshot.end_time &&
    String(snapshot.start_time) >= String(snapshot.end_time)
  )
    errors.push({ field: "end_time", label: "结束时间", reason: "必须晚于开始时间" });
  if (!snapshot.staff_count || Number(snapshot.staff_count) <= 0)
    errors.push({ field: "staff_count", label: "工作人员数量", reason: "必须大于 0" });
  if (!snapshot.construction_plan)
    errors.push({ field: "construction_plan", label: "搭建方案", reason: "不能为空" });
  if (!snapshot.regular_crowd)
    errors.push({ field: "regular_crowd", label: "平日人数", reason: "请选择人数范围" });
  if (!snapshot.contact_phone || !/^1[3-9]\d{9}$/.test(String(snapshot.contact_phone)))
    errors.push({ field: "contact_phone", label: "负责人联系方式", reason: "须为 11 位手机号码" });

  if (snapshot.has_opening === "是") {
    if (!snapshot.opening_start)
      errors.push({ field: "opening_start", label: "开幕式开始时间", reason: "未填写" });
    if (!snapshot.opening_end)
      errors.push({ field: "opening_end", label: "开幕式结束时间", reason: "未填写" });
    if (!snapshot.opening_crowd)
      errors.push({ field: "opening_crowd", label: "主要活动日人数", reason: "请选择人数范围" });
  }

  if (snapshot.has_performers === "是") {
    if (!snapshot.performer_count || Number(snapshot.performer_count) <= 0)
      errors.push({ field: "performer_count", label: "演员数量", reason: "必须大于 0" });
    if (!snapshot.guest_count || Number(snapshot.guest_count) <= 0)
      errors.push({ field: "guest_count", label: "嘉宾数量", reason: "必须大于 0" });
  }

  return errors;
}

export function validateSecurityPlan(
  snapshot: Record<string, unknown> | null | undefined,
  riskLevel: string | null | undefined,
): ValidationError[] {
  const errors: ValidationError[] = [];
  if (!snapshot) return [{ field: "", label: "安保方案", reason: "尚未生成任何版本" }];
  if (!riskLevel) return [{ field: "risk_level", label: "风险等级", reason: "请先选择风险等级" }];

  if (!snapshot.security_staff_config)
    errors.push({ field: "security_staff_config", label: "安保人员配置", reason: "不能为空" });
  if (!snapshot.movement_plan)
    errors.push({ field: "movement_plan", label: "动线设计", reason: "不能为空" });
  if (!snapshot.equipment_list)
    errors.push({ field: "equipment_list", label: "安保设备清单", reason: "不能为空" });
  if (!snapshot.emergency_plan)
    errors.push({ field: "emergency_plan", label: "应急预案", reason: "不能为空" });
  if (!snapshot.security_staff_count || Number(snapshot.security_staff_count) <= 0)
    errors.push({ field: "security_staff_count", label: "安保人员数量", reason: "必须大于 0" });

  const rl = riskLevel || "";
  if (rl === "大型" && !snapshot.medical_plan)
    errors.push({ field: "medical_plan", label: "医疗救护措施", reason: "不能为空" });
  if (["大型", "中型", "高风险"].includes(rl) && !snapshot.fire_plan)
    errors.push({ field: "fire_plan", label: "消防措施", reason: "不能为空" });
  if (["大型", "高风险"].includes(rl) && !snapshot.crowd_control)
    errors.push({ field: "crowd_control", label: "人流管控方案", reason: "不能为空" });

  return errors;
}

export function validateRiskAssessment(
  snapshot: Record<string, unknown> | null | undefined,
): ValidationError[] {
  const errors: ValidationError[] = [];
  if (!snapshot) return [{ field: "", label: "风险评估表", reason: "尚未生成任何版本" }];

  if (!snapshot.reporting_unit)
    errors.push({ field: "reporting_unit", label: "填报单位", reason: "不能为空" });
  if (!snapshot.report_date)
    errors.push({ field: "report_date", label: "填报日期", reason: "未填写" });
  if (!snapshot.activity_content)
    errors.push({ field: "activity_content", label: "活动内容", reason: "不能为空" });
  if (!snapshot.activity_location)
    errors.push({ field: "activity_location", label: "活动地点", reason: "不能为空" });
  if (!snapshot.crowd_scale)
    errors.push({ field: "crowd_scale", label: "预计参与人数规模", reason: "请选择" });
  if (!snapshot.risk_factors || (Array.isArray(snapshot.risk_factors) && snapshot.risk_factors.length < 4))
    errors.push({ field: "risk_factors", label: "主要风险因素", reason: "至少填写 4 条" });
  if (!snapshot.mitigation_measures || (Array.isArray(snapshot.mitigation_measures) && snapshot.mitigation_measures.length < 4))
    errors.push({ field: "mitigation_measures", label: "防范化解措施", reason: "至少填写 4 条" });
  if (!snapshot.contact_person)
    errors.push({ field: "contact_person", label: "联系人", reason: "不能为空" });
  if (!snapshot.contact_phone || !/^1[3-9]\d{9}$/.test(String(snapshot.contact_phone)))
    errors.push({ field: "contact_phone", label: "联系电话", reason: "须为 11 位手机号码" });
  if (!snapshot.assessor_signature)
    errors.push({ field: "assessor_signature", label: "评估主体负责人签字", reason: "请上传签名图片" });

  if (snapshot.has_media === "是") {
    if (!snapshot.media_channel)
      errors.push({ field: "media_channel", label: "媒体采录方式", reason: "请选择" });
  }

  return errors;
}

export function validateResponsibilityLetter(
  snapshot: Record<string, unknown> | null | undefined,
): ValidationError[] {
  const errors: ValidationError[] = [];
  if (!snapshot) return [{ field: "", label: "责任确认书", reason: "尚未生成任何版本" }];

  if (!snapshot.sponsor_unit)
    errors.push({ field: "sponsor_unit", label: "活动主办单位", reason: "不能为空" });
  if (!snapshot.security_leader_name)
    errors.push({ field: "security_leader_name", label: "活动安全负责人", reason: "不能为空" });
  if (!snapshot.security_leader_signature)
    errors.push({ field: "security_leader_signature", label: "安全负责人签字", reason: "请上传签名图片" });
  if (!snapshot.confirm_date)
    errors.push({ field: "confirm_date", label: "确认日期", reason: "未填写" });
  if (!snapshot.confirm_location)
    errors.push({ field: "confirm_location", label: "确认地点", reason: "不能为空" });

  return errors;
}

/** Validate every visible field has a non-empty value (submit gate). */
export function validateAllFieldsFilled(
  snapshot: Record<string, unknown> | null | undefined,
  fields: { name: string; ui_label: string; ui_type: string; condition?: string }[],
): ValidationError[] {
  const errors: ValidationError[] = [];
  if (!snapshot) return errors;
  for (const f of fields) {
    if (f.ui_type === "autofill" || f.ui_type === "declarations") continue;
    // skip hidden conditional fields
    if (f.condition && !evalCondition(f.condition, snapshot)) continue;
    const v = snapshot[f.name];
    if (v === undefined || v === null || v === "") {
      errors.push({ field: f.name, label: f.ui_label, reason: "请填写" });
    }
  }
  return errors;
}

function evalCondition(cond: string, snapshot: Record<string, unknown>): boolean {
  const parts = cond.split(/\s*(==|!=)\s*/);
  if (parts.length === 3) {
    const key = parts[0].trim();
    const op = parts[1].trim();
    const val = parts[2].trim().replace(/['"]/g, "");
    const cur = snapshot[key];
    if (op === "==") return cur === val;
    if (op === "!=") return cur !== val;
  }
  return true; // unknown condition → always show
}
