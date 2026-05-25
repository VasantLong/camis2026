-- ============================================================
-- SuperAdmin + AdminManager 角色 + 角色申请表
-- 对应决策: docs/rbac.md
-- ============================================================

-- 新增权限
INSERT INTO permissions (name, resource, action) VALUES
    ('manage_users', 'users', 'manage'),
    ('administer_users', 'users', 'administer')
ON CONFLICT (name) DO NOTHING;

-- 新增角色
INSERT INTO roles (name, description) VALUES
    ('SuperAdmin', '超级管理员 — 用户 CRUD、系统配置'),
    ('AdminManager', '行政部负责人 — 审批角色申请、管理仪表盘')
ON CONFLICT (name) DO NOTHING;

-- SuperAdmin ← manage_users + administer_users
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'SuperAdmin' AND p.name IN ('manage_users', 'administer_users')
ON CONFLICT DO NOTHING;

-- AdminManager ← AdminStaff 全部权限 + manage_users
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'AdminManager' AND p.name IN (
    'manage_users', 'view_dashboard', 'force_cancel', 'force_postpone', 'export_report'
)
ON CONFLICT DO NOTHING;

-- ============================================================
-- 角色申请表
-- ============================================================

CREATE TABLE IF NOT EXISTS role_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id),
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    reviewer_id UUID REFERENCES users(id),
    reviewed_at TIMESTAMPTZ
);

-- 每个用户同时只能有一个待审批申请
CREATE UNIQUE INDEX IF NOT EXISTS idx_one_pending_per_user
    ON role_requests (user_id) WHERE status = 'pending';
