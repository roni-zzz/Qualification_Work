import bcrypt

from db import connectToDB
import re

import psycopg2
from db import addAvailableSystems


def getCurrentAlarmSystemID(username: str) -> str | None:
    conn = connectToDB.connectToDB()
    cursor = conn.cursor()

    cursor.execute("SELECT alarm_system_id FROM user_table WHERE username = %s", (username,))
    row = cursor.fetchone()
    currentAlarmSystemID = row[0] if row else None

    conn.close()

    return currentAlarmSystemID


def get_username_by_user_id(user_id: int) -> str | None:
    """Return username for the given user (user_table.id). None if not found."""
    conn = connectToDB.connectToDB()
    if conn is None:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM user_table WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_alarm_system_id_by_user_id(user_id: int) -> int | None:
    """Return alarm_system_id for the given user (by user_table.id). None if not paired or not found."""
    conn = connectToDB.connectToDB()
    if conn is None:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT alarm_system_id FROM user_table WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else None
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_alarm_system_id_by_device_id(device_id: str) -> int | None:
    """
    Return alarm_system_id for the device (e.g. esp32_123456 -> lookup microcontroller_id 123456).
    None if device not registered or not found.
    """
    match = re.match(r"^esp32_(\d+)$", (device_id or "").strip())
    if not match:
        return None
    mc_id = int(match.group(1))
    try:
        conn = connectToDB.connectToDB()
    except Exception:
        # connectToDB raises on failure; do not crash API handlers (e.g. /api/events/ingest)
        return None
    if conn is None:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT alarm_system_id FROM microcontroller WHERE microcontroller_id = %s",
            (mc_id,),
        )
        row = cursor.fetchone()
        return int(row[0]) if row else None
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def ensure_user_has_alarm_system(user_id: int) -> int | None:
    """Return alarm_system_id for the user, creating and pairing one if they don't have one."""
    username = get_username_by_user_id(user_id)
    if not username:
        return None
    if get_alarm_system_id_by_user_id(user_id) is None:
        connectUserToSystem(username)
    return get_alarm_system_id_by_user_id(user_id)


def connectUserToSystem(user_id: int, system_password: str) -> bool:
    try:
        conn = connectToDB.connectToDB()
        cursor = conn.cursor()

        cursor.execute("SELECT alarm_system_id FROM user_table WHERE id = %s", (user_id,))
        user_row = cursor.fetchone()
        if not user_row:
            return False

        current_system_id = user_row[0]
        if current_system_id is not None:
            return False

        cursor.execute(
            """
            SELECT alarm_system_id, system_password_hash
            FROM alarm_system_table
            WHERE paired = FALSE
            """
        )
        candidates = cursor.fetchall()

        matched_system_id = None
        for alarm_system_id, password_hash in candidates:
            if bcrypt.checkpw(system_password.encode(), password_hash.encode()):
                matched_system_id = alarm_system_id
                break

        if matched_system_id is None:
            return False

        cursor.execute(
            """
            UPDATE user_table
            SET alarm_system_id = %s
            WHERE id = %s
            """,
            (matched_system_id, user_id),
        )
        cursor.execute(
            "UPDATE alarm_system_table SET paired = TRUE WHERE alarm_system_id = %s",
            (matched_system_id,),
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()
