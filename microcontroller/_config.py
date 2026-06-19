# WiFi Mode: "AP" for Access Point (ESP32 creates hotspot) or "STA" for Station (ESP32 connects to existing WiFi)
WIFI_MODE = "STA"

# Access Point settings 
AP_SSID = "ESP32_WarehouseAlarm"
AP_PASSWORD = "Group24"  # Must be at least 8 characters

# Station mode settings 
WIFI_SSID = "Roni"  # Your WiFi network name (SSID)
WIFI_PASSWORD = "12345678"

# Backend: Pi (or dev PC) on your LAN — same URL the phone uses, port 8000 if using Docker.
# Use /api/events/ingest with X-ESP32-Secret (see backend ESP32_INGEST_SECRET in .env).
BACKEND_URL = "http://172.20.10.12:5000/api/events/ingest"
# Must match backend/.env ESP32_INGEST_SECRET.
ESP32_INGEST_SECRET = "generate-a-long-random-string"

# Unique per physical board. Must match microcontroller_id in the DB: esp32_001 -> id 1, esp32_002 -> id 2, etc.
# Flash different config.py on each ESP32 (or edit this line before uploading).
DEVICE_ID = "esp32_002"