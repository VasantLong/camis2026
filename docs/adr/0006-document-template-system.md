# ADR 0006: 文档模板生成系统

## 状态

已采纳（2026-06-06）

## 背景

当前系统中文档（ActivityPlan、SecurityPlan、KeyMaterial）通过手动上传附件或 seed 脚本硬造，缺少结构化表单填写→模板渲染→生成正式文件的流程。UML 用例规约（UC2-UC4）明确描述了"调取方案模板→在线填写→提交生成"的交互模式。系统需要内置文档模板，角色通过填写表单自动生成备案与审核文件。

## 决策

采用 **DOCX 模板 + 代码定义表单 Schema + 统一版本管理** 的三层架构：

1. **模板格式**：DOCX（`docxtpl` 库，Jinja2 语法占位符 `{{ field_name }}`），存储于代码仓库 `app/templates/{type}/template.docx`，随应用部署
2. **表单字段**：每个模板类型对应一个 Pydantic schema（`app/templates/{type}/schema.py`），字段名与 DOCX 占位符一一对应。前端通过 `GET /activities/{id}/plan/schema` 获取字段定义，通用 `TemplateForm` 组件动态渲染
3. **版本管理**：统一实体 `filled_documents` 管理所有模板产物的版本（含表单快照、DOCX/PDF 产物、模板 hash），通过 `(activity_id, template_type, version_number)` 唯一约束。现有实体（activity_plans/security_plans/key_materials）通过 `current_filled_document_id` 指向当前版本
4. **生成时机**：用户手动触发——"保存草稿"（`draft_data JSONB`）和"提交生成"（创建 `filled_documents` 版本），驳回修正产生新版本
5. **模板类型**：5 个内置模板——活动方案、安保方案（风险等级决定条件段）、风险评估表、安全消防责任确认书、备案承诺书
6. **电子签名**：用户上传签名/印章图片，渲染时嵌入 DOCX 签名占位符
7. **附件分类**：附件挂到 `filled_documents.id`（版本级附件），通用活动附件通过 `activity_id IS NOT NULL AND filled_document_id IS NULL` 区分

## 理由

- **DOCX over HTML→PDF**：政务文书（红头文件、公章位、签字栏）排版要求高，DOCX 天然适配。LibreOffice headless 转 PDF 用于前端预览，保持 100% 保真度
- **代码 Schema over 动态表单引擎**：模板类型固定（5 种），字段相对稳定，无需动态表单引擎的复杂度
- **代码仓库存储 over MinIO**：模板是系统内置资产，非用户内容。随代码部署，走 git review，免于对象存储可用性依赖
- **统一版本管理 over 分散版本字段**：所有模板产物共享版本语义（草稿→生成→驳回→重新生成），一张表统一管理避免重复逻辑

## 前后端契约

### API 端点设计

所有模板操作挂载到实体路由下（模板不是独立资源，是活动实体的附属）：

```
# 活动方案
GET    /activities/{id}/plan/schema              → 返回表单字段定义
PUT    /activities/{id}/plan/draft               → 保存草稿（body: 表单数据）
POST   /activities/{id}/plan/generate            → 提交生成 DOCX+PDF
GET    /activities/{id}/plan/versions             → 版本历史列表
GET    /activities/{id}/plan/versions/{vid}        → 某版本详情（含 data_snapshot）

# 安保方案（同上模式）
GET    /activities/{id}/security-plan/schema
PUT    /activities/{id}/security-plan/draft
POST   /activities/{id}/security-plan/generate
GET    /activities/{id}/security-plan/versions
GET    /activities/{id}/security-plan/versions/{vid}

# 关键材料（material_id 由懒创建获得）
GET    /activities/{id}/materials/{mid}/schema
PUT    /activities/{id}/materials/{mid}/draft
POST   /activities/{id}/materials/{mid}/generate
GET    /activities/{id}/materials/{mid}/versions
GET    /activities/{id}/materials/{mid}/versions/{vid}

# 附件上传（扩展现有端点）
POST   /documents/upload?filled_document_id={fdid}

# PDF 预览（通过 pre-signed URL）
GET    /documents/{doc_id}/url?inline=1
```

### Schema 端点响应格式

`GET /activities/{id}/plan/schema` 返回：

```json
{
  "template_type": "activity_plan",
  "display_name": "活动方案",
  "has_draft": true,
  "current_version": 2,
  "fields": [
    { "name": "activity_name", "ui_label": "活动名称", "ui_type": "text", "required": true },
    { "name": "activity_description", "ui_label": "活动内容描述", "ui_type": "textarea" },
    { "name": "estimated_days", "ui_label": "预计天数", "ui_type": "number", "min": 1 },
    { "name": "risk_factors", "ui_label": "主要风险因素", "ui_type": "repeater", "min_items": 4 },
    { "name": "security_manager_signature", "ui_label": "负责人签名", "ui_type": "signature" }
  ]
}
```

`ui_type` 控件池：`text` / `textarea` / `number` / `date` / `select` / `repeater`（列表增删）/ `signature`（电子签名板）/ `attachment`（文件选择）

### 前端组件架构

