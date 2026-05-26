export const ROLE_LABEL_MAP: Record<string, string> = {
  SuperAdmin: "超级管理员",
  Promoter: "宣策部",
  SecurityOfficer: "安保部",
  AdminStaff: "行政部",
  AdminManager: "行政部负责人",
  SecurityManager: "安保部负责人",
  GovLiaison: "政府对接",
};

export const ROLE_DESC_MAP: Record<string, string> = {
  SuperAdmin: "管理用户角色、系统配置",
  Promoter: "创建立项、编制活动方案",
  SecurityOfficer: "编制安保方案、审核材料、确认审批结果",
  AdminStaff: "监控活动面板、强制变更状态、管理用户",
  GovLiaison: "上传批文、标注审批结果",
};

export const ACTIVITY_STATUSES = [
  "待设计方案",
  "待安保方案设计",
  "待备案申请",
  "备案材料已交接",
  "审批通过",
  "审批通过-待举办",
  "举办中",
  "已结束",
  "待补充备案材料",
  "不通过/已终止",
  "已取消",
  "已延期",
];

export const STATUS_COLOR_MAP: Record<string, string> = {
  待设计方案: "blue",
  待安保方案设计: "cyan",
  待备案申请: "geekblue",
  备案材料已交接: "purple",
  审批通过: "green",
  "审批通过-待举办": "gold",
  举办中: "volcano",
  已结束: "green",
  待补充备案材料: "orange",
  "不通过/已终止": "red",
  已取消: "default",
  已延期: "warning",
};

export const TERMINAL_STATUSES = [
  "已结束",
  "不通过/已终止",
  "已取消",
  "已延期",
];

export interface TransitionDef {
  label: string;
  mode: "transition" | "reject" | "forceCancel" | "forcePostpone";
  toStatus?: string;
  permission: string;
  confirmMessage?: string;
}

export function getAvailableTransitions(
  status: string,
  permissions: string[]
): TransitionDef[] {
  if (TERMINAL_STATUSES.includes(status)) return [];

  const has = (p: string) => permissions.includes(p);
  const actions: TransitionDef[] = [];

  if (status === "待设计方案") {
    if (has("manage_security"))
      actions.push({ label: "提交到安保方案设计", mode: "transition", toStatus: "待安保方案设计", permission: "manage_security" });
  }
  if (status === "待安保方案设计") {
    if (has("reject_approval"))
      actions.push({ label: "驳回（内部循环）", mode: "reject", permission: "reject_approval" });
    if (has("manage_security"))
      actions.push({ label: "签署完成—提交备案", mode: "transition", toStatus: "待备案申请", permission: "manage_security" });
  }
  if (status === "待备案申请") {
    // Filing phase — actions come from Filing components
  }
  if (status === "备案材料已交接") {
    if (has("manage_security"))
      actions.push({ label: "审批通过", mode: "transition", toStatus: "审批通过", permission: "manage_security" });
    if (has("manage_security"))
      actions.push({ label: "需补充材料", mode: "transition", toStatus: "待补充备案材料", permission: "manage_security" });
    if (has("manage_security"))
      actions.push({ label: "驳回—不通过", mode: "transition", toStatus: "不通过/已终止", permission: "manage_security" });
  }
  if (status === "待补充备案材料") {
    if (has("manage_security"))
      actions.push({ label: "重新递交", mode: "transition", toStatus: "备案材料已交接", permission: "manage_security" });
  }
  if (status === "审批通过") {
    if (has("confirm_approval"))
      actions.push({ label: "确认通过", mode: "transition", toStatus: "审批通过-待举办", permission: "confirm_approval" });
    if (has("reject_approval"))
      actions.push({ label: "驳回（逆向流转）", mode: "reject", permission: "reject_approval" });
  }
  if (status === "审批通过-待举办") {
    if (has("manage_security"))
      actions.push({ label: "活动开始举办", mode: "transition", toStatus: "举办中", permission: "manage_security" });
  }
  if (status === "举办中") {
    if (has("manage_security"))
      actions.push({ label: "活动结束", mode: "transition", toStatus: "已结束", permission: "manage_security" });
  }

  if (has("force_cancel"))
    actions.push({ label: "强制取消", mode: "forceCancel", permission: "force_cancel" });
  if (has("force_postpone"))
    actions.push({ label: "强制延期", mode: "forcePostpone", permission: "force_postpone" });

  return actions;
}
