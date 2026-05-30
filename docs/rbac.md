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
| `role_requests` | 角色申请（待审批/已批准/已驳回） | `id` (UUID) |

一个用户可拥有多个角色，一个角色可拥有多个权限。角色 UUID 由 `uuid_generate_v4()` 在 INSERT 时生成，引用角色时按 `name` 查询。

---

## 角色总览

| 角色 | 部门 | 职责 | 权限数 |
|------|------|------|--------|
| **SuperAdmin** | 系统 | 全权限（用户管理、系统配置） | 全部 |
| **AdminManager** | 行政部 | 审批角色申请、强制变更、Dashboard | 7 |
| **SecurityManager** | 安保部 | 审核安保方案、状态流转、确认审批、驳回 | 8 |
| **AdminStaff** | 行政部 | 监控活动面板、强制变更状态、Dashboard | 5 |
| **SecurityOfficer** | 安保部 | 上传材料、电子签署、打包备案、状态流转 | 5 |
| **Promoter** | 宣策部 | 创建立项、编制活动方案、提交安保审核 (submit_plan) | 4 |
| **GovLiaison** | 政府对接 | 上传批文、审查材料合规性、标注审批结果 | 4 |

---

## 权限全量（21 项）

### SuperAdmin（全部权限）

拥有系统中所有权限（通过 `CROSS JOIN` 分配），包括所有其他角色权限的超集。

### Promoter（4 项）

| 权限名 | 资源 | 操作 | 对应用例 |
|--------|------|------|---------|
| `create_activity` | activities | create | 创建活动 |
| `submit_plan` | activities | submit_plan | 提交到安保方案设计 |
| `upload_plan` | activities | upload_plan | 上传活动方案文件 |
| `view_owned_activity` | activities | view_owned | 查看自己创建的活动列表和详情 |

### SecurityManager（7 项）

安保部负责人，拥有 SecurityOfficer 全部权限 + 管理权限。

| 权限名 | 资源 | 操作 | 对应用例 |
|--------|------|------|---------|
| `view_owned_activity` | activities | view_owned | 查看活动列表和详情 |
| `manage_security` | activities | manage_security | 状态流转 |
| `review_security_plan` | activities | review_security_plan | 审核安保方案（通过/打回） |
| `confirm_approval` | activities | confirm_approval | 确认政府审批结果 |
| `reject_approval` | activities | reject_approval | 驳回审批结果 |
| `upload_security_material` | documents | upload | 上传安保材料 |
| `pack_filing` | filing | pack | 校验材料、打包、纸质交接 |

### SecurityOfficer（5 项）

| 权限名 | 资源 | 操作 | 对应用例 |
|--------|------|------|---------|
| `view_owned_activity` | activities | view_owned | 查看活动列表和详情 |
| `manage_security` | activities | manage_security | 状态流转（签署完成） |
| `upload_security_material` | documents | upload | 上传安保材料 |
| `sign_document` | documents | sign | 对上传的材料电子签署 |
| `pack_filing` | filing | pack | 校验材料、打包、纸质交接 |

### AdminManager（5 项）

行政部负责人，拥有 AdminStaff 全部权限 + 角色审批。

| 权限名 | 资源 | 操作 | 对应用例 |
|--------|------|------|---------|
| `view_dashboard` | dashboard | view | 查看活动面板、活动详情统计 |
| `force_cancel` | activities | force_cancel | 强制取消活动 |
| `force_postpone` | activities | force_postpone | 强制延期活动 |
| `export_report` | dashboard | export_report | 导出月报 |
| `manage_users` | users | manage | 查看/审批/驳回角色申请 |

### AdminStaff（4 项）

普通行政人员，不包含角色审批权限。

| 权限名 | 资源 | 操作 | 对应用例 |
|--------|------|------|---------|
| `view_dashboard` | dashboard | view | 查看活动面板、活动详情统计 |
| `force_cancel` | activities | force_cancel | 强制取消活动 |
| `force_postpone` | activities | force_postpone | 强制延期活动 |
| `export_report` | dashboard | export_report | 导出月报 |

### GovLiaison（4 项）

