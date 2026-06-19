"""Persist and load FCM tokens per alarm system so push works after backend restart."""
from typing import List, Optional

from db import connectToDB


def save_fcm_token(alarm_system_id: Optional[int], token: str, user_id: Optional[int] = None) -> bool:
    """Register or update a device token. alarm_system_id can be null until the user is linked to a warehouse."""
    conn = connectToDB.connectToDB()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM fcm_tokens WHERE token = %s", (token,))
        if user_id is not None:
            try:
                cur.execute(
                    "INSERT INTO fcm_tokens (token, alarm_system_id, user_id) VALUES (%s, %s, %s)",
                    (token, alarm_system_id, user_id),
                )
            except Exception:
                cur.execute(
                    "INSERT INTO fcm_tokens (token, alarm_system_id) VALUES (%s, %s)",
                    (token, alarm_system_id),
                )
        else:
            cur.execute(
                "INSERT INTO fcm_tokens (token, alarm_system_id) VALUES (%s, %s)",
                (token, alarm_system_id),
            )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"FCM token save failed (table may not exist): {e}")
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_fcm_tokens(alarm_system_id: int) -> List[str]:
    """Return all FCM tokens registered for this alarm system."""
    conn = connectToDB.connectToDB()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT token FROM fcm_tokens WHERE alarm_system_id = %s", (alarm_system_id,))
        return [row[0] for row in cur.fetchall()]
    except Exception as e:
        print(f"FCM token load failed (table may not exist): {e}")
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass


def delete_fcm_token(token: str) -> bool:
    """Delete one FCM token row. Useful for pruning invalid/unregistered tokens."""
    conn = connectToDB.connectToDB()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM fcm_tokens WHERE token = %s", (token,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"delete_fcm_token failed: {e}")
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_fcm_tokens_excluding_contractor(alarm_system_id: int) -> List[str]:
    """
    Tokens for sensor/door push notifications. Excludes devices registered to users
    with warehouse_role = contractor (they should not receive sensor-triggered pushes).
    Tokens without user_id (legacy) are still included.
    """
    conn = connectToDB.connectToDB()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT f.token
                FROM fcm_tokens f
                LEFT JOIN user_table u ON u.id = f.user_id
                                WHERE (
                                        f.alarm_system_id = %s
                                        OR (f.user_id IS NOT NULL AND u.alarm_system_id = %s)
                                )
                  AND (
                    f.user_id IS NULL
                    OR COALESCE(u.warehouse_role, 'admin') <> 'contractor'
                  )
                """,
                                (alarm_system_id, alarm_system_id),
            )
        except Exception:
            conn.rollback()
            return get_fcm_tokens(alarm_system_id)
        return [row[0] for row in cur.fetchall()]
    except Exception as e:
        print(f"get_fcm_tokens_excluding_contractor: {e}")
        return get_fcm_tokens(alarm_system_id)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_fcm_tokens_for_users(alarm_system_id: int, user_ids: List[int]) -> List[str]:
    """Tokens for specific users in this warehouse (for targeted admin/supervisor notifications)."""
    if not user_ids:
        return []
    conn = connectToDB.connectToDB()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        try:
            placeholders = ",".join(["%s"] * len(user_ids))
            cur.execute(
                f"""
                SELECT token FROM fcm_tokens
                WHERE alarm_system_id = %s AND user_id IN ({placeholders})
                """,
                (alarm_system_id, *user_ids),
            )
        except Exception:
            conn.rollback()
            return get_fcm_tokens(alarm_system_id)
        return [row[0] for row in cur.fetchall()]
    except Exception as e:
        print(f"get_fcm_tokens_for_users: {e}")
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_fcm_tokens_by_user_warehouse_link(alarm_system_id: int) -> List[str]:
    """
    Fallback token lookup for one-off notifications.
    Returns tokens for users currently linked to the given warehouse, regardless of
    the alarm_system_id stored in fcm_tokens (helps if rows became stale after re-linking users).
    """
    conn = connectToDB.connectToDB()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT f.token
            FROM fcm_tokens f
            JOIN user_table u ON u.id = f.user_id
            WHERE u.alarm_system_id = %s
            """,
            (alarm_system_id,),
        )
        return [row[0] for row in cur.fetchall()]
    except Exception as e:
        print(f"get_fcm_tokens_by_user_warehouse_link: {e}")
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass
