from typing import List, Dict, Optional, Sequence

import psycopg2

from db import connectToDB


def save_event(event_dict: Dict, alarm_system_id: Optional[int], was_armed: bool) -> None:
    """
    Persist a single sensor event to the database.

    event_dict is the validated payload from ValidateData plus a server-side timestamp.
    """
    if alarm_system_id is None:
        # If we somehow don't know which alarm system this belongs to, skip persisting.
        return

    conn = connectToDB.connectToDB()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sensor_events (
                id BIGSERIAL PRIMARY KEY,
                alarm_system_id INT NOT NULL REFERENCES alarm_system_table (alarm_system_id) ON DELETE CASCADE,
                device_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                count INT NOT NULL,
                timestamp DOUBLE PRECISION NOT NULL,
                was_armed BOOLEAN NOT NULL
            );
            """,
        )
        val = event_dict.get("value")
        val_sql = float(val) if val is not None else None
        cur.execute(
            """
            INSERT INTO sensor_events (
                alarm_system_id, device_id, event_type, count, timestamp, was_armed, value
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                alarm_system_id,
                event_dict.get("device_id"),
                event_dict.get("event_type"),
                int(event_dict.get("count") or 0),
                float(event_dict.get("timestamp") or 0.0),
                bool(was_armed),
                val_sql,
            ),
        )
        conn.commit()
    except Exception as e:
        # For now just log; API should still succeed so the in-memory/event-stream behaviour is unchanged.
        print(f"Event persist failed: {e}")
        conn.rollback()
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_events_for_system(
    alarm_system_id: int,
    armed_only: bool = True,
    limit: int = 500,
    exclude_event_types: Optional[Sequence[str]] = None,
) -> List[Dict]:
    """
    Load historical events for a given alarm system, newest first.

    If armed_only is True, only return events that were recorded while the system was armed
    (matches previous in-memory behaviour).
    exclude_event_types: e.g. ["current_power_usage"] to keep history focused on doors.
    """
    conn = connectToDB.connectToDB()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sensor_events (
                id BIGSERIAL PRIMARY KEY,
                alarm_system_id INT NOT NULL REFERENCES alarm_system_table (alarm_system_id) ON DELETE CASCADE,
                device_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                count INT NOT NULL,
                timestamp DOUBLE PRECISION NOT NULL,
                was_armed BOOLEAN NOT NULL
            );
            """,
        )
        where = ["alarm_system_id = %s"]
        params: List = [alarm_system_id]
        if armed_only:
            where.append("was_armed = TRUE")
        if exclude_event_types:
            where.append("NOT (event_type = ANY(%s))")
            params.append(list(exclude_event_types))
        params.append(limit)
        sql = f"""
            SELECT device_id, event_type, count, timestamp, value
            FROM sensor_events
            WHERE {' AND '.join(where)}
            ORDER BY timestamp DESC
            LIMIT %s
        """
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        events: List[Dict] = []
        for row in rows:
            device_id, event_type, count, timestamp, value = row[0], row[1], row[2], row[3], row[4]
            d = {
                "device_id": device_id,
                "event_type": event_type,
                "count": int(count),
                "timestamp": float(timestamp),
            }
            if value is not None:
                d["value"] = float(value)
            events.append(d)
        return events
    except psycopg2.errors.UndefinedTable:
        # If table does not exist yet, just behave as "no history"
        conn.rollback()
        return []
    except Exception as e:
        print(f"Event history load failed: {e}")
        conn.rollback()
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_power_samples_for_system(alarm_system_id: int, limit: int = 120) -> List[Dict]:
    """
    Recent power samples for charting (mA). Newest rows limited, returned oldest-first for time series.
    """
    conn = connectToDB.connectToDB()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT device_id, timestamp, COALESCE(value, 0.0)
            FROM sensor_events
            WHERE alarm_system_id = %s
              AND event_type = 'current_power_usage'
            ORDER BY timestamp DESC
            LIMIT %s
            """,
            (alarm_system_id, limit),
        )
        rows = cur.fetchall()
        chronological = list(reversed(rows))
        return [
            {
                "device_id": r[0],
                "timestamp": float(r[1]),
                "value_ma": float(r[2]),
            }
            for r in chronological
        ]
    except Exception as e:
        print(f"get_power_samples_for_system failed: {e}")
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass

