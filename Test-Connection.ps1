# Test connections to Owlin services
Write-Host "Testing Owlin Connections..." -ForegroundColor Cyan
Write-Host ""

# Test Backend
Write-Host "Testing Backend (port 8000)..." -ForegroundColor Yellow
try {
    $backend = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -TimeoutSec 2 -UseBasicParsing
    Write-Host "[OK] Backend is responding!" -ForegroundColor Green
    Write-Host "     Status: $($backend.StatusCode)" -ForegroundColor Gray
} catch {
    Write-Host "[FAIL] Backend is not responding" -ForegroundColor Red
    Write-Host "       Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Test Frontend
Write-Host "Testing Frontend (port 5176)..." -ForegroundColor Yellow
try {
    $frontend = Invoke-WebRequest -Uri "http://127.0.0.1:5176" -TimeoutSec 2 -UseBasicParsing
    Write-Host "[OK] Frontend is responding!" -ForegroundColor Green
    Write-Host "     Status: $($frontend.StatusCode)" -ForegroundColor Gray
} catch {
    Write-Host "[FAIL] Frontend is not responding" -ForegroundColor Red
    Write-Host "       Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Trying localhost instead..." -ForegroundColor Yellow
    try {
        $frontend2 = Invoke-WebRequest -Uri "http://localhost:5176" -TimeoutSec 2 -UseBasicParsing
        Write-Host "[OK] Frontend responds on localhost!" -ForegroundColor Green
    } catch {
        Write-Host "[FAIL] Frontend not responding on localhost either" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Port Status:" -ForegroundColor Cyan
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
$port5176 = Get-NetTCPConnection -LocalPort 5176 -ErrorAction SilentlyContinue

if ($port8000) {
    Write-Host "Port 8000: LISTENING" -ForegroundColor Green
} else {
    Write-Host "Port 8000: NOT LISTENING" -ForegroundColor Red
}

if ($port5176) {
    Write-Host "Port 5176: LISTENING" -ForegroundColor Green
} else {
    Write-Host "Port 5176: NOT LISTENING" -ForegroundColor Red
}

Write-Host ""
Read-Host "Press Enter to exit"

