# 文档模板流程测试 — 当前状态与遗留问题

分支: `test/template-flow` → `feat/workflow-enhance`

## 测试覆盖

`tests/browser/17_template_flow.py` — 3 个测试用例：

| TC | 内容 | 状态 |
|----|------|------|
| TC1 | Promoter 活动方案：草稿 → 生成 v1 → 版本出现 | ✅ 通过 |
| TC2 | 修改内容 → 生成 v2 → 版本对比 v1 vs v2 | ✅ 通过 |
| TC3 | SecurityOfficer 安保方案：风险等级 → 生成 | ✅ 通过 |

## 已修复的问题

1. **FK 约束违规**: `_get_or_create_entity` 创建 ActivityPlan 时 `designer_id=0000...` 无效 UUID → 已传 `user_id`
2. **缺失 commit()**: 移除自动 workflow 后 `generate()` 未 commit，数据回滚 → 已加 `await self.db.commit()`
3. **dayjs("") → Invalid Date**: 空字符串传入 dayjs → 已加空值判断
4. **`require_permission` 注入方式**: 错误使用 `Depends(require_permission(...))` → 改为直接传回调
5. **PDF 预览阻塞生成**: Modal iframe 挡住后续操作 → PDF 改为后台生成 + 版本列表按需预览
6. **版本不持久化**: commit() 缺失导致页面刷新后版本消失 → 已修复
7. **antd v6 弃用警告**: `Space direction` → `orientation`, `Modal destroyOnClose` → `destroyOnHidden`
8. **key spread 警告**: `{...common}` 含 key 展开到 Form.Item → 改为显式 props
9. **TC2 Modal `onOk` 不触发**: `page.keyboard.press("Enter")` 被 antd v6 Modal 整体 div 截获 → 改用 `.locator('...').click()` 直接点击按钮
10. **v2 生成阻塞**: `_docx_to_pdf_sync` 中 `subprocess.run` 阻塞 asyncio 事件循环，v1 后台 PDF 任务阻塞 v2 请求 → 包裹 `asyncio.to_thread()` 将 soffice 放入线程池
11. **Console 日志捕获**: 各测试脚本内联 console 监听重复 → 提炼 `capture_console()` 到 `utils.py`，实时写入 `logs/{name}_console.log`
12. **snapshot_data 未回传前端**: `get_schema` service 已计算但 route handler 未传入 SchemaResponse → 三个 handler 补传 `snapshot_data`
13. **角色权限控制**: TemplateForm 无只读模式，有 `view_owned_activity` 但无写权限的用户可交互但 403 → 新增 `readOnly` prop，Promoter 编辑活动方案，SecurityOfficer/Manager 编辑安保方案
14. **最终确定缺表单校验**: `finalize_plan` 不验证内容完整性 → 前端基于 snapshot 禁用按钮 + 后端 Pydantic 校验 `ActivityPlanForm`

## 未解决的问题

### 1. 401 Unauthorized 偶发

控制台出现 `Failed to load resource: 401`，来自 `/auth/refresh` 端点。token 在 60 分钟过期，但测试 30 秒内到期——原因未明。可能是 CDP 模式下 cookie/session 同步问题。

### 2. 版本详情弹窗"慢"

用户反馈点击版本"详情"按钮后弹窗慢。后端 6ms，前端 Modal 动画约 300ms。感知慢可能是动画 + API 调用间隙。可优化为预取数据。

## 待实施的功能

*(暂无)*

## 下一步建议

1. 排查 401 问题——可能是 CDP 模式下 cookie/session 同步问题
2. 为测试添加更多中间状态断言（截图、DOM 检查）
3. 安保方案最终确定按钮及校验（与活动方案对称）
