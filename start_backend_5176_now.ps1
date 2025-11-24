# Start Backend on Port 5176
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Starting Backend on Port 5176" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ROOT

# Kill any existing process on port 5176
Write-Host "[1/5] Checking for existing processes on port 5176..." -ForegroundColor Yellow
$connections = Get-NetTCPConnection -LocalPort 5176 -State Listen -ErrorAction SilentlyContinue
if ($connections) {
    $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($processId in $pids) {
        Write-Host "  Stopping process $processId..." -ForegroundColor Yellow
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

# Check virtual environment
Write-Host "[2/5] Checking virtual environment..." -ForegroundColor Yellow
$venvPath = Join-Path $ROOT ".venv\Scripts\activate.bat"
if (-not (Test-Path $venvPath)) {
    Write-Host "  [ERROR] Virtual environment not found at .venv\Scripts\activate.bat" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] Virtual environment found" -ForegroundColor Green

# Set environment variables
Write-Host "[3/5] Setting environment variables..." -ForegroundColor Yellow
$env:OWLIN_ENV = "dev"
$env:FEATURE_OCR_PIPELINE_V2 = "true"
$env:PYTHONPATH = $ROOT

# Ensure directories exist
Write-Host "[4/5] Ensuring directories exist..." -ForegroundColor Yellow
$dirs = @("data", "data\uploads", "data\logs")
foreach ($dir in $dirs) {
    $fullPath = Join-Path $ROOT $dir
    if (-not (Test-Path $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
        Write-Host "  Created: $dir" -ForegroundColor Gray
    }
}

# Start backend
Write-Host "[5/5] Starting backend on port 5176..." -ForegroundColor Yellow
$pythonExe = Join-Path $ROOT ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Host "  [ERROR] Python executable not found at $pythonExe" -ForegroundColor Red
    exit 1
}

# Start in a new window
Start-Process -FilePath $pythonExe -ArgumentList "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "5176", "--reload" -WorkingDirectory $ROOT -WindowStyle Normal

Write-Host ""
Write-Host "Backend starting in new window..." -ForegroundColor Green
Write-Host "Waiting 8 seconds for backend to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 8

# Test if it's working
Write-Host ""
Write-Host "Testing endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5176/invoices?dev=1" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Host "  [SUCCESS] Backend is running on port 5176!" -ForegroundColor Green
    Write-Host "  Status Code: $($response.StatusCode)" -ForegroundColor Gray
    Write-Host "  Response length: $($response.Content.Length) bytes" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Access at: http://localhost:5176/invoices?dev=1" -ForegroundColor Cyan
} catch {
    Write-Host "  [WARN] Backend may still be starting..." -ForegroundColor Yellow
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Gray
    Write-Host "  Try accessing: http://localhost:5176/invoices?dev=1 in a few seconds" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan

