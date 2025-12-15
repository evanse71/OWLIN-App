# Debug script to start servers and show output
$ErrorActionPreference = "Continue"
$ROOT = "c:\Users\tedev\FixPack_2025-11-02_133105"
Set-Location $ROOT

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   OWLIN Server Startup - Debug Mode" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "[1/6] Checking Python virtual environment..." -ForegroundColor Yellow
$pythonExe = Join-Path $ROOT ".venv311\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = Join-Path $ROOT ".venv\Scripts\python.exe"
    if (-not (Test-Path $pythonExe)) {
        Write-Host "  [ERROR] Python virtual environment not found!" -ForegroundColor Red
        Write-Host "  Checked: .venv311\Scripts\python.exe" -ForegroundColor Gray
        Write-Host "  Checked: .venv\Scripts\python.exe" -ForegroundColor Gray
        exit 1
    }
}
Write-Host "  [OK] Found: $pythonExe" -ForegroundColor Green

# Check Node
Write-Host "[2/6] Checking Node.js..." -ForegroundColor Yellow
$nodeExe = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeExe) {
    Write-Host "  [ERROR] Node.js not found in PATH!" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] Found: $($nodeExe.Source)" -ForegroundColor Green

# Check frontend dependencies
Write-Host "[3/6] Checking frontend dependencies..." -ForegroundColor Yellow
$frontendDir = Join-Path $ROOT "frontend_clean"
$nodeModules = Join-Path $frontendDir "node_modules"
if (-not (Test-Path $nodeModules)) {
    Write-Host "  [WARN] node_modules not found. Installing..." -ForegroundColor Yellow
    Set-Location $frontendDir
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [ERROR] npm install failed!" -ForegroundColor Red
        exit 1
    }
    Set-Location $ROOT
} else {
    Write-Host "  [OK] node_modules found" -ForegroundColor Green
}

# Kill existing processes
Write-Host "[4/6] Cleaning up existing processes..." -ForegroundColor Yellow
Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*$ROOT*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Write-Host "  [OK] Cleanup complete" -ForegroundColor Green

# Set environment variables
Write-Host "[5/6] Setting environment variables..." -ForegroundColor Yellow
$env:OWLIN_ENV = "dev"
$env:FEATURE_OCR_PIPELINE_V2 = "true"
$env:PYTHONPATH = $ROOT
$env:PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION = "python"
Write-Host "  [OK] Environment variables set" -ForegroundColor Green

# Start Backend
Write-Host "[6/6] Starting servers..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Starting Backend on port 8000..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$ROOT'; `$env:OWLIN_ENV='dev'; `$env:FEATURE_OCR_PIPELINE_V2='true'; `$env:PYTHONPATH='$ROOT'; `$env:PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION='python'; Write-Host '=== BACKEND SERVER (Port 8000) ===' -ForegroundColor Green; Write-Host ''; '$pythonExe' -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"
)

Start-Sleep -Seconds 3

Write-Host "Starting Frontend on port 5176..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$frontendDir'; Write-Host '=== FRONTEND SERVER (Port 5176) ===' -ForegroundColor Green; Write-Host ''; npm run dev"
)

Write-Host ""
Write-Host "Waiting 15 seconds for servers to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Test connections
Write-Host ""
Write-Host "Testing connections..." -ForegroundColor Yellow
Write-Host ""

$backendOk = $false
$frontendOk = $false

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Host "[✓] Backend is running on http://localhost:8000" -ForegroundColor Green
    $backendOk = $true
} catch {
    Write-Host "[✗] Backend not responding: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "    Check the Backend Server window for errors" -ForegroundColor Yellow
}

try {
    $response = Invoke-WebRequest -Uri "http://localhost:5176" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Host "[✓] Frontend is running on http://localhost:5176" -ForegroundColor Green
    $frontendOk = $true
} catch {
    Write-Host "[✗] Frontend not responding: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "    Check the Frontend Server window for errors" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($backendOk -and $frontendOk) {
    Write-Host "   ✓ Both servers are running!" -ForegroundColor Green
    Write-Host "   Opening browser..." -ForegroundColor Yellow
    Start-Process "http://localhost:5176"
} else {
    Write-Host "   ⚠ Some servers may not be ready" -ForegroundColor Yellow
    Write-Host "   Check the server windows for errors" -ForegroundColor Yellow
    Write-Host "   Then try: http://localhost:5176" -ForegroundColor Cyan
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
