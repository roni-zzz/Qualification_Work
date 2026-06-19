"""Sensor display names per warehouse (admin-editable; no physical location)."""
from typing import List
from db import connectToDB


def get_sensor_labels(alarm_system_id: int) -> List[str]:
    """Return ordered list of sensor labels for this warehouse. Positions 0,1,2,..."""
    conn = connectToDB.connectToDB()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT label FROM sensor_labels
            WHERE alarm_system_id = %s
            ORDER BY position
            """,
            (alarm_system_id,),
        )
        return [row[0] for row in cur.fetchall()]
    except Exception:
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass


def set_sensor_labels(alarm_system_id: int, labels: List[str]) -> bool:
    """
    Replace sensor labels for this warehouse.
    Position 0 = first reed (e.g. D4), position 1 = second reed (e.g. D14).
    Up to two entries; empty strings skip that position.
    """
    conn = connectToDB.connectToDB()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM sensor_labels WHERE alarm_system_id = %s",
            (alarm_system_id,),
        )
        for pos in range(2):
            if pos >= len(labels):
                break
            label = (labels[pos] or "").strip()
            if label:
                cur.execute(
                    "INSERT INTO sensor_labels (alarm_system_id, position, label) VALUES (%s, %s, %s)",
                    (alarm_system_id, pos, label),
                )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"set_sensor_labels failed: {e}")
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass
