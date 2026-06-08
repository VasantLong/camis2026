# API 路由设计

模块化单体架构下的 REST 端点契约。所有端点（除 `/auth/*` 和 `/health`）需携带 `Authorization: Bearer <jwt>`。

## 路由总览

| 方法   | 路径 | 权限 |
| ------ | ---- | ---- |
| `POST` | `/auth/register` | 公开 |
| `POST` | `/auth/login` | 公开 |
| `GET`  | `/auth/me` | 登录用户 |
| `PATCH`| `/auth/me` | 登录用户 |
| `GET`  | `/auth/roles` | 登录用户 |
| `POST` | `/auth/me/role-request` | 登录用户 |
| `POST` | `/auth/me/email-change` | 登录用户 |
| `GET`  | `/auth/verify-email` | 公开（token 验证） |
| `POST` | `/auth/refresh` | Cookie |
| `POST` | `/auth/logout` | 登录用户 |
| `GET`  | `/health` | 公开 |
| `GET`  | `/activities` | `view_owned_activity` |
| `POST` | `/activities` | `create_activity` |
| `GET`  | `/activities/{id}` | `view_owned_activity` |
| `GET`  | `/activities/{id}/history` | `view_owned_activity` |
| `GET`  | `/activities/{id}/documents` | `view_owned_activity` |
| `GET`  | `/activities/{id}/security-plan` | `view_owned_activity` |
| `PUT`  | `/activities/{id}/security-plan` | `manage_security` |
| `GET`  | `/activities/{id}/plan/schema` | 登录用户 |
| `PUT`  | `/activities/{id}/plan/draft` | `submit_plan` |
| `POST` | `/activities/{id}/plan/generate` | `submit_plan` |
| `GET`  | `/activities/{id}/plan/versions` | 登录用户 |
| `GET`  | `/activities/{id}/plan/versions/{vn}` | 登录用户 |
| `GET`  | `/activities/{id}/plan/versions/{v1}/diff/{v2}` | 登录用户 |
| `POST` | `/activities/{id}/plan/finalize` | `submit_plan` |
| `GET`  | `/activities/{id}/security-plan/schema` | 登录用户 |
| `PUT`  | `/activities/{id}/security-plan/draft` | `manage_security` |
| `POST` | `/activities/{id}/security-plan/generate` | `manage_security` |
| `POST` | `/activities/{id}/security-plan/submit-review` | `manage_security` |
| `POST` | `/activities/{id}/security-plan/sign` | `manage_security` |
| `POST` | `/activities/{id}/security-plan/reject` | `reject_approval` |
| `GET`  | `/activities/{id}/security-plan/versions` | 登录用户 |
| `GET`  | `/activities/{id}/security-plan/versions/{vn}` | 登录用户 |
| `GET`  | `/activities/{id}/security-plan/versions/{v1}/diff/{v2}` | 登录用户 |
| `POST` | `/activities/{id}/materials` | `pack_filing` （创建 KeyMaterial，返回 material_id） |
| `GET`  | `/activities/{id}/materials/{mid}/schema` | 登录用户 |
| `PUT`  | `/activities/{id}/materials/{mid}/draft` | `pack_filing` |
| `POST` | `/activities/{id}/materials/{mid}/generate` | `pack_filing` |
| `GET`  | `/activities/{id}/materials/{mid}/versions` | 登录用户 |
| `GET`  | `/activities/{id}/materials/{mid}/versions/{vn}` | 登录用户 |
| `GET`  | `/activities/{id}/materials/{mid}/versions/{v1}/diff/{v2}` | 登录用户 |
| `PUT`  | `/activities/{id}/status` | `manage_security`¹ |
| `POST` | `/activities/{id}/reject` | `reject_approval` |
| `POST` | `/activities/{id}/force-cancel` | `force_cancel` |
| `POST` | `/activities/{id}/force-postpone` | `force_postpone` |
| `POST` | `/documents/upload` | 登录用户 |
| `GET`  | `/documents/{id}` | 登录用户（302 重定向） |
| `GET`  | `/documents/{id}/url` | 登录用户（返回 presigned URL） |
| `GET`  | `/documents/presign/by-path?path=...` | 登录用户（通过 minio_path 获取 presigned URL） |
| `GET`  | `/activities/{id}/materials` | 登录用户 |
| `POST` | `/activities/{id}/materials/{mid}/sign` | `sign_document` |
| `POST` | `/activities/{id}/materials/{mid}/audit` | `audit_material` |
| `GET`  | `/activities/{id}/materials/audit-history` | 登录用户 |
| `POST` | `/activities/{id}/filing/pack` | `pack_filing` |
| `POST` | `/activities/{id}/filing/handover` | `pack_filing` |
| `GET`  | `/activities/{id}/filing/validate` | `pack_filing` |
| `GET`  | `/activities/{id}/filing/status` | 登录用户 |
| `GET`  | `/dashboard` | `view_dashboard` |
| `GET`  | `/dashboard/activities/{id}` | `view_dashboard` |
| `POST` | `/dashboard/reports/monthly` | `export_report` |
| `GET`  | `/admin/role-requests` | `manage_users` |
| `POST` | `/admin/role-requests/{id}/approve` | `manage_users` |
| `POST` | `/admin/role-requests/{id}/reject` | `manage_users` |
| `GET`  | `/admin/users` | `administer_users` |
| `GET`  | `/admin/users/{id}` | `administer_users` |
| `PUT`  | `/admin/users/{id}/roles` | `administer_users` |
| `PATCH`| `/admin/users/{id}/status` | `administer_users` |
| `POST` | `/admin/users/{id}/archive` | `administer_users` |
| `POST` | `/admin/users/{id}/unarchive` | `administer_users` |
| `GET`  | `/admin/users/{id}/overview` | `administer_users` |
| `GET`  | `/notifications` | 登录用户 |
| `GET`  | `/notifications/unread-count` | 登录用户 |
| `PATCH`| `/notifications/{id}/read` | 登录用户 |
| `PATCH`| `/notifications/read-all` | 登录用户 |
| `GET`  | `/dashboard/reports/{month}` | `export_report` |
| `GET`  | `/dashboard/reports/{month}/data` | `export_report` |
| `GET`  | `/dashboard/reports/{month}/view` | `export_report` |
| `GET`  | `/activities/counts` | 登录用户 |

> ¹ `PUT /activities/{id}/status` 同时接受 `manage_security`、`audit_material`、`submit_plan` 权限。目标状态为"审批通过-待举办"时额外要求 `confirm_approval`。
> 活动可见性按角色自动过滤状态（见 `docs/rbac.md`）。

## 端点详细说明

### 活动管理

#### `POST /activities` — 创建活动（立项）

```json
// Request
{
  "name": "2026年春节文旅嘉年华",
  "type": "大型户外活动",
  "estimated_time": "2026-02-10T09:00:00+08:00",
  "location": "市民广场",
  "sponsor": "市文旅局",
  "sponsor_contact": "张三",
  "sponsor_phone": "13800138000",
  "deadline": "2026-01-20T18:00:00+08:00",
  "designer_id": "uuid-of-designer"
}

// Response 201
{
  "id": "uuid",
  "name": "2026年春节文旅嘉年华",
  "status": "待设计方案",
  "created_at": "2026-01-05T10:30:00+08:00"
}
```

**校验规则**：必填字段缺失 → 422；截止时间早于当前时间或晚于举办时间 → 400；场地/时间冲突 → 409

#### `GET /activities` — 活动列表

```
GET /activities?status=审批通过-待举办&page=1&size=20
```

支持按 status、date_from、date_to、keyword、tab（`pending`\|`completed`）筛选。分页，返回 `{ items: ActivityResponse[], total: int }`。

#### `GET /activities/{id}` — 活动详情

