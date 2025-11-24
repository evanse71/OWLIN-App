# Restart backend to load new mega upgrade routes
Write-Host "Restarting backend for Code Assistant Mega Upgrade..." -ForegroundColor Cyan

# Kill all Python processes on port 8000
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port8000) {
    Write-Host "Stopping processes on port 8000..." -ForegroundColor Yellow
    $port8000 | ForEach-Object {
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

# Clear Python cache
Write-Host "Clearing Python cache..." -ForegroundColor Yellow
Get-ChildItem -Path backend -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue | Remove-Item -Force
Get-ChildItem -Path backend -Recurse -Filter "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force

# Start backend
Write-Host "Starting backend..." -ForegroundColor Green
Set-Location backend
Start-Process python -ArgumentList "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload" -WindowStyle Hidden

Start-Sleep -Seconds 5

# Test endpoints
Write-Host "`nTesting new endpoints..." -ForegroundColor Cyan
$endpoints = @(
    "/api/chat/config",
    "/api/chat/models", 
    "/api/chat/metrics",
    "/api/chat/quality"
)

foreach ($endpoint in $endpoints) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000$endpoint" -TimeoutSec 5 -ErrorAction Stop
        Write-Host "  [OK] $endpoint" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] $endpoint - $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`nBackend restarted. New routes should be available." -ForegroundColor Green
Set-Location ..

