# Verify Owlin App is Running
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Verifying Owlin App Status" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Backend
Write-Host "Checking Backend (port 8000)..." -ForegroundColor Yellow
try {
    $backend = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 3
    Write-Host "  ✅ Backend is running! Status: $($backend.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Backend is not responding" -ForegroundColor Red
    Write-Host "     Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Check Frontend
Write-Host "Checking Frontend (port 5176)..." -ForegroundColor Yellow
try {
    $frontend = Invoke-WebRequest -Uri "http://127.0.0.1:5176" -UseBasicParsing -TimeoutSec 3
    Write-Host "  ✅ Frontend is running! Status: $($frontend.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Frontend is not responding" -ForegroundColor Red
    Write-Host "     Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Check Invoices Page
Write-Host "Checking Invoices Page..." -ForegroundColor Yellow
try {
    $invoices = Invoke-WebRequest -Uri "http://127.0.0.1:5176/invoices" -UseBasicParsing -TimeoutSec 3
    Write-Host "  ✅ Invoices page is accessible! Status: $($invoices.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "  ⚠️  Invoices page check: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   App URL: http://localhost:5176/invoices" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
