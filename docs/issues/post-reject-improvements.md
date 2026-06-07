# 驳回后改进 + 待备案申请界面设计

分支: `feat/workflow-enhance`

## 1. 驳回后未修改时阻止重复提交

### 问题

当前 SecurityOfficer 被驳回后，"提交审核"按钮立即可点击。如果 Officer 未做任何修改（未生成新版本）就再次提交，Manager 看到的仍是同一内容，形成无效循环。

### 方案

**A) 弹出提示**：点击"提交审核"时检查当前最新版本号是否与驳回前相同 → 相同则弹窗提示"请先生成新版本后再提交审核"

**B) 按钮禁用**：驳回后"提交审核"按钮直接禁用 → 生成新版本（版本号递增）后重新启用

推荐 **B**——更直接的 UX 引导，避免用户做无效操作。实现：在 `submit-review` 按钮的 disabled 条件中加入"是否存在大于驳回时版本的新版本"。

### 相关代码

- `ActivityDetailPage.tsx`：submit-review 按钮 disabled 条件
- `template_service.py`：`submit_security_plan_for_review`

## 2. "待备案申请"状态下的界面设计

### 背景

活动流转到"待备案申请"后，Officer 需要打包备案材料，Manager 需要审阅。当前两个角色看到的内容未专门设计。

### 待讨论

| 角色 | 当前看到 | 需要讨论 |
|------|---------|---------|
| SecurityOfficer | 安保方案表单（锁定）+ 备案 tab | 是否需要更清晰的打包引导？ |
| SecurityManager | VersionTimeline | 是否需要查看打包进度？ |

### 建议

- **Officer**：安保方案 tab 显示"已签署"确认 + VersionSnapshot，引导用户到备案 tab 进行打包操作
- **Manager**：安保方案 tab 显示"已签署"确认 + VersionTimeline，无需额外操作

具体设计待讨论后确定。
