-- ============================================================
-- SuperAdmin 角色 + 角色申请表
-- 对应决策: docs/rbac.md
-- ============================================================

-- 新增权限：管理用户
INSERT INTO permissions (name, resource, action) VALUES
    ('manage_users', 'users', 'manage')
ON CONFLICT (name) DO NOTHING;

-- 新增角色：超级管理员
INSERT INTO roles (name, description) VALUES
    ('SuperAdmin', '超级管理员 — 管理用户角色、系统配置')
ON CONFLICT (name) DO NOTHING;

-- SuperAdmin ← manage_users
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'SuperAdmin' AND p.name IN ('manage_users')
ON CONFLICT DO NOTHING;

-- AdminStaff ← manage_users（行政部也可管理用户）
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'AdminStaff' AND p.name IN ('manage_users')
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
