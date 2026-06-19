"""
Run the admin migration (phone, role, sensor_labels, device_last_seen) and set one user as admin.
Usage (from backend folder):
  python scripts/run_migration_and_set_admin.py
  python scripts/run_migration_and_set_admin.py admins123987@gmail.com

Uses .env in backend/ for DATABASE_PASSWORD and DATABASE_HOST.
"""
import os
import sys
from pathlib import Path

# backend/scripts/ -> backend/
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from db import connectToDB


def run_migration():
    migration_path = backend_dir / "db" / "migrations" / "001_add_phone_and_admin_tables.sql"
    if not migration_path.exists():
        print(f"Migration file not found: {migration_path}")
        return False
    sql = migration_path.read_text()
    conn = connectToDB.connectToDB()
    try:
        cur = conn.cursor()
        # Run each statement (split by semicolon; skip empty or trailing ")" only)
        for raw in sql.split(";"):
            stmt = raw.strip()
            if not stmt or stmt == ")" or stmt.startswith("--"):
                continue
            cur.execute(stmt)
        conn.commit()
        print("Migration applied successfully.")
        return True
    except Exception as e:
        conn.rollback()
        print(f"Migration error: {e}")
        return False
    finally:
        conn.close()


def set_admin(email: str):
    conn = connectToDB.connectToDB()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE user_table SET role = 'admin' WHERE email = %s RETURNING id",
            (email.strip().lower(),),
        )
        row = cur.fetchone()
        conn.commit()
        if row:
            print(f"User {email} is now an admin (id={row[0]}).")
            return True
        else:
            print(f"No user found with email: {email}. Check the address and try again.")
            return False
    except Exception as e:
        conn.rollback()
        print(f"Update error: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    admin_email = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
    if not admin_email:
        print("Usage: python scripts/run_migration_and_set_admin.py <admin_email>")
        print("Example: python scripts/run_migration_and_set_admin.py admins123987@gmail.com")
        sys.exit(1)

    print("Applying migration...")
    if not run_migration():
        sys.exit(1)
    print("Setting admin role...")
    if not set_admin(admin_email):
        sys.exit(1)
    print("Done.")
