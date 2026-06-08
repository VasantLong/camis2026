# 模板 DOCX 按源文件样式重建

分支: `feat/workflow-enhance`

## 问题

当前 5 个 `app/templates/*/template.docx` 为简化版，字段排版与源 `.doc` 文件（`docs/风险评估报备表.doc`、`docs/主办单位安全和消防责任确认书.doc` 等）差异较大：

- 源文件为正式政府表格，含复杂表格结构、合并单元格、边框、签章区
- 当前 template.docx 为平铺文本，丢失了表格布局和签章位置

## 方案

docxtpl 支持在 Word 表格中注入 Jinja2 占位符，表格样式完全保留。流程：

1. 将源 `.doc` 转为 `.docx`（LibreOffice）
2. 在表格对应位置插入 `{{ field_name }}` 占位符
3. 复杂表格、合并单元格、边框全部保留

## 时机

待工作流全部跑通后再实施。当前不影响流程验证。

## 涉及文件

| 模板 | 源文件 |
|------|--------|
| `app/templates/risk_assessment/template.docx` | `docs/风险评估报备表.doc` |
| `app/templates/responsibility_letter/template.docx` | `docs/主办单位安全和消防责任确认书.doc` |
| `app/templates/activity_plan/template.docx` | `docs/活动方案.doc` |
| `app/templates/security_plan/template.docx` | `docs/安保方案.doc`（如有） |
