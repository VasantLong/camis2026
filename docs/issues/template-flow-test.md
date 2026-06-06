# 文档模板流程测试 — 当前状态与遗留问题

分支: `test/template-flow`

## 测试覆盖

`tests/browser/17_template_flow.py` — 3 个测试用例：

| TC | 内容 | 状态 |
|----|------|------|
| TC1 | Promoter 活动方案：草稿 → 生成 v1 → 版本出现 | ✅ 通过 |
| TC2 | 修改内容 → 生成 v2 → 版本对比 v1 vs v2 | ❌ 阻塞 |
| TC3 | SecurityOfficer 安保方案：风险等级 → 生成 | ⏳ 依赖 TC2 |

## 已修复的问题

1. **FK 约束违规**: `_get_or_create_entity` 创建 ActivityPlan 时 `designer_id=0000...` 无效 UUID → 已传 `user_id`
2. **缺失 commit()**: 移除自动 workflow 后 `generate()` 未 commit，数据回滚 → 已加 `await self.db.commit()`
3. **dayjs("") → Invalid Date**: 空字符串传入 dayjs → 已加空值判断
4. **`require_permission` 注入方式**: 错误使用 `Depends(require_permission(...))` → 改为直接传回调
5. **PDF 预览阻塞生成**: Modal iframe 挡住后续操作 → PDF 改为后台生成 + 版本列表按需预览
6. **版本不持久化**: commit() 缺失导致页面刷新后版本消失 → 已修复
7. **antd v6 弃用警告**: `Space direction` → `orientation`, `Modal destroyOnClose` → `destroyOnHidden`
8. **key spread 警告**: `{...common}` 含 key 展开到 Form.Item → 改为显式 props

## 未解决的问题

### 1. 第二次生成的确认弹窗无法触发 (TC2 阻塞)

**现象**: TC1 生成 v1 成功，版本列表正常显示。TC2 修改 textarea 后"提交生成"按钮启用，确认弹窗打开，但点击/Enter 都无法触发 `onOk` 回调，Modal 不关闭。

**已排查**:
- 按钮确实是 enabled 状态 (测试断言通过)
- Modal 确实打开了 (测试断言通过)
- `onOk` → `doGenerate` → `onSubmit` → API 调用链至少在第一次生成时正常 (v1 出现)
- 后端日志显示最后一次 TC1 的 generate 返回 200/51ms
- `confirmLoading={submitting}` 始终为 false (因 doGenerate 中 setSubmitting 未在正确时机设置)

**怀疑方向**:
- antd v6 Modal `onOk` 与 async 函数交互问题
- React 状态批处理导致 `setConfirmOpen(false)` 在 `doGenerate` finally 中未生效
- `planSchema` 引用变化触发组件重渲染，Modal 状态丢失
- 401/token 刷新干扰 axios 请求

### 2. 401 Unauthorized 偶发

控制台出现 `Failed to load resource: 401`，来自 `/auth/refresh` 端点。token 在 60 分钟过期，但测试 30 秒内到期——原因未明。

### 3. 版本详情弹窗"慢"

用户反馈点击版本"详情"按钮后弹窗慢。后端 6ms，前端 Modal 动画约 300ms。感知慢可能是动画 + API 调用间隙。可优化为预取数据。

## 待实施的功能

1. **"最终确定"按钮**: 已加后端端点 `POST .../plan/finalize` + 前端按钮，但未在测试中验证。需在 TC2 后点击"最终确定"才能触发 workflow 转到"待安保方案设计"
2. **角色权限控制**: Promoter 编辑活动方案，其他角色只读最新版本内容
3. **表单无修改时禁用按钮**: 已实现基于 snapshot diff 的 `isDirty` 逻辑

## 下一步建议

1. 排查 antd Modal `onOk` 回调不执行的根本原因——可能是 React 状态更新时序问题
2. 考虑将 Modal 改为受控组件 + 独立 submit handler，避免 async onOk 的复杂性
3. 为测试添加更多中间状态断言（截图、DOM 检查）
4. 排查 401 问题——可能是 CDP 模式下 cookie/session 同步问题
