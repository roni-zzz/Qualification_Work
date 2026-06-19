# PostgreSQL setup for backend

## Option A: Use the setup script (easiest)

**In PowerShell:**

1. Open PowerShell (or Terminal in VS Code/Cursor).
2. Go to the backend folder and run the script:

```powershell
cd "C:\Users\lance\Music\SwEng 26\sweng24-guidewirewarehousealarm\backend"
.\db\setup_db.ps1
```

If you get "cannot run scripts" run once: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

The script creates the `alarm_system` database and tables. It uses the password from `backend\.env` (`DATABASE_PASSWORD`). If your postgres password is not `1991`, change it in `.env` first.

---

## Option B: Do it manually in the terminal

**1. Start PostgreSQL**  
Windows: Win+R → `services.msc` → find **PostgreSQL** → Start.

**2. In PowerShell**, from the **backend** folder:

```powershell
cd "C:\Users\lance\Music\SwEng 26\sweng24-guidewirewarehousealarm\backend"

# Set your postgres password (same as in .env)
$env:PGPASSWORD = "1991"

# Create database (path may be 16 instead of 18)
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost -d postgres -c "CREATE DATABASE alarm_system;"

# Create tables
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost -d alarm_system -f db\workflow.sql

# Clear password from environment
Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
```

If you have PostgreSQL 16, change `18` to `16` in the path.

**3. Restart the backend:**

```powershell
py run.py
```

---

## .env

In `backend\.env` use your real postgres password (no spaces around `=`):

```
DATABASE_PASSWORD=1991
DATABASE_HOST=localhost
```
