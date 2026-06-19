# WiFi Mode: "AP" for Access Point (ESP32 creates hotspot) or "STA" for Station (ESP32 connects to existing WiFi)
WIFI_MODE = "STA"

# Access Point settings 
AP_SSID = "ESP32_WarehouseAlarm"
AP_PASSWORD = "Group24"  # Must be at least 8 characters

# Station mode settings 
WIFI_SSID = "Roni"  # Your WiFi network name (SSID)
WIFI_PASSWORD = "12345678"

# Backend: Pi on your LAN — same host/port as the app (Docker usually :8000).
# Prefer mDNS if your Pi advertises it (e.g. sweng24warehousealarm.local); else use http://<PI_IP>:8000/...
# Use /api/events/ingest with X-ESP32-Secret (see backend ESP32_INGEST_SECRET in .env).
BACKEND_URL = "http://172.20.10.12:5000/api/events/ingest"
# Must match backend/.env ESP32_INGEST_SECRET.
ESP32_INGEST_SECRET = "generate-a-long-random-string"

# Unique per physical board. Must match a registered device_id in DB.
DEVICE_ID = "esp32_1"

# Reed / magnetic sensors: GPIO number, pull-up, active HIGH when open (adjust if your wiring differs).
REED1_PIN = 4   # D4 — first sensor
REED2_PIN = 14  # D14 — second sensor (set to None to disable)