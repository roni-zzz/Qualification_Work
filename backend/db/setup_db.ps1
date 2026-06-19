# Run in PowerShell from the backend folder: .\db\setup_db.ps1

$ErrorActionPreference = "Stop"
$psql = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
if (-not (Test-Path $psql)) { $psql = "C:\Program Files\PostgreSQL\16\bin\psql.exe" }
if (-not (Test-Path $psql)) {
    Write-Host "psql not found. Edit this script and set the path to your PostgreSQL bin\psql.exe"
    exit 1
}

$backendDir = (Get-Item $PSScriptRoot).Parent.FullName
$envFile = Join-Path $backendDir ".env"
$dbPassword = "1991"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*DATABASE_PASSWORD\s*=\s*(.+)\s*$') { $dbPassword = $matches[1].Trim().Trim('"') }
    }
}
$env:PGPASSWORD = $dbPassword

Write-Host "Creating database alarm_system..."
& $psql -U postgres -h localhost -d postgres -c "CREATE DATABASE alarm_system;" 2>$null
# Ignore error if DB already exists

Write-Host "Creating tables..."
& $psql -U postgres -h localhost -d alarm_system -f (Join-Path $PSScriptRoot "workflow.sql")
if ($LASTEXITCODE -ne 0) { Write-Host "Failed. Check that PostgreSQL is running and password in .env is correct."; exit 1 }

Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
Write-Host "Done. Start backend with: py run.py"
