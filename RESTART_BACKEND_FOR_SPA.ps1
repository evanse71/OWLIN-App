# Restart Backend to Enable SPA Mode
Write-Host "===================================" -ForegroundColor Cyan
Write-Host "Restarting Backend for SPA Mode" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

# Kill any processes on port 8000
Write-Host "[1/3] Stopping existing backend processes..." -ForegroundColor Yellow
$conn = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($conn) {
    $conn | ForEach-Object {
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        Write-Host "  Stopped process PID: $($_.OwningProcess)" -ForegroundColor Gray
    }
    Start-Sleep -Seconds 2
} else {
    Write-Host "  No processes found on port 8000" -ForegroundColor Gray
}

# Verify static files
Write-Host ""
Write-Host "[2/3] Verifying static files..." -ForegroundColor Yellow
$staticIndex = "backend\static\index.html"
$staticAssets = "backend\static\assets"

if (Test-Path $staticIndex) {
    Write-Host "  ✓ index.html found" -ForegroundColor Green
} else {
    Write-Host "  ✗ index.html MISSING!" -ForegroundColor Red
    exit 1
}

if (Test-Path $staticAssets) {
    $assetCount = (Get-ChildItem $staticAssets -File).Count
    Write-Host "  ✓ assets directory found ($assetCount files)" -ForegroundColor Green
} else {
    Write-Host "  ✗ assets directory MISSING!" -ForegroundColor Red
    exit 1
}

# Start backend
Write-Host ""
Write-Host "[3/3] Starting backend..." -ForegroundColor Yellow
Set-Location backend

# Check for virtual environment
$venv = "..\.venv\Scripts\Activate.ps1"
if (Test-Path $venv) {
    Write-Host "  Activating virtual environment..." -ForegroundColor Gray
    & $venv
}

# Start backend with reload
Write-Host "  Starting uvicorn on port 8000..." -ForegroundColor Gray
Start-Process python -ArgumentList "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload" -WindowStyle Normal

Set-Location ..

# Wait for backend to start
Write-Host ""
Write-Host "Waiting for backend to start..." -ForegroundColor Yellow
$maxWait = 10
$waited = 0
$ready = $false

while ($waited -lt $maxWait) {
    Start-Sleep -Seconds 1
    $waited++
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        # Still waiting
    }
    Write-Host "  Waiting... ($waited/$maxWait)" -ForegroundColor Gray
}

if ($ready) {
    Write-Host ""
    Write-Host "✓ Backend is ready!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Frontend should now be available at:" -ForegroundColor Cyan
    Write-Host "  http://localhost:8000" -ForegroundColor White
    Write-Host "  http://localhost:8000/invoices" -ForegroundColor White
    Write-Host ""
    Write-Host "Open your browser and navigate to the URL above." -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "✗ Backend failed to start after $maxWait seconds" -ForegroundColor Red
    Write-Host "  Check the backend window for errors" -ForegroundColor Yellow
}

