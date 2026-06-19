from db import connectToDB
import psycopg2
import bcrypt
from typing import Optional, Dict, Tuple, Any

# In-memory store for dev when PostgreSQL is not running (users lost on restart)
_dev_users: Dict[str, Dict] = {}
_dev_next_id = 1

# Query that works when phone/role columns exist (after migration)
_SELECT_USER_FULL = "SELECT id, email, username, COALESCE(role, 'user'), phone FROM user_table WHERE email = %s"
# Fallback when phone or role column is missing (old DB before migration)
_SELECT_USER_LEGACY = "SELECT id, email, username FROM user_table WHERE email = %s"


def _select_user_by_email(cursor, email: str) -> Optional[Tuple[Any, ...]]:
    """Fetch one user row by email. Tries full columns first, then legacy (no phone/role)."""
    try:
        cursor.execute(_SELECT_USER_FULL, (email,))
        return cursor.fetchone()
    except psycopg2.errors.UndefinedColumn:
        cursor.connection.rollback()  # allow another query after failed one
        cursor.execute(_SELECT_USER_LEGACY, (email,))
        row = cursor.fetchone()
        if row:
            return (row[0], row[1], row[2], "user", None)  # id, email, username, role, phone
        return None


def _find_or_create_google_user_dev(google_id: str, email: str, name: str) -> Dict:
    """Fallback when DB is unavailable: in-memory user store (dev only)."""
    global _dev_next_id
    if email in _dev_users:
        return _dev_users[email]
    user = {
        "id": _dev_next_id,
        "email": email,
        "name": name or email.split("@")[0],
    }
    _dev_next_id += 1
    _dev_users[email] = user
    return user


def _find_google_user_dev_only(email: str) -> Optional[Dict]:
    """Look up user in dev store only; no create. Returns None if not found."""
    return _dev_users.get(email)


def find_google_user_only(google_id: str, email: str, name: str) -> Optional[Dict]:
    """
    Find an existing user by email (Google OAuth). Does NOT create.
    Returns user dict or None if not found.
    """
    conn = None
    try:
        conn = connectToDB.connectToDB()
        if conn is None:
            return _find_google_user_dev_only(email)
        cursor = conn.cursor()
        user = _select_user_by_email(cursor, email)
        if user:
            user_id, user_email, username, role, phone = user
            return {
                "id": user_id,
                "email": user_email,
                "name": username or name,
                "role": role or "user",
                "phone": phone,
            }
        return None
    except psycopg2.OperationalError:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
        return _find_google_user_dev_only(email)
    except Exception as e:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
        print(f"Error in find_google_user_only: {e}")
        return None
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def get_user_by_email_for_password_login(email: str) -> Optional[tuple]:
    """
    For email/password login (admin-created users). Returns (user_dict, password_hash) or None.
    user_dict has id, email, name, role, phone, warehouse_role. Only returns if password_hash is not null.
    """
    conn = None
    try:
        conn = connectToDB.connectToDB()
        if conn is None:
            return None
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT id, email, username, COALESCE(role, 'user'), COALESCE(phone, ''), COALESCE(warehouse_role, ''), password_hash
                   FROM user_table WHERE email = %s AND password_hash IS NOT NULL""",
                (email.strip().lower(),),
            )
        except psycopg2.errors.UndefinedColumn:
            conn.rollback()
            cursor.execute(
                """SELECT id, email, username, COALESCE(role, 'user'), COALESCE(phone, ''), password_hash
                   FROM user_table WHERE email = %s AND password_hash IS NOT NULL""",
                (email.strip().lower(),),
            )
        row = cursor.fetchone()
        if not row:
            return None
        if len(row) == 7:
            user_id, user_email, username, role, phone, warehouse_role, password_hash = row
            phone = phone or None
        elif len(row) == 6:
            user_id, user_email, username, role, phone, password_hash = row
            warehouse_role = None
            phone = phone or None
        else:
            user_id, user_email, username, password_hash = row
            role, phone, warehouse_role = "user", None, None
        user_dict = {
            "id": user_id,
            "email": user_email,
            "name": username or user_email.split("@")[0],
            "role": role or "user",
            "phone": phone,
            "warehouse_role": warehouse_role,
        }
        return (user_dict, password_hash)
    except Exception as e:
        print(f"get_user_by_email_for_password_login: {e}")
        return None
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def ensure_global_admin_role(user_id: int) -> bool:
    """Persist role='admin' for a user. Returns True if role is admin after operation."""
    conn = None
    try:
        conn = connectToDB.connectToDB()
        if conn is None:
            return False
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE user_table
            SET role = 'admin'
            WHERE id = %s
              AND COALESCE(role, 'user') <> 'admin'
            """,
            (user_id,),
        )
        conn.commit()
        return True
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        print(f"ensure_global_admin_role: {e}")
        return False
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def find_or_create_google_user(google_id: str, email: str, name: str) -> Optional[Dict]:
    """
    Find or create a user from Google OAuth.
    Returns user dict with id, email, name, or None if error.
    When PostgreSQL is unavailable, falls back to in-memory store (dev only).
    """
    conn = None
    try:
        conn = connectToDB.connectToDB()
        if conn is None:
            print("Database connection returned None; using dev in-memory store")
            return _find_or_create_google_user_dev(google_id, email, name)
        cursor = conn.cursor()
        user = _select_user_by_email(cursor, email)

        if user:
            user_id, user_email, username, role, phone = user
            return {
                "id": user_id,
                "email": user_email,
                "name": username or name,
                "role": role or "user",
                "phone": phone,
            }
        else:
            cursor.execute("SELECT COUNT(*) FROM user_table")
            user_count = int(cursor.fetchone()[0] or 0)
            role = "admin" if user_count == 0 else "user"

            import secrets

            random_password = secrets.token_urlsafe(32)
            password_hash = bcrypt.hashpw(
                random_password.encode(),
                bcrypt.gensalt(),
            ).decode()
            username = email.split("@")[0][:100]
            try:
                cursor.execute(
                    """
                    INSERT INTO user_table (username, email, alarm_system_id, password_hash, role)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, email, username
                    """,
                    (username, email, None, password_hash, role),
                )
            except psycopg2.errors.UndefinedColumn:
                cursor.execute(
                    """
                    INSERT INTO user_table (username, email, alarm_system_id, password_hash)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, email, username
                    """,
                    (username, email, None, password_hash),
                )
            new_user = cursor.fetchone()
            conn.commit()
            if new_user:
                user_id, user_email, username = new_user
                return {
                    "id": user_id,
                    "email": user_email,
                    "name": username or name,
                    "role": role,
                    "phone": None,
                }

    except psycopg2.OperationalError:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
        print(
            "PostgreSQL not available (connection refused). Using dev in-memory store for Google OAuth."
        )
        return _find_or_create_google_user_dev(google_id, email, name)
    except psycopg2.IntegrityError:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        try:
            user = _select_user_by_email(cursor, email)
            if user:
                user_id, user_email, username, role, phone = user
                return {
                    "id": user_id,
                    "email": user_email,
                    "name": username or name,
                    "role": role or "user",
                    "phone": phone,
                }
        except Exception:
            pass
        return None
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        print(f"Error in find_or_create_google_user: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass