export const ACTIVITY_STATUSES = [
  "待设计方案",
  "待安保方案设计",
  "待备案申请",
  "备案材料已交接",
  "审批通过",
  "审批通过-待举办",
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
  待补充备案材料: "orange",
  "不通过/已终止": "red",
  已取消: "default",
  已延期: "warning",
};
