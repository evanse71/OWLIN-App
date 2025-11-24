# Fix Port 5176 - Stop Backend and Start Frontend
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Fixing Port 5176 Configuration" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Kill any process on port 5176
Write-Host "[1/4] Stopping any process on port 5176..." -ForegroundColor Yellow
$connections = Get-NetTCPConnection -LocalPort 5176 -State Listen -ErrorAction SilentlyContinue
if ($connections) {
    $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($pid in $pids) {
        Write-Host "  Killing process $pid..." -ForegroundColor Yellow
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

# Verify port 5176 is free
$stillRunning = Get-NetTCPConnection -LocalPort 5176 -State Listen -ErrorAction SilentlyContinue
if ($stillRunning) {
    Write-Host "  [WARN] Port 5176 still in use. Trying to kill all Python processes..." -ForegroundColor Red
    Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# Step 2: Verify backend is on port 8000
Write-Host ""
Write-Host "[2/4] Checking backend on port 8000..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "  [OK] Backend is running on port 8000" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Backend not running on port 8000" -ForegroundColor Red
    Write-Host "  Please start the backend with: start_backend_8000.bat" -ForegroundColor Yellow
}

# Step 3: Start frontend on port 5176
Write-Host ""
Write-Host "[3/4] Starting frontend on port 5176..." -ForegroundColor Yellow

$frontendDir = Join-Path $PSScriptRoot "source_extracted\tmp_lovable"
if (-not (Test-Path $frontendDir)) {
    Write-Host "  [ERROR] Frontend directory not found: $frontendDir" -ForegroundColor Red
    Write-Host "  Trying alternative: frontend_clean" -ForegroundColor Yellow
    $frontendDir = Join-Path $PSScriptRoot "frontend_clean"
}

if (Test-Path $frontendDir) {
    Push-Location $frontendDir
    
    if (-not (Test-Path "node_modules")) {
        Write-Host "  Installing dependencies..." -ForegroundColor Yellow
        npm install
    }
    
    Write-Host "  Starting Vite dev server on port 5176..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "   Frontend Starting..." -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Once you see 'Local: http://localhost:5176/'," -ForegroundColor Green
    Write-Host "open: http://localhost:5176/invoices?dev=1" -ForegroundColor Green
    Write-Host ""
    
    npm run dev
} else {
    Write-Host "  [ERROR] Frontend directory not found!" -ForegroundColor Red
    Write-Host "  Expected: $frontendDir" -ForegroundColor Yellow
    Pop-Location
    exit 1
}

