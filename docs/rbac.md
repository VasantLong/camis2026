# RBAC 权限配置

## 表结构

```
roles ──< role_permissions >── permissions
  │
  ├──< user_roles >── users
  │
  └──< role_requests >── users (角色申请)
```

| 表 | 用途 | 主键 |
|----|------|------|
| `roles` | 角色定义 | `id` (UUID) |
| `permissions` | 权限定义 (resource + action) | `id` (UUID) |
| `role_permissions` | 角色 ↔ 权限，多对多 | (`role_id`, `permission_id`) |
| `user_roles` | 用户 ↔ 角色，多对多 | (`user_id`, `role_id`) |
| `role_requests` | 角色申请（待审批/已批准/已驳回） | `id` (UUID) | |

一个用户可拥有多个角色，一个角色可拥有多个权限。角色 UUID 由 `uuid_generate_v4()` 在 INSERT 时生成，引用角色时按 `name` 查询。

---

## 角色总览

| 角色 | 部门 | 职责 | 权限数 |
|------|------|------|--------|
| **SuperAdmin** | 系统 | 管理用户角色、系统配置 | 1 |
| **Promoter** | 宣策部 | 创建立项、编制活动方案 | 3 |
| **SecurityOfficer** | 安保部 | 编制安保方案、审核材料、确认审批结果 | 7 |
| **AdminStaff** | 行政部 | 监控活动面板、强制变更状态、管理用户 | 5 |
| **GovLiaison** | 政府对接 | 上传批文、标注审批结果 | 2 |

---

## 权限全量（18 项）

### SuperAdmin（1 项）

| 权限名 | 资源 | 操作 | 对应用例 |
|--------|------|------|---------|
| `manage_users` | users | manage | 查看/审批/驳回角色申请 |

### Promoter（3 项）

| 权限名 | 资源 | 操作 | 对应用例 |
|--------|------|------|---------|
| `create_activity` | activities | create | 创建活动 |
| `upload_plan` | activities | upload_plan | 上传活动方案文件 |
| `view_owned_activity` | activities | view_owned | 查看自己创建的活动列表和详情 |

### SecurityOfficer（7 项）

| 权限名 | 资源 | 操作 | 对应用例 |
|--------|------|------|---------|
| `manage_security` | activities | manage_security | 状态流转（提交安保方案设计、签署完成） |
| `upload_security_material` | documents | upload | 上传安保材料 |
| `audit_material` | materials | audit | 审核备案材料 |
| `sign_document` | documents | sign | 电子签署 |
| `confirm_approval` | activities | confirm_approval | 确认政府审批结果（转为"审批通过-待举办"） |
| `reject_approval` | activities | reject_approval | 驳回审批结果（打回政府对接） |
| `pack_filing` | filing | pack | 校验材料、打包、纸质交接 |

### AdminStaff（5 项）

| 权限名 | 资源 | 操作 | 对应用例 |
|--------|------|------|---------|
| `view_dashboard` | dashboard | view | 查看活动面板、活动详情统计 |
| `force_cancel` | activities | force_cancel | 强制取消活动 |
| `force_postpone` | activities | force_postpone | 强制延期活动 |
| `export_report` | dashboard | export_report | 导出月报 |
| `manage_users` | users | manage | 查看/审批/驳回角色申请 |

### GovLiaison（2 项）

| 权限名 | 资源 | 操作 | 对应用例 |
|--------|------|------|---------|
| `upload_approval` | documents | upload_approval | 上传政府批文 |
| `update_approval_status` | activities | update_approval_status | 标记审批结果（通过/需补充/不通过） |

---

## 路由权限映射（实际生效的 18 个端点）

| 方法 | 路径 | 权限 | 角色 |
|------|------|------|------|
| `POST` | `/auth/me/role-request` | 登录即可 | 任意用户 |
| `GET` | `/admin/role-requests` | `manage_users` | SuperAdmin / AdminStaff |
| `POST` | `/admin/role-requests/{id}/approve` | `manage_users` | SuperAdmin / AdminStaff |
| `POST` | `/admin/role-requests/{id}/reject` | `manage_users` | SuperAdmin / AdminStaff |
| `POST` | `/activities` | `create_activity` | Promoter |
| `GET` | `/activities` | `view_owned_activity` | Promoter |
| `GET` | `/activities/{id}` | `view_owned_activity` | Promoter |
| `GET` | `/activities/{id}/history` | `view_owned_activity` | Promoter |
| `GET` | `/activities/{id}/documents` | `view_owned_activity` | Promoter |
| `PUT` | `/activities/{id}/status` | `manage_security` | SecurityOfficer |
| `POST` | `/activities/{id}/reject` | `reject_approval` | SecurityOfficer |
| `POST` | `/activities/{id}/force-cancel` | `force_cancel` | AdminStaff |
| `POST` | `/activities/{id}/force-postpone` | `force_postpone` | AdminStaff |
| `GET` | `/activities/{id}/filing/validate` | `pack_filing` | SecurityOfficer |
| `POST` | `/activities/{id}/filing/pack` | `pack_filing` | SecurityOfficer |
| `POST` | `/activities/{id}/filing/handover` | `pack_filing` | SecurityOfficer |
| `GET` | `/dashboard` | `view_dashboard` | AdminStaff |
| `GET` | `/dashboard/activities/{id}` | `view_dashboard` | AdminStaff |
| `POST` | `/dashboard/reports/monthly` | `export_report` | AdminStaff |

---

## 权限校验链路

```
请求 (Bearer token)
  │
  ▼
get_current_user (app/deps.py)
  解码 JWT → 查 users 表 → 返回 User 对象
  │
  ▼
get_user_permissions (app/rbac.py:13)
  SELECT permissions.name
  FROM permissions
    JOIN role_permissions ON role_permissions.permission_id = permissions.id
    JOIN user_roles ON user_roles.role_id = role_permissions.role_id
  WHERE user_roles.user_id = :user_id
  → 返回 {"create_activity", "upload_plan", ...}
  │
  ▼
require_permission("create_activity") (app/rbac.py:26)
  if "create_activity" not in permissions_set → 403 "缺少权限: create_activity"
  else → 通过
```

所有权限检查在路由层通过 `Depends(require_permission(...))` 完成，服务层不做角色/权限判断。

---

## 角色申请流程

```
用户注册 → 无角色 → GET /auth/me 返回 pending_role_request=null
  │
  ▼
POST /auth/me/role-request {role_id} → status=pending
  │
  ▼
SuperAdmin / AdminStaff:
  GET /admin/role-requests → 待审批列表
  │
  ├─ POST /admin/role-requests/{id}/approve → INSERT user_roles → 权限生效
  └─ POST /admin/role-requests/{id}/reject   → status=rejected（含驳回原因）
```

约束：
- 每个用户同时只能有 1 个 `pending` 申请
- 不能申请 SuperAdmin 角色
- 管理员审批后即时生效（INSERT user_roles），无需用户重新登录

---

## 已知 Gap

### 定义了但未使用的权限（7 项）

以下权限存在于 `init-scripts/03-rbac-tables.sql` 种子数据中，但没有任何路由通过 `require_permission` 校验它们。可能原因：对应功能尚未实现，或实现在路由层用了其他权限名。

| 权限 | 角色 |
|------|------|
| `upload_plan` | Promoter |
| `upload_security_material` | SecurityOfficer |
| `audit_material` | SecurityOfficer |
| `sign_document` | SecurityOfficer |
| `confirm_approval` | SecurityOfficer |
| `upload_approval` | GovLiaison |
| `update_approval_status` | GovLiaison |

### 安保部负责人（计划中）

UML 文档中"安保部负责人"概念尚未在代码中有对应角色（`manager_id` 字段为死代码）。将在后续分支 `feat/security-manager` 实现。