| 权限名 | 资源 | 操作 | 对应用例 |
|--------|------|------|---------|
| `view_owned_activity` | activities | view_owned | 查看备案材料已交接的活动 |
| `audit_material` | materials | audit | 审查关键材料合规性 |
| `upload_approval` | documents | upload_approval | 上传政府批文 |
| `update_approval_status` | activities | update_approval_status | 标记审批结果（通过/需补充/不通过） |

---

## 路由权限映射（实际生效的 23 个端点）

| 方法 | 路径 | 权限 | 角色 |
|------|------|------|------|
| `POST` | `/auth/me/role-request` | 登录即可 | 任意用户 |
| `GET` | `/admin/role-requests` | `manage_users` | SuperAdmin / AdminManager |
| `POST` | `/admin/role-requests/{id}/approve` | `manage_users` | SuperAdmin / AdminManager |
| `POST` | `/admin/role-requests/{id}/reject` | `manage_users` | SuperAdmin / AdminManager |
| `GET` | `/admin/users` | `administer_users` | SuperAdmin |
| `GET` | `/admin/users/{id}` | `administer_users` | SuperAdmin |
| `PUT` | `/admin/users/{id}/roles` | `administer_users` | SuperAdmin |
| `PATCH` | `/admin/users/{id}/status` | `administer_users` | SuperAdmin |
| `POST` | `/admin/users/{id}/archive` | `administer_users` | SuperAdmin |
| `POST` | `/admin/users/{id}/unarchive` | `administer_users` | SuperAdmin |
| `POST` | `/activities` | `create_activity` | Promoter |
| `GET` | `/activities` | `view_owned_activity` | Promoter |
| `GET` | `/activities/{id}` | `view_owned_activity` | Promoter |
| `GET` | `/activities/{id}/history` | `view_owned_activity` | 所有 |
| `GET` | `/activities/{id}/documents` | `view_owned_activity` | 所有 |
| `GET` | `/activities/{id}/security-plan` | `view_owned_activity` | 所有 |
| `GET` | `/activities/{id}/filing/status` | 登录即可 | 所有 |
| `PUT` | `/activities/{id}/status` | `manage_security` 或 `audit_material`¹ | SecurityManager / GovLiaison |
| `POST` | `/activities/{id}/reject` | `reject_approval` | SecurityManager |
| `POST` | `/activities/{id}/force-cancel` | `force_cancel` | AdminStaff/AdminManager |
| `POST` | `/activities/{id}/force-postpone` | `force_postpone` | AdminStaff/AdminManager |
| `GET` | `/activities/{id}/filing/validate` | `pack_filing` | SecurityOfficer/SecurityManager |
| `POST` | `/activities/{id}/filing/pack` | `pack_filing` | SecurityOfficer/SecurityManager |
| `POST` | `/activities/{id}/filing/handover` | `pack_filing` | SecurityOfficer/SecurityManager |
| `GET` | `/dashboard` | `view_dashboard` | AdminStaff/AdminManager |
| `GET` | `/dashboard/activities/{id}` | `view_dashboard` | AdminStaff |
| `POST` | `/dashboard/reports/monthly` | `export_report` | AdminStaff |

> ¹ `PUT /activities/{id}/status` 在目标状态为"审批通过-待举办"时，额外要求 `confirm_approval` 权限。

---

## 活动可见性

活动列表和详情按角色自动过滤：

| 角色 | 可见活动 | 过滤方式 |
|------|---------|---------|
| Promoter | 自己创建的待设计方案 | `owner_id = 自己 AND status = 待设计方案` |
| SecurityOfficer | 待安保方案设计 | `status = 待安保方案设计` |
| SecurityManager | 安保相关流程 | `status IN (待安保方案设计, 待备案申请, 备案材料已交接, 审批通过, 待补充备案材料)` |
| GovLiaison | 待处理的审批活动 | `status = 备案材料已交接` |
| SuperAdmin | 全部活动 | 无过滤 |
| AdminStaff/AdminManager | 全部活动（只读） | 无过滤 |

多角色用户取最大可见范围（如 Promoter + AdminStaff → 全部）。

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

### 定义了但未使用的权限（4 项）

| 权限 | 角色 |
|------|------|
| `upload_plan` | Promoter |
| `upload_security_material` | SecurityOfficer |
| `upload_approval` | GovLiaison |
| `update_approval_status` | GovLiaison |

> `sign_document` 已在 filings router 中激活。
