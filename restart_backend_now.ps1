# Quick Backend Restart for /invoices fix
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Restarting Backend (Port 5176)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Stop backend
Write-Host "[1/3] Stopping backend..." -ForegroundColor Yellow
$proc = Get-NetTCPConnection -LocalPort 5176 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess
if ($proc) {
    Stop-Process -Id $proc -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Write-Host "  ✓ Backend stopped" -ForegroundColor Green
} else {
    Write-Host "  ℹ No backend running" -ForegroundColor Gray
}

# Wait
Write-Host ""
Write-Host "[2/3] Waiting for port to be released..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

# Start backend
Write-Host ""
Write-Host "[3/3] Starting backend..." -ForegroundColor Yellow
Start-Process -FilePath "start_backend_5176.bat" -WindowStyle Normal
Write-Host "  ✓ Backend started" -ForegroundColor Green

# Wait and test
Write-Host ""
Write-Host "Waiting 12 seconds for backend to fully start..." -ForegroundColor Cyan
Start-Sleep -Seconds 12

Write-Host ""
Write-Host "Testing /invoices endpoint..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5176/invoices" -TimeoutSec 3 -ErrorAction Stop
    if ($response.Content -like '*"invoices"*') {
        Write-Host ""
        Write-Host "✅ SUCCESS! /invoices endpoint is working!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Response preview:" -ForegroundColor Gray
        Write-Host $response.Content.Substring(0, [Math]::Min(300, $response.Content.Length)) -ForegroundColor Gray
    } else {
        Write-Host "⚠️  Backend responded but content unexpected" -ForegroundColor Yellow
    }
} catch {
    Write-Host ""
    Write-Host "❌ Still getting error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "The backend may need more time. Please:" -ForegroundColor Yellow
    Write-Host "1. Wait 10 more seconds" -ForegroundColor White
    Write-Host "2. Test manually: curl http://localhost:5176/invoices" -ForegroundColor White
    Write-Host "3. Check the backend window for any errors" -ForegroundColor White
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan

