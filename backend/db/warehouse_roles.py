"""Per-warehouse roles: admin, supervisor, worker, contractor (separate from platform admin/user role)."""
from typing import List, Optional, Set

from db import connectToDB

WAREHOUSE_ROLES: Set[str] = {"admin", "supervisor", "worker", "contractor"}


def get_warehouse_role(user_id: int) -> Optional[str]:
    """Return warehouse_role for this user, or None if not linked to a warehouse."""
    conn = connectToDB.connectToDB()
    if conn is None:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT alarm_system_id, COALESCE(warehouse_role, 'admin')
            FROM user_table WHERE id = %s
            """,
            (user_id,),
        )
        row = cur.fetchone()
        if not row or row[0] is None:
            return None
        return str(row[1]).strip().lower() if row[1] else "admin"
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def count_users_in_warehouse(alarm_system_id: int) -> int:
    conn = connectToDB.connectToDB()
    if conn is None:
        return 0
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM user_table WHERE alarm_system_id = %s",
            (alarm_system_id,),
        )
        row = cur.fetchone()
        return int(row[0]) if row else 0
    except Exception:
        return 0
    finally:
        try:
            conn.close()
        except Exception:
            pass


def warehouse_has_admin(alarm_system_id: int) -> bool:
    conn = connectToDB.connectToDB()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 1 FROM user_table
            WHERE alarm_system_id = %s AND COALESCE(warehouse_role, 'admin') = 'admin'
            LIMIT 1
            """,
            (alarm_system_id,),
        )
        return cur.fetchone() is not None
    except Exception:
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass


def user_ids_guardians(alarm_system_id: int) -> List[int]:
    """Users who should be notified of worker/contractor arm-disarm actions (admin + supervisor)."""
    conn = connectToDB.connectToDB()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id FROM user_table
            WHERE alarm_system_id = %s
              AND COALESCE(warehouse_role, 'admin') IN ('admin', 'supervisor')
            """,
            (alarm_system_id,),
        )
        return [int(r[0]) for r in cur.fetchall()]
    except Exception:
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass


def user_ids_admins_only(alarm_system_id: int) -> List[int]:
    conn = connectToDB.connectToDB()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id FROM user_table
            WHERE alarm_system_id = %s AND COALESCE(warehouse_role, 'admin') = 'admin'
            """,
            (alarm_system_id,),
        )
        return [int(r[0]) for r in cur.fetchall()]
    except Exception:
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_username(user_id: int) -> str:
    conn = connectToDB.connectToDB()
    if conn is None:
        return "User"
    try:
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(username, email, '') FROM user_table WHERE id = %s", (user_id,))
        row = cur.fetchone()
        if row and row[0]:
            return str(row[0])[:80]
        return "User"
    except Exception:
        return "User"
    finally:
        try:
            conn.close()
        except Exception:
            pass


def can_view_history(warehouse_role: Optional[str]) -> bool:
    if warehouse_role is None:
        return True
    return warehouse_role not in ("worker", "contractor")
