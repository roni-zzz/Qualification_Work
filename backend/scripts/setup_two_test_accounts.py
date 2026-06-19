"""
Link two DB user accounts to two mock alarm systems, each with one microcontroller.
After running, you can send events to each account separately:
  - Account 1 (first user): device_id esp32_111
  - Account 2 (second user): device_id esp32_222

Run from repo root:
  py backend/scripts/setup_two_test_accounts.py
Or from backend folder:
  py scripts/setup_two_test_accounts.py

Requires: PostgreSQL running, two users in user_table, .env with DATABASE_PASSWORD etc.
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir / "db"))

import connectToDB
import addAvailableSystems

# Mock microcontroller IDs: events with device_id esp32_111 go to account 1, esp32_222 to account 2
MC_ID_1 = 111
MC_ID_2 = 222


def main():
    conn = connectToDB.connectToDB()
    cursor = conn.cursor()

    # Get first two users (by id)
    cursor.execute(
        "SELECT id, email, username, alarm_system_id FROM user_table ORDER BY id LIMIT 2"
    )
    rows = cursor.fetchall()
    if len(rows) < 2:
        print("Need at least 2 users in user_table. Found:", len(rows))
        conn.close()
        sys.exit(1)

    user1_id, user1_email, user1_username, user1_sys = rows[0]
    user2_id, user2_email, user2_username, user2_sys = rows[1]
    print(f"User 1: id={user1_id} email={user1_email} -> device esp32_{MC_ID_1}")
    print(f"User 2: id={user2_id} email={user2_email} -> device esp32_{MC_ID_2}")

    # Create two alarm systems (or reuse if we want same systems; creating new keeps test isolated)
    system1_id, pw1 = addAvailableSystems.create_alarm_system(cursor)
    system2_id, pw2 = addAvailableSystems.create_alarm_system(cursor)
    print(f"Created alarm system {system1_id} (password: {pw1})")
    print(f"Created alarm system {system2_id} (password: {pw2})")

    # Assign user1 -> system1, user2 -> system2
    cursor.execute(
        "UPDATE user_table SET alarm_system_id = %s WHERE id = %s",
        (system1_id, user1_id),
    )
    cursor.execute(
        "UPDATE user_table SET alarm_system_id = %s WHERE id = %s",
        (system2_id, user2_id),
    )
    cursor.execute(
        "UPDATE alarm_system_table SET paired = %s WHERE alarm_system_id IN (%s, %s)",
        ("T", system1_id, system2_id),
    )

    # Register mock microcontrollers: 111 -> system1, 222 -> system2
    cursor.execute(
        """
        INSERT INTO microcontroller (microcontroller_id, alarm_system_id, current_state)
        VALUES (%s, %s, 'idle')
        ON CONFLICT (microcontroller_id) DO UPDATE SET alarm_system_id = EXCLUDED.alarm_system_id
        """,
        (MC_ID_1, system1_id),
    )
    cursor.execute(
        """
        INSERT INTO microcontroller (microcontroller_id, alarm_system_id, current_state)
        VALUES (%s, %s, 'idle')
        ON CONFLICT (microcontroller_id) DO UPDATE SET alarm_system_id = EXCLUDED.alarm_system_id
        """,
        (MC_ID_2, system2_id),
    )

    conn.commit()
    conn.close()

    print("Done.")
    print("")
    print("Send events to Account 1 (first user):")
    print("  py backend/scripts/send_test_events.py --device esp32_111")
    print("")
    print("Send events to Account 2 (second user):")
    print("  py backend/scripts/send_test_events.py --device esp32_222")
    print("")
    print("Send to both (one event each):")
    print("  py backend/scripts/send_test_events.py --both")


if __name__ == "__main__":
    main()
