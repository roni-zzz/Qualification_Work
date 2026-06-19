from typing import Optional

from db import connectToDB
#hashing
import bcrypt
import psycopg2
#real random
import secrets
import string

def generate_random_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def create_alarm_system(cur) -> tuple[int, str]:
    password = generate_random_password(12)
    password_hash = bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt()
    ).decode()

    cur.execute(
        """
        INSERT INTO alarm_system_table (
            system_password_hash,
            armed,
            paired
        )
        VALUES (%s, FALSE, FALSE)
        RETURNING alarm_system_id
        """,
        (password_hash,)
    )

    alarm_system_id = cur.fetchone()[0]
    return alarm_system_id, password


#testing


# def addAlarmSystems(numberOfSystems: int) -> None:
#     conn = connectToDB.connectToDB()
#     try:
#         cursor = conn.cursor()

#         for _ in range(numberOfSystems):
#             system_id, password = create_alarm_system(cursor)
#             print(f"Created alarm system {system_id} with password {password}")

#         conn.commit()

#     except Exception:
#         conn.rollback()
#         raise

#     finally:
#         conn.close()


def create_warehouse_with_device(
    cur,
    microcontroller_id: Optional[int] = None,
) -> tuple[int, int, str]:
    """
    Create one alarm system and one microcontroller (the "warehouse" / ESP32).
    If microcontroller_id is set, use it (so firmware DEVICE_ID esp32_<n> can match without reflashing).
    Otherwise allocate the next free id (MAX+1).
    Returns (alarm_system_id, microcontroller_id, device_id e.g. 'esp32_7').
    """
    alarm_system_id, _ = create_alarm_system(cur)
    if microcontroller_id is not None:
        mc_id = int(microcontroller_id)
        if mc_id < 1:
            raise ValueError("microcontroller_id must be >= 1")
        cur.execute(
            "SELECT 1 FROM microcontroller WHERE microcontroller_id = %s",
            (mc_id,),
        )
        if cur.fetchone():
            raise ValueError(
                f"microcontroller_id {mc_id} is already in use — pick another id or omit for auto"
            )
    else:
        cur.execute("SELECT COALESCE(MAX(microcontroller_id), 0) + 1 FROM microcontroller")
        mc_id = cur.fetchone()[0]
    cur.execute(
        """
        INSERT INTO microcontroller (microcontroller_id, alarm_system_id, current_state)
        VALUES (%s, %s, 'idle')
        """,
        (mc_id, alarm_system_id),
    )
    return alarm_system_id, mc_id, f"esp32_{mc_id}"


# addAlarmSystems(10)