# Quick Start Script for OWLIN
$ErrorActionPreference = "Continue"
$ROOT = "c:\Users\tedev\FixPack_2025-11-02_133105"
Set-Location $ROOT

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   OWLIN Server Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "[1/6] Checking Python..." -ForegroundColor Yellow
$pythonExe = "$ROOT\.venv311\Scripts\python.exe"
if (Test-Path $pythonExe) {
    $version = & $pythonExe --version
    Write-Host "  ✓ Found: $version" -ForegroundColor Green
} else {
    Write-Host "  ✗ Python not found at: $pythonExe" -ForegroundColor Red
    exit 1
}

# Check Node
Write-Host "[2/6] Checking Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version
    Write-Host "  ✓ Found: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Node.js not found!" -ForegroundColor Red
    exit 1
}

# Check frontend dependencies
Write-Host "[3/6] Checking frontend dependencies..." -ForegroundColor Yellow
$frontendDir = "$ROOT\frontend_clean"
if (-not (Test-Path "$frontendDir\node_modules")) {
    Write-Host "  ⚠ node_modules not found. Installing..." -ForegroundColor Yellow
    Set-Location $frontendDir
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ npm install failed!" -ForegroundColor Red
        exit 1
    }
    Set-Location $ROOT
} else {
    Write-Host "  ✓ node_modules found" -ForegroundColor Green
}

# Kill existing processes
Write-Host "[4/6] Cleaning up existing processes..." -ForegroundColor Yellow
Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*$ROOT*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Write-Host "  ✓ Cleanup complete" -ForegroundColor Green

# Set environment
$env:OWLIN_ENV = "dev"
$env:FEATURE_OCR_PIPELINE_V2 = "true"
$env:PYTHONPATH = $ROOT
$env:PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION = "python"

# Start Backend
Write-Host "[5/6] Starting Backend on port 8000..." -ForegroundColor Yellow
$backendScript = @"
cd '$ROOT'
`$env:OWLIN_ENV='dev'
`$env:FEATURE_OCR_PIPELINE_V2='true'
`$env:PYTHONPATH='$ROOT'
`$env:PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION='python'
Write-Host '=== BACKEND SERVER (Port 8000) ===' -ForegroundColor Green
Write-Host ''
'$pythonExe' -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
"@

Start-Process powershell -ArgumentList @("-NoExit", "-Command", $backendScript)
Start-Sleep -Seconds 5

# Start Frontend
Write-Host "[6/6] Starting Frontend on port 5176..." -ForegroundColor Yellow
$frontendScript = @"
cd '$frontendDir'
Write-Host '=== FRONTEND SERVER (Port 5176) ===' -ForegroundColor Cyan
Write-Host ''
npm run dev
"@

Start-Process powershell -ArgumentList @("-NoExit", "-Command", $frontendScript)

Write-Host ""
Write-Host "Waiting 25 seconds for servers to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 25

# Test connections
Write-Host ""
Write-Host "Testing connections..." -ForegroundColor Cyan
Write-Host ""

$backendOk = $false
$frontendOk = $false

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
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
    Write-Host "   ⚠ Check the server windows for errors" -ForegroundColor Yellow
    Write-Host "   Then try: http://localhost:5176" -ForegroundColor Cyan
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
