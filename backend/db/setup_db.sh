#!/usr/bin/env bash

set -e

# Stop immediately on error
trap "echo 'Script failed.'; exit 1" ERR

# Check if psql exists
if ! command -v psql >/dev/null 2>&1; then
    echo "psql not found. Install PostgreSQL with: sudo pacman -S postgresql"
    exit 1
fi

# Get backend directory (script is inside db/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

ENV_FILE="$BACKEND_DIR/.env"
DB_PASSWORD="1991"

# Read DATABASE_PASSWORD from .env if it exists
if [[ -f "$ENV_FILE" ]]; then
    while IFS= read -r line; do
        if [[ "$line" =~ ^[[:space:]]*DATABASE_PASSWORD[[:space:]]*=[[:space:]]*(.+)[[:space:]]*$ ]]; then
            DB_PASSWORD="${BASH_REMATCH[1]}"
            DB_PASSWORD="${DB_PASSWORD%\"}"
            DB_PASSWORD="${DB_PASSWORD#\"}"
        fi
    done < "$ENV_FILE"
fi

export PGPASSWORD="$DB_PASSWORD"

echo "Creating database alarm_system..."
psql -U postgres -h localhost -d postgres \
     -c "CREATE DATABASE alarm_system;" 2>/dev/null || true
# Ignore error if DB already exists

echo "Creating tables..."
psql -U postgres -h localhost -d alarm_system \
     -f "$SCRIPT_DIR/workflow.sql"

echo "Done. Start backend with: py run.py"

unset PGPASSWORD