返回 Activity 全部字段 + 关联的子实体摘要（ActivityPlan、SecurityPlan、FilingDoc、ApprovalRecord 当前状态）。

#### `GET /activities/{id}/history` — 状态流转历史

```json
[
  {
    "from_status": null,
    "to_status": "待设计方案",
    "operator": "张三",
    "timestamp": "..."
  },
  {
    "from_status": "待设计方案",
    "to_status": "待安保方案设计",
    "operator": "李四",
    "timestamp": "..."
  },
  {
    "from_status": "待安保方案设计",
    "to_status": "待备案申请",
    "operator": "王五",
    "timestamp": "..."
  }
]
```

### 工作流

#### `PUT /activities/{id}/status` — 状态变更

```json
// Request
{
  "to_status": "待安保方案设计",
  "comment": "活动方案已提交，请安保部审核"
}

// Response 200
{
  "activity_id": "uuid",
  "from_status": "待设计方案",
  "to_status": "待安保方案设计"
}
```

**状态机约束**：`to_status` 必须是 `docs/state-machine.md` 中定义的合法转换目标，否则 422。

#### `POST /activities/{id}/reject` — 驳回

```json
// Request
{
  "reason": "安保人员配置不足，需增加2人"
}
// → status 不变 (UC3内部循环) 或 status 回滚至 "待安保方案设计" (UC6逆向流转)
```

#### `POST /activities/{id}/force-cancel` — 强制取消

```json
// Request
{
  "reason": "红色暴雨预警，接上级通知取消"
}
// → status = "已取消"，锁定后续操作
```

#### `POST /activities/{id}/force-postpone` — 强制延期

```json
// Request
{
  "reason": "场地维修中，延期至下月"
}
// → status = "已延期"，锁定后续操作
```

### 文档管理

#### `POST /activities/{id}/documents` — 上传文件

multipart/form-data：

```
file: <binary>
tags: "风险评估表,安保"
content_type: "application/pdf"
```

→ MinIO 存储 + `documents` 表元数据。返回 DocumentResponse。

#### `GET /documents/{id}` — 下载文件

302 重定向至 MinIO 预签名 URL（30 分钟有效）。✅ 已实现。

#### `GET /activities/{id}/documents` — 活动关联文档列表

返回该活动下所有上传的文档元数据列表。

### 备案

#### `POST /activities/{id}/filing/pack` — 打包备案材料

聚合该活动关联的所有已签署文件 → 生成 PDF 集合。返回打包结果（含下载链接）。

**前置条件**：所有 KeyMaterial 的电子签名齐全，否则 422 返回缺失清单。

#### `POST /activities/{id}/filing/handover` — 确认纸质交接

安保部人员线下递交给政府对接人员后在系统中确认。

#### `GET /activities/{id}/filing/validate` — 校验材料合规性

返回所有 KeyMaterial 的合规状态清单。

### 仪表盘

#### `GET /dashboard` — 活动实施面板

返回多维度聚合数据：

```json
{
  "total": 156,
  "by_status": {
    "待设计方案": 12,
    "待安保方案设计": 8,
    "审批通过-待举办": 45,
    "已取消": 3
  },
  "compliance_rate": 0.92,
  "recent_anomalies": [
    {
      "activity_id": "uuid",
      "reason": "红色暴雨取消",
      "change_status": "已取消"
    }
  ]
}
```

#### `POST /dashboard/reports/monthly` — 导出月报

```json
// Request
{ "month": "2026-01" }
// → 异步生成 PDF 报表，完成后通过 NotificationService 推送下载链接
```

### 文档模板

模板系统提供 5 种内置文档模板（活动方案、安保方案、风险评估报备表、安全消防责任确认书、备案承诺书），通过 schema 驱动表单填写 → `docxtpl` 渲染 DOCX → `soffice` 转 PDF 存 MinIO。

#### `GET /activities/{id}/plan/schema` — 获取活动方案表单定义

