# Simple Backend Startup Script
$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Starting Backend Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ROOT

# Find Python
if (Test-Path ".venv311\Scripts\python.exe") {
    $python = Resolve-Path ".venv311\Scripts\python.exe"
} elseif (Test-Path ".venv\Scripts\python.exe") {
    $python = Resolve-Path ".venv\Scripts\python.exe"
} else {
    Write-Host "[ERROR] Python not found!" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Using Python: $python" -ForegroundColor Green

# Kill any existing backend on port 8000
Write-Host ""
Write-Host "Checking for existing processes on port 8000..." -ForegroundColor Yellow
$existing = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    $pids = $existing | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($processId in $pids) {
        Write-Host "  Killing process $processId..." -ForegroundColor Yellow
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

# Set environment
$env:OWLIN_ENV = "dev"
$env:FEATURE_OCR_PIPELINE_V2 = "true"
$env:PYTHONPATH = $ROOT
$env:PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION = "python"

# Ensure directories
$dirs = @("data", "data\uploads", "data\logs")
foreach ($dir in $dirs) {
    $path = Join-Path $ROOT $dir
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}

# Start backend
Write-Host ""
Write-Host "Starting backend on port 8000..." -ForegroundColor Yellow
Write-Host "  Command: $python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload" -ForegroundColor Gray
Write-Host ""

# Start in new window
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$ROOT'; `$env:OWLIN_ENV='dev'; `$env:FEATURE_OCR_PIPELINE_V2='true'; `$env:PYTHONPATH='$ROOT'; `$env:PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION='python'; Write-Host '========================================' -ForegroundColor Cyan; Write-Host '   Backend Server (Port 8000)' -ForegroundColor Cyan; Write-Host '========================================' -ForegroundColor Cyan; Write-Host ''; & '$python' -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"
)

Write-Host "[OK] Backend starting in new window..." -ForegroundColor Green
Write-Host ""
Write-Host "Waiting 12 seconds for startup..." -ForegroundColor Yellow
Start-Sleep -Seconds 12

# Test
Write-Host ""
Write-Host "Testing backend..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/routes/status" -TimeoutSec 5 -UseBasicParsing
    Write-Host "[SUCCESS] Backend is running!" -ForegroundColor Green
    Write-Host "  Status Code: $($response.StatusCode)" -ForegroundColor Gray
    $data = $response.Content | ConvertFrom-Json
    Write-Host "  Total Routes: $($data.total_routes)" -ForegroundColor Gray
    Write-Host "  Chat Router: $($data.chat_router_loaded)" -ForegroundColor Gray
} catch {
    Write-Host "[WARN] Backend may still be starting or has errors" -ForegroundColor Yellow
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Gray
    Write-Host "  Check the backend window for details" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Backend URL: http://localhost:8000" -ForegroundColor Yellow
Write-Host "   Frontend: http://localhost:5176" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
