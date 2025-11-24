# Quick test script to verify backend is working
Write-Host "Testing Backend Connection..." -ForegroundColor Cyan
Write-Host ""

# Test 1: Check if port is listening
Write-Host "[1/3] Checking if port 8000 is listening..." -ForegroundColor Yellow
$port = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port) {
    Write-Host "       ✅ Port 8000 is in use (PID: $($port.OwningProcess))" -ForegroundColor Green
} else {
    Write-Host "       ❌ Port 8000 is NOT in use - Backend is not running" -ForegroundColor Red
    Write-Host ""
    Write-Host "To start backend manually:" -ForegroundColor Yellow
    Write-Host "  .\start_backend_8000.bat" -ForegroundColor Cyan
    exit 1
}

# Test 2: Check health endpoint
Write-Host "[2/3] Testing /api/health endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "       ✅ Health endpoint responding (Status: $($response.StatusCode))" -ForegroundColor Green
        $content = $response.Content | ConvertFrom-Json
        Write-Host "       Status: $($content.status)" -ForegroundColor Gray
    } else {
        Write-Host "       ⚠️  Health endpoint returned status: $($response.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "       ❌ Health endpoint failed: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "The backend window should show:" -ForegroundColor Yellow
    Write-Host "  'INFO: Uvicorn running on http://0.0.0.0:8000'" -ForegroundColor Gray
    exit 1
}

# Test 3: Check if backend process is running
Write-Host "[3/3] Checking backend process..." -ForegroundColor Yellow
$pythonProcesses = Get-Process -Name python -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    Write-Host "       ✅ Python processes running: $($pythonProcesses.Count)" -ForegroundColor Green
    $pythonProcesses | ForEach-Object {
        Write-Host "          PID: $($_.Id) - Started: $($_.StartTime)" -ForegroundColor Gray
    }
} else {
    Write-Host "       ⚠️  No Python processes found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✅ Backend appears to be working!" -ForegroundColor Green
Write-Host ""
Write-Host "Backend URL: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Health URL:  http://localhost:8000/api/health" -ForegroundColor Cyan
Write-Host ""