```json
{
  "template_type": "activity_plan",
  "display_name": "活动方案",
  "has_draft": true,
  "draft_data": {"activity_content": "上次草稿内容"},
  "current_version": 2,
  "fields": [
    {"name": "activity_content", "ui_label": "活动主要内容", "ui_type": "textarea", "required": true}
  ]
}
```

前端 `TemplateForm` 根据 `fields` 动态渲染表单控件（8 种 `ui_type`：text/textarea/number/date/select/checkbox/repeater/signature）。

#### `PUT /activities/{id}/plan/draft` — 保存草稿

不占版本号，写入 `activity_plans.draft_data`。

#### `POST /activities/{id}/plan/generate` — 提交生成

渲染 DOCX + 转 PDF → MinIO → INSERT `filled_documents`（版本+1）→ 清空草稿。响应含 `pdf_preview_url`（预签名 URL，前端 iframe 预览）。活动状态为"待设计方案"时自动触发工作流变迁至"待安保方案设计"。

安保方案 schema 含 `risk_level_first: true`，前端先弹风险等级选择器（大型/中型/高风险），写入 `PUT /activities/{id}/security-plan` 的 `risk_level` 后加载条件表单。

版本历史和差异对比见 `GET .../versions` 和 `GET .../versions/{v1}/diff/{v2}`。

## 实现状态

| 端点                                    | 状态                                    |
| --------------------------------------- | --------------------------------------- |
| `GET /health`                           | ✅                                      |
| `POST /auth/register`                   | ✅                                      |
| `POST /auth/login`                      | ✅                                      |
| `POST /auth/refresh`                    | ✅                                      |
| `POST /auth/logout`                     | ✅                                      |
| `GET /auth/me`                          | ✅                                      |
| `PATCH /auth/me`                        | ✅                                      |
| `POST /auth/me/role-request`            | ✅                                      |
| `POST /auth/me/email-change`            | ✅                                      |
| `GET /auth/verify-email`                | ✅                                      |
| `POST /activities`                      | ✅                                      |
| `GET /activities`                       | ✅                                      |
| `GET /activities/{id}`                  | ✅                                      |
| `GET /activities/{id}/history`          | ✅                                      |
| `PUT /activities/{id}/status`           | ✅                                      |
| `POST /activities/{id}/reject`          | ✅                                      |
| `POST /activities/{id}/force-cancel`    | ✅                                      |
| `POST /activities/{id}/force-postpone`  | ✅                                      |
| `POST /documents/upload`                | ✅（待适配 activity_id）                |
| `GET /documents/{id}`                   | ✅                                      |
| `GET /documents/project/{project_id}`   | ✅（待改为 /activities/{id}/documents） |
| `GET /activities/{id}/documents`        | ❌                                      |
| `POST /activities/{id}/documents`       | ❌                                      |
| `GET /activities/{id}/filing/validate`  | ✅                                      |
| `POST /activities/{id}/filing/pack`     | ✅                                      |
| `POST /activities/{id}/filing/handover` | ✅                                      |
| `GET /dashboard`                        | ✅                                      |
| `GET /dashboard/activities/{id}`        | ✅                                      |
| `POST /dashboard/reports/monthly`       | ✅                                      |

> 已实现: 22/22 端点 + refresh/logout。全部实现。

## 错误响应格式

统一格式：

```json
{
  "detail": "错误描述",
  "code": "RESOURCE_CONFLICT",
  "fields": { "location": "该场地涉及时段已被占用" }
}
```

| HTTP 状态码 | 场景                               |
| ----------- | ---------------------------------- |
| 201         | 创建成功                           |
| 200         | 操作成功                           |
| 302         | 文件下载重定向                     |
| 400         | 校验失败（必填缺失、格式错误）     |
| 401         | 未登录或 token 过期                |
| 403         | 已登录但无权限（角色不符）         |
| 404         | 活动/文档不存在                    |
| 409         | 资源冲突（场地冲突、状态不可变更） |
| 422         | 业务规则阻断（材料不全、签名缺失） |
