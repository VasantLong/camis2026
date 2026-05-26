-- ============================================================
-- 文档表适配：添加 activity_id 关联
-- ============================================================

ALTER TABLE documents ADD COLUMN IF NOT EXISTS activity_id UUID REFERENCES activities(id);
CREATE INDEX IF NOT EXISTS idx_documents_activity ON documents(activity_id);
