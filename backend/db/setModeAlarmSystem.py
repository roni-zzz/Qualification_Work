from db import connectToDB
from db import getModeOfSystem


def setMode(alarm_system_id: int, value: bool) -> bool:
    """Set armed state for the alarm system. Returns True on success."""
    conn = connectToDB.connectToDB()
    if conn is None:
        raise RuntimeError("Could not connect to DB")
    try:
        cursor = conn.cursor()
        currentMode = getModeOfSystem.getModeBySysId(alarm_system_id)
        if currentMode == value:
            return True
        cursor.execute(
            "UPDATE alarm_system_table SET armed = %s WHERE alarm_system_id = %s",
            (value, alarm_system_id),
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        try:
            conn.close()
        except Exception:
            pass