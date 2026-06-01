-- ============================================================
-- 用户归档：添加归档原因与归档时间字段
-- 归档操作为不可逆封存，需记录凭证
-- ============================================================

ALTER TABLE users ADD COLUMN IF NOT EXISTS archive_reason TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;
