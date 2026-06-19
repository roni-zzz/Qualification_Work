import psycopg2

from db import connectToAlarmSystem
from db import connectToDB


def connectMicroController(microControllerId: int, username: str) -> bool:
    conn = connectToDB.connectToDB()
    systemId = connectToAlarmSystem.getCurrentAlarmSystemID(username)

    if systemId is None:
        print("The system id is none")
        return False
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO microcontroller (microcontroller_id, alarm_system_id, current_state)
            VALUES (%s, %s, %s)
            ON CONFLICT (microcontroller_id) DO UPDATE SET
                alarm_system_id = EXCLUDED.alarm_system_id,
                current_state = EXCLUDED.current_state
            """,
            (microControllerId, systemId, "idle"),
        )
        conn.commit()
        print("Microcontroller is added to system")
        return True
    except Exception:
        conn.rollback()
        print("Couldnt connect microcontroller")
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass


def connect_microcontroller_by_user_id(user_id: int, micro_controller_id: int) -> bool:
    """Link device to the current user's alarm system. Creates alarm system and pairs user if needed."""
    username = connectToAlarmSystem.get_username_by_user_id(user_id)
    if not username:
        return False
    if connectToAlarmSystem.get_alarm_system_id_by_user_id(user_id) is None:
        return False
    return connectMicroController(micro_controller_id, username)