通用 `TemplateForm` 组件消费 schema 后动态渲染：
- 根据 `ui_type` 映射到对应控件组件
- 根据 `required` / `min` / `max` / `min_items` 做前端校验
- "保存草稿"按钮调用 `PUT .../draft`（不占版本号）
- "提交生成"按钮调用 `POST .../generate`（渲染 DOCX+PDF，创建版本）
- 提交生成前弹窗确认是否生成新版本

签名控件（`ui_type: signature`）：
- 首次使用时提示用户上传签名/印章图片（存 MinIO，用户级别）
- 后续使用时自动从用户签名库选取
- 渲染时后端嵌入 DOCX 签名占位符

### 表单填写 → 生成流程（以活动方案为例）

```
Promoter 进入活动详情页 → 点击"活动方案"Tab
  ↓
前端 GET /schema → TemplateForm 渲染表单
  ↓ (如果 has_draft=true，预填草稿数据)
Promoter 填写 → 点击"保存草稿"
  ↓ PUT /draft → 写入 activity_plans.draft_data
Promoter 确认完毕 → 点击"提交生成"
  ↓ 弹窗："确认生成活动方案？（将创建 v{N+1} 版本）"
  ↓ POST /generate
后端：docxtpl 渲染 DOCX + LibreOffice 转 PDF → MinIO
  ↓ INSERT filled_documents (version_number=N+1)
  ↓ UPDATE activity_plans.current_filled_document_id = NEW.id
  ↓ UPDATE activity_plans.draft_data = NULL（草稿已消费）
  ↓ 若状态为"待设计方案" → WorkflowService.transition("待安保方案设计")
前端：显示生成成功 + PDF 预览 (iframe)
```

### 安保方案风险等级 → 模板条件段

```
SecurityOfficer 进入安保方案 Tab
  ↓ (首次) 弹窗："请评估活动风险等级"
  ↓ 选择：大型 / 中型 / 高风险
  ↓ 写入 security_plans.risk_level
  ↓ GET /schema?risk_level=大型
后端：根据 risk_level 过滤 schema 字段（条件段可见性）
  ↓ 返回对应的字段定义 + DOCX 模板中对应段落激活
```

同一活动后续修订（驳回重做）不再改变 `risk_level`。

### KeyMaterial 懒创建

```
SecurityOfficer 点击材料列表中的"填写风险评估表"
  ↓ 前端检查：该活动下是否存在 material_type=risk_assessment 的 KeyMaterial？
  ↓ 没有 → POST /activities/{id}/materials (material_type=risk_assessment)
  ↓ 后端创建 KeyMaterial 行，返回 material_id
  ↓ 有 → 直接用已有 material_id
  ↓ GET /activities/{id}/materials/{mid}/schema → 渲染表单
```

一个活动下同 `(activity_id, material_type)` 唯一，不会重复创建。

### 版本历史与差异展示

版本时间线（`GET .../versions`）返回：
```json
{
  "versions": [
    { "version_number": 3, "generated_by": "张三", "created_at": "...", "is_current": true },
    { "version_number": 2, "generated_by": "张三", "created_at": "...", "is_current": false },
    { "version_number": 1, "generated_by": "李四", "created_at": "...", "is_current": false }
  ]
}
```

版本差异（`GET .../versions/{vid}/diff?against={vid2}`）：
- 后端比较两个版本的 `data_snapshot`（JSONB 字段级 diff）
- 前端以高亮方式展示变更字段：绿色 = 新增内容，黄色 = 修改内容，红色 = 删除内容

### 备案打包 ZIP 结构

```
filing_pack_{activity_id}_{timestamp}.zip
├── 备案清单.pdf                     ← 索引页（材料名+版本号+签署+合格状态）
├── 01_活动方案_v3.docx
├── 02_安保方案_v2.docx
├── 03_风险评估表_v1.docx
├── 04_责任确认书_v1.docx
└── 05_备案承诺书_v1.docx
```

- ZIP 存 MinIO，`filing_docs` 加 `pack_url` 字段指向
- 前端提供"导出备案包"下载按钮
- 政府对接人员线上逐条审查（走各 `filled_documents` 行），线下下载 ZIP 打印

### PDF 预览方案

- 后端生成 DOCX 时同步用 LibreOffice headless 转 PDF，存 MinIO
- `filled_documents` 同时记录 `minio_path`（DOCX）和 `pdf_path`（PDF）
- 前端预览使用 `<iframe src="{presigned_pdf_url}">` — 100% 排版保真度
- 不使用 mammoth.js / docx-preview 等前端 DOCX 渲染库（政务文书排版偏差不可接受）

## 影响

- 新增 `filled_documents` 表 + `TemplateService`（第 11 个 Service）
- 修改 `activity_plans`、`security_plans`、`key_materials`（加 `draft_data`、`current_filled_document_id`、unique 约束）
- 修改 `documents`（加 `filled_document_id`）
- 前端新增通用 `TemplateForm` 组件
- 打包流程改造：`pack_materials()` 生成 ZIP，补齐 `filing_doc_materials` 关联
- 分三阶段实施：P1 模板引擎核心（后端渲染链路）→ P2 前端表单（TemplateForm + 版本历史）→ P3 签名+打包
- 新增依赖：`docxtpl`、`python-docx`。PDF 转换复用 LibreOffice
