"""
Create or update a user for email/password login with role admin.

Does not store plaintext passwords in the repo — pass via env or argv when you run once.

From backend/:
  ADMIN_BOOTSTRAP_PASSWORD='your-password' python scripts/ensure_password_admin.py user@example.com

Or (password visible in shell history):
  python scripts/ensure_password_admin.py user@example.com 'your-password'

Uses backend/.env for DATABASE_*.
"""
import getpass
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from dotenv import load_dotenv

load_dotenv(backend_dir / ".env")

import bcrypt
import psycopg2
from db import connectToDB


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    email = sys.argv[1].strip().lower()
    if not email or "@" not in email:
        print("Invalid email.")
        return 1

    password = (os.environ.get("ADMIN_BOOTSTRAP_PASSWORD") or "").strip()
    if not password and len(sys.argv) >= 3:
        password = sys.argv[2]
    if not password:
        p1 = getpass.getpass("Password: ")
        p2 = getpass.getpass("Again: ")
        if p1 != p2:
            print("Passwords do not match.")
            return 1
        password = p1
    if not password:
        print("Password required.")
        return 1

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode()
    username = email.split("@")[0][:100]

    conn = connectToDB.connectToDB()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM user_table WHERE lower(trim(email)) = %s",
            (email,),
        )
        row = cur.fetchone()
        if row:
            try:
                cur.execute(
                    """
                    UPDATE user_table
                    SET password_hash = %s, role = 'admin', username = %s
                    WHERE lower(trim(email)) = %s
                    """,
                    (password_hash, username, email),
                )
            except psycopg2.errors.UndefinedColumn:
                conn.rollback()
                cur.execute(
                    """
                    UPDATE user_table
                    SET password_hash = %s, username = %s
                    WHERE lower(trim(email)) = %s
                    """,
                    (password_hash, username, email),
                )
                print("Updated password; role column missing — run migrations, then set admin role.")
                conn.commit()
                return 0
            conn.commit()
            print(f"Updated existing user {email!r} — password reset and role set to admin (id={row[0]}).")
            return 0

        try:
            cur.execute(
                """
                INSERT INTO user_table (username, email, alarm_system_id, password_hash, role)
                VALUES (%s, %s, NULL, %s, 'admin')
                """,
                (username, email, password_hash),
            )
        except psycopg2.errors.UndefinedColumn:
            conn.rollback()
            cur.execute(
                """
                INSERT INTO user_table (username, email, alarm_system_id, password_hash)
                VALUES (%s, %s, NULL, %s)
                """,
                (username, email, password_hash),
            )
            print(
                "Inserted user without role column — run migrations and: "
                f"python scripts/run_migration_and_set_admin.py {email}"
            )
        conn.commit()
        print(f"Created admin user {email!r} (email/password login).")
        return 0
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        return 1
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
