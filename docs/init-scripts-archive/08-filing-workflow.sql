-- ============================================================
-- 备案工作流：material_audits 表 + key_materials 扩展
-- 对应决策：CONTEXT.md (MaterialAudit), feat/filing-workflow
-- ============================================================

-- 材料审核记录表
CREATE TABLE IF NOT EXISTS material_audits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    material_id UUID NOT NULL REFERENCES key_materials(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    action VARCHAR(32) NOT NULL,         -- 'sign' | 'audit'
    conclusion VARCHAR(32),              -- NULL for sign; 'qualified'/'unqualified' for audit
    opinion TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- key_materials 加审核轮次
ALTER TABLE key_materials ADD COLUMN IF NOT EXISTS audit_round INTEGER NOT NULL DEFAULT 0;

-- key_materials 加签署状态
ALTER TABLE key_materials ADD COLUMN IF NOT EXISTS sign_status VARCHAR(32) NOT NULL DEFAULT 'unsigned';
