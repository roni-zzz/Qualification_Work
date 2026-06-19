--database name: alarm_system 

--User table:
CREATE TABLE user_table (
  id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  username VARCHAR(100) UNIQUE NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  alarm_system_id INT,
  password_hash TEXT NOT NULL,
  role VARCHAR(20) DEFAULT 'user',
  phone VARCHAR(30),
  CHECK (role IN ('admin', 'user'))
);

--Alarm system table
CREATE TABLE alarm_system_table (
  alarm_system_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  system_password_hash TEXT NOT NULL,
  armed BOOLEAN NOT NULL DEFAULT FALSE,
  paired BOOLEAN NOT NULL DEFAULT FALSE
);

--micro controller table
CREATE TABLE microcontroller (
  microcontroller_id INT PRIMARY KEY,
  alarm_system_id INT NOT NULL,
  current_state TEXT NOT NULL,
  FOREIGN KEY (alarm_system_id)
    REFERENCES alarm_system_table (alarm_system_id)
    ON DELETE CASCADE
);

-- FCM push tokens (one token per device; re-registering updates alarm_system_id)
CREATE TABLE IF NOT EXISTS fcm_tokens (
  token TEXT PRIMARY KEY,
  alarm_system_id INT NOT NULL,
  FOREIGN KEY (alarm_system_id) REFERENCES alarm_system_table (alarm_system_id) ON DELETE CASCADE
);

-- Historical sensor events (for per-user history views)
CREATE TABLE IF NOT EXISTS sensor_events (
  id BIGSERIAL PRIMARY KEY,
  alarm_system_id INT NOT NULL,
  device_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  count INT NOT NULL,
  timestamp DOUBLE PRECISION NOT NULL,
  was_armed BOOLEAN NOT NULL,
  FOREIGN KEY (alarm_system_id) REFERENCES alarm_system_table (alarm_system_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sensor_events_system_ts
  ON sensor_events (alarm_system_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_sensor_events_system_type_ts
  ON sensor_events (alarm_system_id, event_type, timestamp DESC);

-- Sensor display names per warehouse (admin sets these; no physical location stored)
CREATE TABLE IF NOT EXISTS sensor_labels (
  alarm_system_id INT NOT NULL REFERENCES alarm_system_table (alarm_system_id) ON DELETE CASCADE,
  position INT NOT NULL,
  label TEXT NOT NULL,
  PRIMARY KEY (alarm_system_id, position)
);

-- Last time we received an event from each device (for offline detection)
CREATE TABLE IF NOT EXISTS device_last_seen (
  microcontroller_id INT PRIMARY KEY REFERENCES microcontroller (microcontroller_id) ON DELETE CASCADE,
  last_seen DOUBLE PRECISION NOT NULL
);