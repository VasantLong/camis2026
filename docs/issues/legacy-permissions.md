# 遗留权限清理

## 问题

GovLiaison 角色在数据库中被授予了 `upload_approval` 和 `update_approval_status` 两个权限，但这两个权限已无代码引用：

| 权限 | 旧用途 | 现状 |
|------|--------|------|
| `upload_approval` | UC5 上传政府批文 | 已由 `audit_material` 权限 + `create_approval_record()` 替代 |
| `update_approval_status` | UC6 登记审批结果 | UC6 已移除，审批状态变更已并入 `audit_material` + `transition()` |

两个权限出现在 GovLiaison 个人中心的"角色与权限"表格中，显示为英文原始标识。

来源：`migrations/versions/642e62051696_initial_baseline.py` 种子数据。

## 当前处理

前端 `PERMISSION_LABEL_MAP` 已将两个权限标记为"(已废弃)"，避免用户看到英文标识。

## 后续

- [ ] 创建 Alembic migration 从 `permissions` 表删除这两条记录
- [ ] 更新 `role_permissions` 关联表，移除 GovLiaison 对应的 `(role_id, permission_id)` 行
- [ ] 前端 `PERMISSION_LABEL_MAP` 同步移除废弃条目
