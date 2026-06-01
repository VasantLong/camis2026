-- ============================================================
-- 通知关联引用：添加 reference_id 和 reference_type
-- ============================================================

ALTER TABLE notifications ADD COLUMN IF NOT EXISTS reference_id UUID;
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS reference_type VARCHAR(32);
