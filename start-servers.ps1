# Start OWLIN Servers
$ErrorActionPreference = "Stop"
$ROOT = "c:\Users\tedev\FixPack_2025-11-02_133105"
Set-Location $ROOT

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Starting OWLIN Servers" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Find Python
$pythonExe = $null
if (Test-Path "$ROOT\.venv311\Scripts\python.exe") {
    $pythonExe = "$ROOT\.venv311\Scripts\python.exe"
    Write-Host "[OK] Found Python: .venv311" -ForegroundColor Green
} elseif (Test-Path "$ROOT\.venv\Scripts\python.exe") {
    $pythonExe = "$ROOT\.venv\Scripts\python.exe"
    Write-Host "[OK] Found Python: .venv" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Python virtual environment not found!" -ForegroundColor Red
    exit 1
}

# Check Node
try {
    $nodeVersion = node --version
    Write-Host "[OK] Found Node.js: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Node.js not found!" -ForegroundColor Red
    exit 1
}

# Set environment
$env:OWLIN_ENV = "dev"
$env:FEATURE_OCR_PIPELINE_V2 = "true"
$env:PYTHONPATH = $ROOT
$env:PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION = "python"

# Create directories
@("data", "data\uploads", "data\logs") | ForEach-Object {
    $dir = Join-Path $ROOT $_
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# Kill existing processes
Write-Host ""
Write-Host "Cleaning up existing processes..." -ForegroundColor Yellow
Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*$ROOT*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Start Backend
Write-Host ""
Write-Host "Starting Backend on port 8000..." -ForegroundColor Cyan
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

Start-Sleep -Seconds 3

# Start Frontend
Write-Host "Starting Frontend on port 5176..." -ForegroundColor Cyan
$frontendDir = Join-Path $ROOT "frontend_clean"

# Check/install dependencies
if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Set-Location $frontendDir
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] npm install failed!" -ForegroundColor Red
        exit 1
    }
    Set-Location $ROOT
}

$frontendScript = @"
cd '$frontendDir'
Write-Host '=== FRONTEND SERVER (Port 5176) ===' -ForegroundColor Green
Write-Host ''
npm run dev
"@

Start-Process powershell -ArgumentList @("-NoExit", "-Command", $frontendScript)

Write-Host ""
Write-Host "Waiting 20 seconds for servers to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 20

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
    Write-Host "   ⚠ Check the server windows for errors" -ForegroundColor Yellow
    Write-Host "   Then try: http://localhost:5176" -ForegroundColor Cyan
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
