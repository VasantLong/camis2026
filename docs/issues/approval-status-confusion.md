# 审批状态概念混淆

## 问题

`ApprovalRecord.approval_status`（审批记录标签）与 `Activity.status`（活动状态）是两个不同概念。前端 GovLiaison 审批提交时传 `approval_status: "审批通过-待举办"` 导致 422 校验失败，因为 `ApprovalRecordRequest` 只接受 `"审批通过" | "待补充备案材料" | "不通过/已终止"`。

## 当前状态

- **"审批通过" 作为 Activity 状态**：已完全移除。`TRANSITION_MATRIX` 不含此状态，活动从 `备案材料已交接` 直达 `审批通过-待举办`
- **"审批通过" 作为 ApprovalRecord 标签**：仍然保留，存储在 `approval_records.approval_status` 列。后端 `create_approval_record()` 映射：`approval_status="审批通过"` → `target="审批通过-待举办"`

## 临时修复

前端 `targetStatus` 在 approve 动作时传 `"审批通过"`（而非 `"审批通过-待举办"`）。

## 后续改进建议

- 统一命名：`ApprovalRecord.approval_status` 的值与 `Activity.status` 完全独立，容易混淆。建议将 `approval_status` 改为更明确的列名（如 `decision`），或使用英文枚举值（`approved` / `revise` / `rejected`）与中文活动状态区分
- 前端 targetStatus 变量命名也容易误导——它实际是 `approval_status` 而非 `target_status`
