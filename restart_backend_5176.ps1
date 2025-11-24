# Restart Backend on Port 5176
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Restarting Backend on Port 5176" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Kill any process on port 5176
Write-Host "[1/3] Stopping backend on port 5176..." -ForegroundColor Yellow
$connections = Get-NetTCPConnection -LocalPort 5176 -State Listen -ErrorAction SilentlyContinue
if ($connections) {
    $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($pid in $pids) {
        Write-Host "  Stopping process $pid..." -ForegroundColor Yellow
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
    Write-Host "  [OK] Backend stopped" -ForegroundColor Green
} else {
    Write-Host "  [INFO] No backend running on port 5176" -ForegroundColor Gray
}

# Step 2: Wait a moment
Write-Host ""
Write-Host "[2/3] Waiting for port to be released..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

# Step 3: Start the backend
Write-Host ""
Write-Host "[3/3] Starting backend..." -ForegroundColor Yellow
Start-Process -FilePath "start_backend_5176.bat" -WindowStyle Normal

Write-Host ""
Write-Host "Backend restart initiated!" -ForegroundColor Green
Write-Host "Waiting 5 seconds for backend to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Test if it's working
Write-Host ""
Write-Host "Testing /invoices endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5176/invoices" -TimeoutSec 3 -ErrorAction Stop
    if ($response.Content -like "*invoices*") {
        Write-Host "  [SUCCESS] /invoices endpoint is working!" -ForegroundColor Green
        Write-Host "  Response preview: $($response.Content.Substring(0, [Math]::Min(100, $response.Content.Length)))..." -ForegroundColor Gray
    } else {
        Write-Host "  [WARN] Backend responded but content looks wrong" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [WARN] Backend not responding yet. It may need more time to start." -ForegroundColor Yellow
    Write-Host "  Try accessing: http://localhost:5176/invoices in a few seconds" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan

