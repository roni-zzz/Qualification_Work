"""Contractor-user disarm requests pending admin approval."""
import time
from typing import Any, Dict, Optional

from db import connectToDB


def create_pending(alarm_system_id: int, requested_by_user_id: int, request_id: str) -> bool:
    conn = connectToDB.connectToDB()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO pending_disarm (id, alarm_system_id, requested_by_user_id, created_at, status)
            VALUES (%s, %s, %s, %s, 'pending')
            """,
            (request_id, alarm_system_id, requested_by_user_id, time.time()),
        )
        conn.commit()
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"create_pending_disarm failed: {e}")
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_pending(request_id: str) -> Optional[Dict[str, Any]]:
    conn = connectToDB.connectToDB()
    if conn is None:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, alarm_system_id, requested_by_user_id, created_at, status
            FROM pending_disarm WHERE id = %s
            """,
            (request_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "alarm_system_id": int(row[1]),
            "requested_by_user_id": int(row[2]),
            "created_at": float(row[3]),
            "status": str(row[4]),
        }
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def set_status(request_id: str, status: str) -> bool:
    conn = connectToDB.connectToDB()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE pending_disarm SET status = %s WHERE id = %s",
            (status, request_id),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"pending_disarm set_status failed: {e}")
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass


def list_pending_for_warehouse(alarm_system_id: int) -> list:
    conn = connectToDB.connectToDB()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, requested_by_user_id, created_at, status
            FROM pending_disarm
            WHERE alarm_system_id = %s AND status = 'pending'
            ORDER BY created_at DESC
            """,
            (alarm_system_id,),
        )
        return [
            {
                "id": r[0],
                "requested_by_user_id": int(r[1]),
                "created_at": float(r[2]),
                "status": str(r[3]),
            }
            for r in cur.fetchall()
        ]
    except Exception:
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass
