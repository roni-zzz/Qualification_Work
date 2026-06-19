from db import connectToDB
import psycopg2
#import method for finding system id by username
from db import connectToAlarmSystem

#function to get mode
def getModeBySysId(alarm_system_id: int) -> bool | None:
    conn = connectToDB.connectToDB()
    mode = None

    if(conn == None):
        print("Couldnt connect")
        return None
    else:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT armed FROM alarm_system_table WHERE alarm_system_id = %s", (alarm_system_id,))
            row = cursor.fetchone()
            mode = row[0] if row is not None else None
        except Exception:
            mode = None
        finally:
            try:
                conn.close()
            except Exception:
                pass
            return mode

#function to get mode by username
def getModeByUsername(username: str) -> bool | None:
    systemId = connectToAlarmSystem.getCurrentAlarmSystemID(username)
    getModeBySysId(systemId)