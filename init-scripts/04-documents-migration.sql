-- ============================================================
-- 文档表适配：支持关联 activity_id
-- documents 表当前通过 project_id 关联 projects，
-- 需要新增 activity_id 以适配活动审批域
-- ============================================================

-- 添加 activity_id 列（可空，兼容已有 project_id 数据）
ALTER TABLE documents ADD COLUMN IF NOT EXISTS activity_id UUID REFERENCES activities(id);

-- 索引
CREATE INDEX IF NOT EXISTS idx_documents_activity ON documents(activity_id);

-- project_id 改为可空，新文档可仅关联 activity_id
ALTER TABLE documents ALTER COLUMN project_id DROP NOT NULL;

-- 备注：
-- - project_id 暂时保留，待前端适配完成后废弃
-- - 新上传的文档应关联 activity_id
