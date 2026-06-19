"""Update and query device last-seen timestamps for offline detection (admin)."""
import re
from typing import List, Tuple
from db import connectToDB


def update_last_seen(device_id: str, timestamp: float) -> None:
    """Record that we received an event from this device (e.g. esp32_111 -> mc_id 111)."""
    match = re.match(r"^esp32_(\d+)$", (device_id or "").strip())
    if not match:
        return
    mc_id = int(match.group(1))
    conn = connectToDB.connectToDB()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO device_last_seen (microcontroller_id, last_seen)
            VALUES (%s, %s)
            ON CONFLICT (microcontroller_id) DO UPDATE SET last_seen = EXCLUDED.last_seen
            """,
            (mc_id, timestamp),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"device_last_seen update failed: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_all_last_seen() -> List[Tuple[int, int, float]]:
    """Return (microcontroller_id, alarm_system_id, last_seen) for all devices that have a last_seen row."""
    conn = connectToDB.connectToDB()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT d.microcontroller_id, m.alarm_system_id, d.last_seen
            FROM device_last_seen d
            JOIN microcontroller m ON m.microcontroller_id = d.microcontroller_id
            ORDER BY d.last_seen DESC
            """
        )
        return list(cur.fetchall())
    except Exception as e:
        print(f"get_all_last_seen failed: {e}")
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_offline_devices(older_than_seconds: float = 600) -> List[Tuple[int, int, float]]:
    """
    Return list of (microcontroller_id, alarm_system_id, last_seen) for devices
    that have not been seen in older_than_seconds (default 10 min).
    """
    import time
    conn = connectToDB.connectToDB()
    try:
        cur = conn.cursor()
        cutoff = time.time() - older_than_seconds
        cur.execute(
            """
            SELECT d.microcontroller_id, m.alarm_system_id, d.last_seen
            FROM device_last_seen d
            JOIN microcontroller m ON m.microcontroller_id = d.microcontroller_id
            WHERE d.last_seen < %s
            ORDER BY d.last_seen ASC
            """,
            (cutoff,),
        )
        return list(cur.fetchall())
    except Exception as e:
        print(f"get_offline_devices failed: {e}")
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass
