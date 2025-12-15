# Verify Servers Status
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Verifying Server Status" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Backend (Port 8000)
Write-Host "Checking Backend (Port 8000)..." -ForegroundColor Yellow
$backendPort = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($backendPort) {
    Write-Host "  [OK] Port 8000 is listening" -ForegroundColor Green
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/invoices?dev=1" -Method GET -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        Write-Host "  [OK] Backend API responding (Status: $($response.StatusCode))" -ForegroundColor Green
    } catch {
        Write-Host "  [WARN] Port open but API not responding: $($_.Exception.Message)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [FAIL] Backend not running on port 8000" -ForegroundColor Red
}

Write-Host ""

# Check Frontend (Port 5176)
Write-Host "Checking Frontend (Port 5176)..." -ForegroundColor Yellow
$frontendPort = Get-NetTCPConnection -LocalPort 5176 -State Listen -ErrorAction SilentlyContinue
if ($frontendPort) {
    Write-Host "  [OK] Port 5176 is listening" -ForegroundColor Green
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:5176" -Method GET -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        Write-Host "  [OK] Frontend responding (Status: $($response.StatusCode))" -ForegroundColor Green
    } catch {
        Write-Host "  [WARN] Port open but frontend not responding: $($_.Exception.Message)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [FAIL] Frontend not running on port 5176" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Access URLs:" -ForegroundColor Cyan
Write-Host "   Frontend: http://localhost:5176" -ForegroundColor Yellow
Write-Host "   Backend API: http://localhost:8000/api" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
