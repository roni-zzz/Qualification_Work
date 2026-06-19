"""
Run admin/roles migration on the DB this app connects to (same connectToDB as the rest of the app).
Call once at startup so the table is updated even if the standalone migration script hit a different DB.
"""
from db import connectToDB


def ensure_user_table_phone_and_role():
    """Add phone and role columns to user_table if missing. Idempotent."""
    conn = None
    try:
        conn = connectToDB.connectToDB()
        cur = conn.cursor()
        cur.execute(
            "ALTER TABLE user_table ADD COLUMN IF NOT EXISTS phone VARCHAR(30)"
        )
        cur.execute(
            "ALTER TABLE user_table ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'user'"
        )
        cur.execute("ALTER TABLE user_table ALTER COLUMN role SET DEFAULT 'user'")
        conn.commit()
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"ensure_schema (user_table): {e}")
        return False
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def ensure_alarm_system_name():
    """Add display name column to alarm_system_table if missing. Idempotent."""
    conn = None
    try:
        conn = connectToDB.connectToDB()
        cur = conn.cursor()
        cur.execute(
            "ALTER TABLE alarm_system_table ADD COLUMN IF NOT EXISTS name VARCHAR(120)"
        )
        conn.commit()
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"ensure_schema (alarm_system name): {e}")
        return False
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def ensure_sensor_labels_and_device_last_seen():
    """Create sensor_labels and device_last_seen tables if missing. Idempotent."""
    conn = None
    try:
        conn = connectToDB.connectToDB()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sensor_labels (
                alarm_system_id INT NOT NULL REFERENCES alarm_system_table (alarm_system_id) ON DELETE CASCADE,
                position INT NOT NULL,
                label TEXT NOT NULL,
                PRIMARY KEY (alarm_system_id, position)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS device_last_seen (
                microcontroller_id INT PRIMARY KEY REFERENCES microcontroller (microcontroller_id) ON DELETE CASCADE,
                last_seen DOUBLE PRECISION NOT NULL
            )
        """)
        conn.commit()
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"ensure_schema (sensor_labels/device_last_seen): {e}")
        return False
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def ensure_sensor_events_value_column():
    """Add optional value column for power readings (mA). Idempotent."""
    conn = None
    try:
        conn = connectToDB.connectToDB()
        cur = conn.cursor()
        cur.execute(
            "ALTER TABLE sensor_events ADD COLUMN IF NOT EXISTS value DOUBLE PRECISION"
        )
        conn.commit()
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"ensure_schema (sensor_events.value): {e}")
        return False
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def ensure_warehouse_role_pending_disarm_fcm_user():
    """Ensure warehouse_role schema, migrate legacy home_role, pending_disarm table, fcm_tokens.user_id. Idempotent."""
    conn = None
    try:
        conn = connectToDB.connectToDB()
        cur = conn.cursor()
        cur.execute(
            """
            ALTER TABLE user_table ADD COLUMN IF NOT EXISTS warehouse_role VARCHAR(20) DEFAULT 'admin'
            """
        )
        # If legacy home_role exists, copy values into warehouse_role (only where warehouse_role is empty).
        cur.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'user_table' AND column_name = 'home_role'
            LIMIT 1
            """
        )
        if cur.fetchone():
            cur.execute(
                """
                UPDATE user_table
                SET warehouse_role = COALESCE(NULLIF(TRIM(home_role), ''), 'admin')
                WHERE COALESCE(TRIM(warehouse_role), '') = ''
                """
            )
            cur.execute("ALTER TABLE user_table DROP COLUMN IF EXISTS home_role")
        cur.execute("ALTER TABLE user_table ALTER COLUMN warehouse_role SET DEFAULT 'admin'")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_disarm (
                id TEXT PRIMARY KEY,
                alarm_system_id INT NOT NULL REFERENCES alarm_system_table (alarm_system_id) ON DELETE CASCADE,
                requested_by_user_id INT NOT NULL REFERENCES user_table (id) ON DELETE CASCADE,
                created_at DOUBLE PRECISION NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending'
            )
            """
        )
        cur.execute(
            "ALTER TABLE fcm_tokens ADD COLUMN IF NOT EXISTS user_id INT REFERENCES user_table (id) ON DELETE SET NULL"
        )
        try:
            cur.execute("ALTER TABLE fcm_tokens ALTER COLUMN alarm_system_id DROP NOT NULL")
        except Exception:
            conn.rollback()
            # Re-open transaction and continue if DB/schema variant doesn't support this yet.
            cur = conn.cursor()
        conn.commit()
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"ensure_schema (warehouse_role/pending_disarm/fcm): {e}")
        return False
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def run_startup_migration():
    """Call at app startup to ensure DB has phone, role, admin tables, and alarm_system name."""
    ensure_user_table_phone_and_role()
    ensure_alarm_system_name()
    ensure_sensor_labels_and_device_last_seen()
    ensure_sensor_events_value_column()
    ensure_warehouse_role_pending_disarm_fcm_user()
