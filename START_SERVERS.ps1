# Start Both Backend and Frontend Servers
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Starting Owlin Development Servers" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ROOT = $PSScriptRoot
if (-not $ROOT) { $ROOT = Get-Location }

Set-Location $ROOT

# Check Python
$pythonExe = Join-Path $ROOT ".venv311\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Host "[ERROR] Python not found at: $pythonExe" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Python found: $pythonExe" -ForegroundColor Green

# Check Node
$nodeExe = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeExe) {
    Write-Host "[ERROR] Node.js not found in PATH" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Node.js found: $($nodeExe.Source)" -ForegroundColor Green

# Check frontend dependencies
$frontendDir = Join-Path $ROOT "frontend_clean"
if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    Write-Host "[INFO] Installing frontend dependencies..." -ForegroundColor Yellow
    Set-Location $frontendDir
    npm install
    Set-Location $ROOT
}

# Set environment variables
$env:OWLIN_ENV = "dev"
$env:FEATURE_OCR_PIPELINE_V2 = "true"
$env:PYTHONPATH = $ROOT
$env:PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION = "python"

# Start Backend
Write-Host ""
Write-Host "Starting Backend on port 8000..." -ForegroundColor Cyan
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
    "& '$pythonExe' -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"
)

Start-Sleep -Seconds 3

# Start Frontend
Write-Host "Starting Frontend on port 5176..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$frontendDir'; " +
    "Write-Host '========================================' -ForegroundColor Cyan; " +
    "Write-Host '   Frontend Server (Port 5176)' -ForegroundColor Cyan; " +
    "Write-Host '========================================' -ForegroundColor Cyan; " +
    "Write-Host ''; " +
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
Write-Host "Waiting 15 seconds for servers to initialize..." -ForegroundColor Yellow
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
    Write-Host "   Please check the PowerShell windows for any errors" -ForegroundColor Yellow
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Open your browser to:" -ForegroundColor Cyan
Write-Host "  http://localhost:5176" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press any key to exit this window (servers will keep running)..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
