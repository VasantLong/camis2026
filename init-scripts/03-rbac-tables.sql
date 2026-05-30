-- ============================================================
-- RBAC 表 + 种子数据
-- 对应决策: docs/adr/0002.md
-- ============================================================

-- 角色
CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(64) NOT NULL UNIQUE,
    description VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 权限
CREATE TABLE IF NOT EXISTS permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(128) NOT NULL UNIQUE,
    resource VARCHAR(128) NOT NULL,
    action VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 用户 ↔ 角色
CREATE TABLE IF NOT EXISTS user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

-- 角色 ↔ 权限
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- ============================================================
-- 种子数据
-- ============================================================

-- 角色
INSERT INTO roles (name, description) VALUES
    ('Promoter', '宣策部人员 — 创建立项、编制活动方案'),
    ('SecurityOfficer', '安保部人员 — 编制安保方案、审核材料、确认审批结果'),
    ('AdminStaff', '行政部人员 — 监控活动面板、强制变更状态、归档'),
    ('GovLiaison', '政府对接人员 — 上传批文、标注审批结果')
ON CONFLICT (name) DO NOTHING;

-- 权限
INSERT INTO permissions (name, resource, action) VALUES
    -- Promoter
    ('create_activity', 'activities', 'create'),
    ('upload_plan', 'activities', 'upload_plan'),
    ('view_owned_activity', 'activities', 'view_owned'),
    ('submit_plan', 'activities', 'submit_plan'),

    -- SecurityOfficer
    ('manage_security', 'activities', 'manage_security'),
    ('review_security_plan', 'activities', 'review_security_plan'),
    ('upload_security_material', 'documents', 'upload'),
    ('audit_material', 'materials', 'audit'),
    ('sign_document', 'documents', 'sign'),
    ('confirm_approval', 'activities', 'confirm_approval'),
    ('reject_approval', 'activities', 'reject_approval'),
    ('pack_filing', 'filing', 'pack'),

    -- AdminStaff
    ('view_dashboard', 'dashboard', 'view'),
    ('force_cancel', 'activities', 'force_cancel'),
    ('force_postpone', 'activities', 'force_postpone'),
    ('export_report', 'dashboard', 'export_report'),

    -- GovLiaison
    ('upload_approval', 'documents', 'upload_approval'),
    ('update_approval_status', 'activities', 'update_approval_status')
ON CONFLICT (name) DO NOTHING;

-- 角色 ↔ 权限 映射
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'Promoter' AND p.name IN (
    'create_activity', 'upload_plan', 'view_owned_activity', 'submit_plan'
)
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'SecurityOfficer' AND p.name IN (
    'view_owned_activity', 'upload_security_material', 'sign_document', 'pack_filing',
    'manage_security'
)
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'SecurityManager' AND p.name IN (
    'view_owned_activity', 'manage_security', 'reject_approval',
    'confirm_approval', 'force_cancel', 'force_postpone',
    'view_dashboard', 'export_report'
)
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'AdminManager' AND p.name IN (
    'view_owned_activity', 'view_dashboard', 'export_report',
    'force_cancel', 'force_postpone', 'manage_security'
)
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
WHERE r.name = 'SuperAdmin'
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'AdminStaff' AND p.name IN (
    'view_owned_activity', 'view_dashboard', 'force_cancel', 'force_postpone', 'export_report'
)
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'GovLiaison' AND p.name IN (
    'view_owned_activity', 'upload_approval', 'update_approval_status', 'audit_material'
)
ON CONFLICT DO NOTHING;
