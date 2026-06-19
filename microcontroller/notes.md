# To upload files

Upload **all** `src/*.py` files, including **`ina219.py`** (INA219 energy sensor driver).

**Windows (PowerShell):**

```powershell
foreach ($file in Get-ChildItem src\*.py) { mpremote connect COM4 fs cp $file.FullName ":$($file.Name)" }
```

**Linux / Raspberry Pi (bash):**

```bash
cd microcontroller
for f in src/*.py; do ~/venv-mpremote/bin/mpremote connect /dev/ttyUSB0 fs cp "$f" ":$(basename "$f")"; done
```

# To run

```bash
mpremote connect COM4 exec "import main"
```

# Ctrl c to stop

## Connect ESP32 to the Pi backend

1. On the Pi, set a shared secret in `backend/.env`: `ESP32_INGEST_SECRET=<long random string>` (same value as `ESP32_INGEST_SECRET` in `src/config.py`).
2. Point `BACKEND_URL` to `http://<PI_LAN_IP>:8000/api/events/ingest` and set `WIFI_SSID` / `WIFI_PASSWORD` for your warehouse Wi‑Fi.
3. Set **`DEVICE_ID` per board** (must be unique): e.g. first ESP32 `esp32_001`, second `esp32_002`. The number after the underscore is the **`microcontroller_id`** in Postgres.
4. For each board, link it to your warehouse in the app (same user, same alarm system): `POST /api/device/connect` with `{"microcontroller_id": 1}` for `esp32_001`, then `{"microcontroller_id": 2}` for `esp32_002` (or use admin). Both rows can share the same `alarm_system_id`.
5. Reeds: **Sensor 1** = `REED1_PIN` (default GPIO 4 / D4), **sensor 2** = `REED2_PIN` (default GPIO 14 / D14). Set `REED2_PIN = None` in `config.py` to disable the second input. Events: `door_open` / `door_closed` for pin 1, `door_open_2` / `door_closed_2` for pin 2.
6. Power / INA219: `main.py` uses I2C on GPIO 21 (SDA), 22 (SCL), LED PWM on GPIO 2. Adjust pins if your wiring differs.
7. Re-upload `config.py` and `main.py` after editing; restart the board.
