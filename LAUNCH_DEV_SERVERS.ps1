# Launch Development Servers for Owlin
# This script starts both backend (port 8000) and frontend (port 5176)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Starting Owlin Development Servers" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ROOT

# Check if ports are already in use
Write-Host "[1/4] Checking ports..." -ForegroundColor Yellow
$port8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
$port5176 = Get-NetTCPConnection -LocalPort 5176 -State Listen -ErrorAction SilentlyContinue

if ($port8000) {
    Write-Host "  [WARN] Port 8000 is already in use" -ForegroundColor Yellow
    $pid8000 = $port8000 | Select-Object -First 1 -ExpandProperty OwningProcess
    Write-Host "  Process ID: $pid8000" -ForegroundColor Gray
}

if ($port5176) {
    Write-Host "  [WARN] Port 5176 is already in use" -ForegroundColor Yellow
    $pid5176 = $port5176 | Select-Object -First 1 -ExpandProperty OwningProcess
    Write-Host "  Process ID: $pid5176" -ForegroundColor Gray
}

# Check Python virtual environment
Write-Host "[2/4] Checking Python environment..." -ForegroundColor Yellow
$pythonExe = Join-Path $ROOT ".venv311\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Host "  [ERROR] Python not found at: $pythonExe" -ForegroundColor Red
    Write-Host "  Please ensure the virtual environment is set up." -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] Python found" -ForegroundColor Green

# Check Node.js
Write-Host "[3/4] Checking Node.js..." -ForegroundColor Yellow
$nodeExe = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeExe) {
    Write-Host "  [ERROR] Node.js not found in PATH" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] Node.js found: $($nodeExe.Source)" -ForegroundColor Green

# Check frontend directory
$frontendDir = Join-Path $ROOT "frontend_clean"
if (-not (Test-Path $frontendDir)) {
    Write-Host "  [ERROR] Frontend directory not found: $frontendDir" -ForegroundColor Red
    exit 1
}

# Start Backend
Write-Host "[4/4] Starting servers..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  Starting Backend on port 8000..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$ROOT'; " +
    "`$env:OWLIN_ENV='dev'; " +
    "`$env:FEATURE_OCR_PIPELINE_V2='true'; " +
    "`$env:PYTHONPATH='$ROOT'; " +
    "`$env:PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION='python'; " +
    "Write-Host '========================================' -ForegroundColor Cyan; " +
    "Write-Host '   Backend Server (Port 8000)' -ForegroundColor Cyan; " +
    "Write-Host '========================================' -ForegroundColor Cyan; " +
    "Write-Host ''; " +
    ".\.venv311\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"
)

Start-Sleep -Seconds 2

# Start Frontend
Write-Host "  Starting Frontend on port 5176..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$frontendDir'; " +
    "Write-Host '========================================' -ForegroundColor Cyan; " +
    "Write-Host '   Frontend Server (Port 5176)' -ForegroundColor Cyan; " +
    "Write-Host '========================================' -ForegroundColor Cyan; " +
    "Write-Host ''; " +
    "if (-not (Test-Path 'node_modules')) { Write-Host 'Installing dependencies...' -ForegroundColor Yellow; npm install }; " +
    "npm run dev"
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Servers are starting..." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Two PowerShell windows have opened:" -ForegroundColor Yellow
Write-Host "  - Backend window: Running on port 8000" -ForegroundColor Gray
Write-Host "  - Frontend window: Running on port 5176" -ForegroundColor Gray
Write-Host ""
Write-Host "Waiting 12 seconds for servers to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 12

# Test connections
Write-Host ""
Write-Host "Testing connections..." -ForegroundColor Yellow
Write-Host ""

$backendOk = $false
$frontendOk = $false

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Host "[✓] Backend is running on http://localhost:8000" -ForegroundColor Green
    Write-Host "    Status: $($response.StatusCode)" -ForegroundColor Gray
    $backendOk = $true
} catch {
    Write-Host "[✗] Backend not responding yet" -ForegroundColor Yellow
    Write-Host "    Error: $($_.Exception.Message)" -ForegroundColor Gray
    Write-Host "    Check the backend window for errors" -ForegroundColor Gray
}

try {
    $response = Invoke-WebRequest -Uri "http://localhost:5176" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Host "[✓] Frontend is running on http://localhost:5176" -ForegroundColor Green
    Write-Host "    Status: $($response.StatusCode)" -ForegroundColor Gray
    $frontendOk = $true
} catch {
    Write-Host "[✗] Frontend not responding yet" -ForegroundColor Yellow
    Write-Host "    Error: $($_.Exception.Message)" -ForegroundColor Gray
    Write-Host "    Check the frontend window for errors" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($backendOk -and $frontendOk) {
    Write-Host "   ✓ Both servers are running!" -ForegroundColor Green
} else {
    Write-Host "   ⚠ Some servers may still be starting" -ForegroundColor Yellow
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Open your browser to:" -ForegroundColor Cyan
Write-Host "  http://localhost:5176" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press any key to exit this window (servers will keep running)..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
