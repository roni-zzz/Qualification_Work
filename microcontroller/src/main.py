import machine
import time
import wifi
import config
from ina219 import INA219
from events import EventManager

# wifi setup
print("\n=== WIFI DEBUG START ===")
print("WIFI_MODE:", config.WIFI_MODE)
print("WIFI_SSID:", config.WIFI_SSID)
print("BACKEND_URL:", config.BACKEND_URL)
print("DEVICE_ID:", config.DEVICE_ID)
print("=== ATTEMPTING CONNECTION ===")

if config.WIFI_MODE == "AP":
    esp_ip = wifi.create_ap(config.AP_SSID, config.AP_PASSWORD)
    print("ESP32 IP: " + esp_ip)
else:
    if wifi.connect(config.WIFI_SSID, config.WIFI_PASSWORD):
        print("WiFi connected successfully" )
    else:
        print("WiFi connection failed")
        print("=== RESTART REQUIRED ===")
        import machine
        machine.reset()


I2C_ADDR = 0x40 
i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21), freq=400000)



led = machine.PWM(machine.Pin(2), freq=1000)
devices = i2c.scan()
if not devices:
    print("No I2C devices found! Check your wires.")
    led.duty(5)
else:
    print("I2C devices found at:", [hex(d) for d in devices])
reed = machine.Pin(config.REED1_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
reed2 = (
    machine.Pin(config.REED2_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
    if getattr(config, "REED2_PIN", None) is not None
    else None
)
events = EventManager(device_id=config.DEVICE_ID)

try:
    energy_sensor = INA219(i2c, addr=I2C_ADDR)
    energy_sensor.set_calibration_16V_400mA()
except Exception:
    print("ERROR, continuing")
last_power_check = 0
POWER_INTERVAL_MS = 100
reed_state = reed.value()
last_reed_change = time.ticks_ms()
reed2_state = reed2.value() if reed2 else 0
last_reed2_change = time.ticks_ms()
MAX_CURRENT_EXPECTED = 400
DEBOUNCE_MS = 10

total_power = 0

devices = i2c.scan()



def check_door_open():
    """Send door_open when reed goes to open (1)."""
    global reed_state, last_reed_change
    now = time.ticks_ms()
    cur = reed.value()
    if cur != reed_state and now - last_reed_change >= DEBOUNCE_MS and cur == 1:
        reed_state = cur
        last_reed_change = now
        return True
    return False

def check_door_closed():
    """Send door_closed when reed goes to closed (0)."""
    global reed_state, last_reed_change
    now = time.ticks_ms()
    cur = reed.value()
    if cur != reed_state and now - last_reed_change >= DEBOUNCE_MS and cur == 0:
        reed_state = cur
        last_reed_change = now
        return True
    return False


def check_door_open_2():
    """Second sensor (D14): door_open_2 when open (1)."""
    global reed2_state, last_reed2_change
    if reed2 is None:
        return False
    now = time.ticks_ms()
    cur = reed2.value()
    if cur != reed2_state and now - last_reed2_change >= DEBOUNCE_MS and cur == 1:
        reed2_state = cur
        last_reed2_change = now
        return True
    return False


def check_door_closed_2():
    """Second sensor: door_closed_2 when closed (0)."""
    global reed2_state, last_reed2_change
    if reed2 is None:
        return False
    now = time.ticks_ms()
    cur = reed2.value()
    if cur != reed2_state and now - last_reed2_change >= DEBOUNCE_MS and cur == 0:
        reed2_state = cur
        last_reed2_change = now
        return True
    return False


def check_power():
    global last_power_check
    now = time.ticks_ms()
    
    if now - last_power_check >= POWER_INTERVAL_MS:
        last_power_check = now
        try:
            # Get current from sensor
            i_ma = energy_sensor.current
            
            #If wired incorrectly, display no light.
            i_ma = max(0, i_ma)
            
            # Map current to 0-1023 duty cycle on led 
            # (Current / Max) * 1023
            duty_val = int((i_ma / MAX_CURRENT_EXPECTED) * 1023)
            
            # Apply brightness, capped at 1023
            led.duty(min(1023, duty_val))
            
            return i_ma
        except Exception:
            led.duty(5) 
            return 45
    return False

events.on("door_open", check_door_open)
events.on("door_closed", check_door_closed)
if reed2 is not None:
    events.on("door_open_2", check_door_open_2)
    events.on("door_closed_2", check_door_closed_2)
events.on("current_power_usage", check_power)


while True:
    events.check_all()
    time.sleep(0.1)  # check 10 times per second
