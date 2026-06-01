-- ============================================================
-- 活动主办方联系信息
-- ============================================================

ALTER TABLE activities ADD COLUMN IF NOT EXISTS sponsor_contact VARCHAR(128);
ALTER TABLE activities ADD COLUMN IF NOT EXISTS sponsor_phone VARCHAR(64);
