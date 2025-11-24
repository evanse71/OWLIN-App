# PowerShell script to check port status
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Port Status Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Checking port 8000 (Backend)..." -ForegroundColor Yellow
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port8000) {
    Write-Host "[IN USE] Port 8000 is occupied" -ForegroundColor Red
    $port8000 | Format-Table LocalAddress, LocalPort, State, OwningProcess -AutoSize
    $pid = $port8000[0].OwningProcess
    $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Host "Process: $($proc.Name) (PID: $pid)" -ForegroundColor Yellow
    }
} else {
    Write-Host "[FREE] Port 8000 is available" -ForegroundColor Green
}

Write-Host ""
Write-Host "Checking port 5176 (Frontend)..." -ForegroundColor Yellow
$port5176 = Get-NetTCPConnection -LocalPort 5176 -ErrorAction SilentlyContinue
if ($port5176) {
    Write-Host "[IN USE] Port 5176 is occupied" -ForegroundColor Red
    $port5176 | Format-Table LocalAddress, LocalPort, State, OwningProcess -AutoSize
    $pid = $port5176[0].OwningProcess
    $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Host "Process: $($proc.Name) (PID: $pid)" -ForegroundColor Yellow
    }
} else {
    Write-Host "[FREE] Port 5176 is available" -ForegroundColor Green
}

Write-Host ""
Write-Host "Testing backend connection..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "[OK] Backend is responding on port 8000" -ForegroundColor Green
    Write-Host $response.Content
} catch {
    Write-Host "[ERROR] Backend is not responding on port 8000" -ForegroundColor Red
    Write-Host "        Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Testing frontend connection..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5176" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "[OK] Frontend is responding on port 5176" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Frontend is not responding on port 5176" -ForegroundColor Red
    Write-Host "        Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Read-Host "Press Enter to exit"

