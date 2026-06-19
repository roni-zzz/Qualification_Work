# Backend (FastAPI)

## Setup

```bash
# From backend folder
py -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set `DATABASE_PASSWORD`, `GOOGLE_CLIENT_ID`, `JWT_SECRET`. See `db/README_SETUP.md` for PostgreSQL setup.

**Push notifications (optional):** To send FCM push when a door opens/closes, add to `.env`: `FIREBASE_CREDENTIALS_PATH=path/to/your-firebase-service-account.json`. Get the JSON from Firebase Console → Project Settings → Service accounts → Generate new private key. The app registers its FCM token at `POST /api/notifications/register` after login.

## Run

```bash
cd backend
py run.py
```

Server runs at **http://127.0.0.1:5000**. API docs: **http://127.0.0.1:5000/docs**

## Raspberry Pi Auto-Start (systemd)

Use systemd so backend starts automatically on boot and restarts on crashes.

1. Create venv and install dependencies:

```bash
cd /home/admin/alarm/backend
python3 -m venv /home/admin/alarm/.venv
/home/admin/alarm/.venv/bin/pip install --upgrade pip
/home/admin/alarm/.venv/bin/pip install -r requirements.txt
```

2. Ensure `/home/admin/alarm/backend/.env` exists and includes at least `JWT_SECRET`, `DATABASE_PASSWORD`, and `ESP32_INGEST_SECRET`.

3. Install and enable the service:

```bash
cd /home/admin/alarm
chmod +x backend/scripts/install_backend_service.sh
sudo backend/scripts/install_backend_service.sh
```

4. Verify:

```bash
systemctl status alarm-backend.service
journalctl -u alarm-backend.service -f
```

If your project path/user differs from `/home/admin/alarm`, pass overrides:

```bash
APP_USER=admin PROJECT_ROOT=/home/admin/alarm VENV_PATH=/home/admin/alarm/.venv sudo backend/scripts/install_backend_service.sh
```

## Structure

- `app/` – FastAPI app (`main.py`), config, validation
- `db/` – PostgreSQL helpers, migrations (`workflow.sql`), auth (`googleAuth.py`)
- `run.py` – Entry point (uvicorn)

## Test event (PowerShell)

```powershell
$ts = [int](Get-Date -UFormat %s)
$body = @{ device_id = "esp32_001"; event_type = "door_open"; count = 1; timestamp = $ts } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:5000/api/events -Method POST -ContentType "application/json" -Body $body
```
