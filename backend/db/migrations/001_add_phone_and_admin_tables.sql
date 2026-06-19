-- Run this on existing DBs that were created before admin/roles feature.
-- Adds phone and role to user_table and creates sensor_labels + device_last_seen.

ALTER TABLE user_table ADD COLUMN IF NOT EXISTS phone VARCHAR(30);
ALTER TABLE user_table ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'user';
-- If role already existed without a default, set it (no-op if default already set)
ALTER TABLE user_table ALTER COLUMN role SET DEFAULT 'user';

CREATE TABLE IF NOT EXISTS sensor_labels (
  alarm_system_id INT NOT NULL REFERENCES alarm_system_table (alarm_system_id) ON DELETE CASCADE,
  position INT NOT NULL,
  label TEXT NOT NULL,
  PRIMARY KEY (alarm_system_id, position)
);

CREATE TABLE IF NOT EXISTS device_last_seen (
  microcontroller_id INT PRIMARY KEY REFERENCES microcontroller (microcontroller_id) ON DELETE CASCADE,
  last_seen DOUBLE PRECISION NOT NULL
);
