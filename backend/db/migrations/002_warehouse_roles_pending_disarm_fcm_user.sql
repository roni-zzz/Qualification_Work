-- Per-warehouse roles, contractor disarm approvals, FCM tokens scoped to user (run via ensure_schema on startup too).

ALTER TABLE user_table ADD COLUMN IF NOT EXISTS warehouse_role VARCHAR(20) DEFAULT 'admin';
ALTER TABLE user_table ALTER COLUMN warehouse_role SET DEFAULT 'admin';

CREATE TABLE IF NOT EXISTS pending_disarm (
    id TEXT PRIMARY KEY,
    alarm_system_id INT NOT NULL REFERENCES alarm_system_table (alarm_system_id) ON DELETE CASCADE,
    requested_by_user_id INT NOT NULL REFERENCES user_table (id) ON DELETE CASCADE,
    created_at DOUBLE PRECISION NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
);

ALTER TABLE fcm_tokens ADD COLUMN IF NOT EXISTS user_id INT REFERENCES user_table (id) ON DELETE SET NULL;
