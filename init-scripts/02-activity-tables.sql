-- ============================================================
-- 活动审批域核心表
-- 对应实体模型: docs/camis-UML.md §实体模型（纯数据载体）
-- ============================================================

-- 活动项目（聚合根）
CREATE TABLE IF NOT EXISTS activities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(128) NOT NULL,
    estimated_time TIMESTAMPTZ NOT NULL,
    location VARCHAR(512) NOT NULL,
    sponsor VARCHAR(255) NOT NULL,
    deadline TIMESTAMPTZ NOT NULL,
    status VARCHAR(64) NOT NULL DEFAULT '待设计方案',
    owner_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 活动方案
CREATE TABLE IF NOT EXISTS activity_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    activity_id UUID NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    content TEXT,
    attachment_url VARCHAR(2048),
    submit_time TIMESTAMPTZ,
    designer_id UUID NOT NULL REFERENCES users(id),
    is_overdue BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 安保方案
CREATE TABLE IF NOT EXISTS security_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    activity_id UUID NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    risk_level VARCHAR(64),
    audit_status VARCHAR(64) NOT NULL DEFAULT '待编制',
    manager_id UUID REFERENCES users(id),
    sign_time TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 备案材料
CREATE TABLE IF NOT EXISTS filing_docs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    activity_id UUID NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    is_qualified BOOLEAN NOT NULL DEFAULT FALSE,
    handover_status VARCHAR(64) NOT NULL DEFAULT '未交接',
    generated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 政府批文
CREATE TABLE IF NOT EXISTS approval_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    activity_id UUID NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    liaison_id UUID NOT NULL REFERENCES users(id),
    approval_status VARCHAR(64) NOT NULL,
    attachment_url VARCHAR(2048),
    approval_date TIMESTAMPTZ,
    rectification_opinion TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 活动实施记录
CREATE TABLE IF NOT EXISTS implementation_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    activity_id UUID NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    admin_id UUID NOT NULL REFERENCES users(id),
    progress TEXT,
    change_status VARCHAR(64) NOT NULL DEFAULT '正常',
    change_reason TEXT,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 关键材料
CREATE TABLE IF NOT EXISTS key_materials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    is_qualified BOOLEAN NOT NULL DEFAULT FALSE,
    opinion TEXT,
    upload_time TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 关键材料 ↔ 安保方案 (多对多)
CREATE TABLE IF NOT EXISTS security_plan_materials (
    security_plan_id UUID NOT NULL REFERENCES security_plans(id) ON DELETE CASCADE,
    material_id UUID NOT NULL REFERENCES key_materials(id) ON DELETE CASCADE,
    PRIMARY KEY (security_plan_id, material_id)
);

-- 关键材料 ↔ 备案材料 (多对多)
CREATE TABLE IF NOT EXISTS filing_doc_materials (
    filing_doc_id UUID NOT NULL REFERENCES filing_docs(id) ON DELETE CASCADE,
    material_id UUID NOT NULL REFERENCES key_materials(id) ON DELETE CASCADE,
    PRIMARY KEY (filing_doc_id, material_id)
);

-- 活动规则
CREATE TABLE IF NOT EXISTS activity_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_type VARCHAR(128) NOT NULL,
    effective_time TIMESTAMPTZ,
    effective_reason TEXT,
    resolve_status VARCHAR(64) NOT NULL DEFAULT '生效中',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 活动 ↔ 规则 (多对多)
CREATE TABLE IF NOT EXISTS activity_rule_targets (
    activity_id UUID NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    rule_id UUID NOT NULL REFERENCES activity_rules(id) ON DELETE CASCADE,
    PRIMARY KEY (activity_id, rule_id)
);

-- 活动状态流转日志 (用于 GET /activities/{id}/history)
CREATE TABLE IF NOT EXISTS activity_status_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    activity_id UUID NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    from_status VARCHAR(64),
    to_status VARCHAR(64) NOT NULL,
    operator_id UUID NOT NULL REFERENCES users(id),
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- 索引
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_activities_status ON activities(status);
CREATE INDEX IF NOT EXISTS idx_activities_owner ON activities(owner_id);
CREATE INDEX IF NOT EXISTS idx_activities_location_time ON activities(location, estimated_time);

CREATE INDEX IF NOT EXISTS idx_plans_activity ON activity_plans(activity_id);
CREATE INDEX IF NOT EXISTS idx_security_activity ON security_plans(activity_id);
CREATE INDEX IF NOT EXISTS idx_filing_activity ON filing_docs(activity_id);
CREATE INDEX IF NOT EXISTS idx_approval_activity ON approval_records(activity_id);
CREATE INDEX IF NOT EXISTS idx_impl_activity ON implementation_records(activity_id);

CREATE INDEX IF NOT EXISTS idx_status_log_activity ON activity_status_log(activity_id);
CREATE INDEX IF NOT EXISTS idx_status_log_time ON activity_status_log(created_at);

-- ============================================================
-- updated_at 触发器
-- ============================================================

CREATE TRIGGER trg_activities_updated_at
    BEFORE UPDATE ON activities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_plans_updated_at
    BEFORE UPDATE ON activity_plans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_security_updated_at
    BEFORE UPDATE ON security_plans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_filing_updated_at
    BEFORE UPDATE ON filing_docs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_impl_updated_at
    BEFORE UPDATE ON implementation_records
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_rules_updated_at
    BEFORE UPDATE ON activity_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
