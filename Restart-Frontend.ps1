# Restart Frontend on Port 5176
Write-Host "Restarting Frontend on port 5176..." -ForegroundColor Yellow

# Kill existing node processes
Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Start frontend
Push-Location "frontend_clean"

Write-Host "Starting original Owlin frontend..." -ForegroundColor Green
Write-Host "Frontend will be at: http://127.0.0.1:5176/invoices?dev=1" -ForegroundColor Cyan
Write-Host ""

npm run dev

