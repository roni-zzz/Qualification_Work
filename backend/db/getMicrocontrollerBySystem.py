from db import connectToDB


def is_microcontroller_registered_to_user(microcontroller_id: int, user_id: int) -> bool:
    """
    Returns True if the given microcontroller_id is registered
    to the alarm system that belongs to the given user.
    """
    conn = connectToDB.connectToDB()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT 1
            FROM microcontroller mc
            JOIN user_table u ON u.alarm_system_id = mc.alarm_system_id
            WHERE u.id = %s AND mc.microcontroller_id = %s
            """,
            (user_id, microcontroller_id),
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()
