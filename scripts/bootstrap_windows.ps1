$ErrorActionPreference = "Stop"

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$ROOT = Join-Path $ROOT ".." | Resolve-Path
$BE = Join-Path $ROOT "backend"
$FE = Join-Path $ROOT "frontend"

Write-Host "==> Backend venv & deps"
Set-Location $BE
python -m venv .venv
& ".\.venv\Scripts\Activate.ps1"
pip install --upgrade pip
if (Test-Path ".\requirements.txt") { pip install -r requirements.txt } else { throw "backend/requirements.txt missing" }

Write-Host "==> Backend .env"
if (-not (Test-Path ".\.env")) {
  if (Test-Path ".\.env.example") { Copy-Item ".\.env.example" ".\.env" }
  else {
@"
DB_PATH=./data/owlin.db
LICENSE_DIR=./license
LOG_DIR=./logs
ALLOW_ORIGINS=http://localhost:3000
OCR_LANG=en
"@ | Out-File -Encoding utf8 ".\.env"
  }
}
New-Item -ItemType Directory -Force -Path ".\data" | Out-Null
New-Item -ItemType Directory -Force -Path ".\logs" | Out-Null
New-Item -ItemType Directory -Force -Path ".\license" | Out-Null

Write-Host "==> DB init (if available)"
if (Get-Command alembic -ErrorAction SilentlyContinue) { alembic upgrade head } elseif (Test-Path ".\scripts\init_db.py") { python .\scripts\init_db.py }

Write-Host "==> Start backend :8001"
$pid = (Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue | Select-Object -First 1).OwningProcess
if ($pid) { Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue }
Start-Process -FilePath "uvicorn" -ArgumentList "app.main:app","--host","0.0.0.0","--port","8001","--reload" -WindowStyle Minimized
Start-Sleep -Seconds 3

Write-Host "==> Frontend deps"
Set-Location $FE
if (Test-Path ".\package.json") { npm install } else { throw "frontend/package.json missing" }

Write-Host "==> Frontend .env.local"
if (-not (Test-Path ".\.env.local")) {
  if (Test-Path ".\.env.example") { Copy-Item ".\.env.example" ".\.env.local" }
  else { "NEXT_PUBLIC_API_BASE=http://localhost:8001" | Out-File -Encoding utf8 ".\.env.local" }
}

Write-Host "==> Start frontend :3000"
$pid = (Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | Select-Object -First 1).OwningProcess
if ($pid) { Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue }
Start-Process -FilePath "npm" -ArgumentList "run","dev" -WindowStyle Minimized
Start-Sleep -Seconds 4

Write-Host "==> Healthcheck"
Set-Location (Join-Path $ROOT "scripts")
bash .\healthcheck.sh

Write-Host "==> Done. Open http://localhost:3000"
