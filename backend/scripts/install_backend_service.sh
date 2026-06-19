#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   sudo ./backend/scripts/install_backend_service.sh
# Optional env overrides:
#   APP_USER=admin APP_GROUP=admin PROJECT_ROOT=/home/admin/alarm VENV_PATH=/home/admin/alarm/.venv

APP_USER="${APP_USER:-admin}"
APP_GROUP="${APP_GROUP:-$APP_USER}"
PROJECT_ROOT="${PROJECT_ROOT:-/home/$APP_USER/alarm}"
BACKEND_DIR="$PROJECT_ROOT/backend"
VENV_PATH="${VENV_PATH:-$PROJECT_ROOT/.venv}"
SERVICE_NAME="alarm-backend.service"
UNIT_PATH="/etc/systemd/system/$SERVICE_NAME"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root: sudo $0"
  exit 1
fi

if [[ ! -f "$BACKEND_DIR/run.py" ]]; then
  echo "Could not find $BACKEND_DIR/run.py"
  echo "Set PROJECT_ROOT, e.g.: PROJECT_ROOT=/home/admin/alarm sudo $0"
  exit 1
fi

if [[ ! -x "$VENV_PATH/bin/python" ]]; then
  echo "Could not find python at $VENV_PATH/bin/python"
  echo "Create venv first, e.g.:"
  echo "  python3 -m venv $VENV_PATH"
  echo "  $VENV_PATH/bin/pip install -r $BACKEND_DIR/requirements.txt"
  exit 1
fi

cat > "$UNIT_PATH" <<EOF
[Unit]
Description=Alarm Backend FastAPI
After=network-online.target postgresql.service
Wants=network-online.target postgresql.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$BACKEND_DIR
Environment=PYTHONUNBUFFERED=1
ExecStart=$VENV_PATH/bin/python $BACKEND_DIR/run.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

echo "Installed and started $SERVICE_NAME"
echo "Check status with: systemctl status $SERVICE_NAME"
echo "Follow logs with: journalctl -u $SERVICE_NAME -f"
