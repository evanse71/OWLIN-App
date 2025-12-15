# Quick Backend Startup Script
$ErrorActionPreference = "Continue"

$ROOT = "c:\Users\tedev\FixPack_2025-11-02_133105"
Set-Location $ROOT

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Starting Backend on Port 8000" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Find Python
if (Test-Path "$ROOT\.venv311\Scripts\python.exe") {
    $python = "$ROOT\.venv311\Scripts\python.exe"
} elseif (Test-Path "$ROOT\.venv\Scripts\python.exe") {
    $python = "$ROOT\.venv\Scripts\python.exe"
} else {
    Write-Host "[ERROR] Python not found in .venv or .venv311" -ForegroundColor Red
    Write-Host "Please ensure virtual environment exists" -ForegroundColor Yellow
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

# Set environment variables
$env:OWLIN_ENV = "dev"
$env:FEATURE_OCR_PIPELINE_V2 = "true"
$env:PYTHONPATH = $ROOT
$env:PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION = "python"

# Ensure directories exist
$dirs = @("data", "data\uploads", "data\logs")
foreach ($dir in $dirs) {
    $path = Join-Path $ROOT $dir
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
        Write-Host "  Created directory: $dir" -ForegroundColor Gray
    }
}

# Start backend in new window
Write-Host ""
Write-Host "Starting backend in new window..." -ForegroundColor Yellow
Write-Host "  Command: $python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload" -ForegroundColor Gray
Write-Host ""

$command = @"
cd '$ROOT'
`$env:OWLIN_ENV='dev'
`$env:FEATURE_OCR_PIPELINE_V2='true'
`$env:PYTHONPATH='$ROOT'
`$env:PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION='python'
Write-Host '========================================' -ForegroundColor Cyan
Write-Host '   Backend Server (Port 8000)' -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan
Write-Host ''
Write-Host 'Starting server...' -ForegroundColor Yellow
Write-Host ''
& '$python' -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $command

Write-Host "[OK] Backend starting in new window..." -ForegroundColor Green
Write-Host ""
Write-Host "Waiting 15 seconds for startup..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Test backend
Write-Host ""
Write-Host "Testing backend connection..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/health" -TimeoutSec 5
    Write-Host "[SUCCESS] Backend is running!" -ForegroundColor Green
    Write-Host "  URL: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "  Health endpoint: http://localhost:8000/api/health" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Response:" -ForegroundColor Gray
    $response | ConvertTo-Json -Depth 3 | Write-Host
} catch {
    Write-Host "[WARN] Backend may still be starting or has errors" -ForegroundColor Yellow
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Gray
    Write-Host "  Please check the backend window for details" -ForegroundColor Gray
    Write-Host "  The backend may take 30+ seconds to start (OCR engines loading)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Backend URL: http://localhost:8000" -ForegroundColor Yellow
Write-Host "   Health Check: http://localhost:8000/api/health" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
