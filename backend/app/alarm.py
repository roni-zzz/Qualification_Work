from fastapi import FastAPI
from pydantic import BaseModel
import threading
import time
import requests

app = FastAPI()

# System state
system_armed = False    
monitor_thread = None   

ESP32_URL = ""  # need to change to the thing for our esp

# Background Sensor Monitor

def monitor_sensors():
    global system_armed  # can see variable
    while system_armed:
        try:
            response = requests.get(ESP32_URL, timeout=3)
            data = response.json()

            # Check sensors
            for sensor, status in data.items():
                if not status:
                    print(f"⚠️ ALERT: {sensor} not working!")

            print("All sensors checked.")

        except Exception as e:
            print("⚠️ ESP32 not reachable!", e)

        time.sleep(5)  # check every 5 seconds

# recieving arm or disarm from front end
class Command(BaseModel):
    action: str  # "arm" or "disarm"


@app.post("/system")
def control_system(command: Command):
    global system_armed, monitor_thread

    if command.action.lower() == "arm":
        if not system_armed:
            system_armed = True
            monitor_thread = threading.Thread(target=monitor_sensors)
            monitor_thread.start()
            return {"status": "System armed"}
        else:
            return {"status": "System already armed"}

    elif command.action.lower() == "disarm":
        system_armed = False
        return {"status": "System disarmed"}

    return {"error": "Invalid command"}