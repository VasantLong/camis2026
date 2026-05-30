-- ============================================================
-- 用户归档：添加 is_archived 字段，替代硬删除
-- ============================================================

ALTER TABLE users ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT FALSE;
