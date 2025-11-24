# PowerShell script to start Owlin on port 5176
$ErrorActionPreference = "Stop"
$ROOT = $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   🦉 OWLIN - Complete Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting Backend (port 8000) and Frontend (port 5176)" -ForegroundColor Yellow
Write-Host ""

# Check if ports are in use
Write-Host "[CHECK] Checking if ports are available..." -ForegroundColor Yellow
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
$port5176 = Get-NetTCPConnection -LocalPort 5176 -ErrorAction SilentlyContinue

if ($port8000) {
    Write-Host "[WARN] Port 8000 is already in use!" -ForegroundColor Red
    Write-Host "       Killing processes on port 8000..." -ForegroundColor Yellow
    $port8000 | ForEach-Object {
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

if ($port5176) {
    Write-Host "[WARN] Port 5176 is already in use!" -ForegroundColor Red
    Write-Host "       Killing processes on port 5176..." -ForegroundColor Yellow
    Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# Kill any existing node/python processes
Write-Host "[CLEANUP] Killing stale processes..." -ForegroundColor Yellow
Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

# Start Backend
Write-Host ""
Write-Host "[1/4] Starting Backend on port 8000..." -ForegroundColor Green
if (-not (Test-Path "$ROOT\.venv\Scripts\activate.bat")) {
    Write-Host "[ERROR] Virtual environment not found at .venv\Scripts\activate.bat" -ForegroundColor Red
    Write-Host "        Please create a virtual environment first!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

$backendScript = @"
cd /d $ROOT
call .venv\Scripts\activate.bat
set PYTHONPATH=$ROOT
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
pause
"@

Start-Process cmd -ArgumentList "/k", $backendScript -WindowStyle Normal

# Wait for backend to start
Write-Host "[2/4] Waiting for backend to start..." -ForegroundColor Yellow
Write-Host "       (This may take 10-15 seconds for first startup)" -ForegroundColor Gray
$BACKEND_READY = $false
for ($i = 1; $i -le 45; $i++) {
    Start-Sleep -Seconds 1
    try {
        # Try both localhost and 127.0.0.1
        $uris = @("http://localhost:8000/api/health", "http://127.0.0.1:8000/api/health")
        $success = $false
        foreach ($uri in $uris) {
            try {
                $response = Invoke-WebRequest -Uri $uri -TimeoutSec 2 -ErrorAction Stop
                if ($response.StatusCode -eq 200) {
                    $BACKEND_READY = $true
                    $success = $true
                    break
                }
            } catch {
                # Try next URI
            }
        }
        if ($success) {
            Write-Host "[OK] Backend is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Continue waiting
    }
    if ($i % 5 -eq 0) {
        Write-Host "        Still waiting... ($i seconds) - Check backend window for errors" -ForegroundColor Yellow
    } else {
        Write-Host "        Waiting... ($i seconds)" -ForegroundColor Gray
    }
}

if (-not $BACKEND_READY) {
    Write-Host "[ERROR] Backend failed to start after 45 seconds" -ForegroundColor Red
    Write-Host "" -ForegroundColor Red
    Write-Host "Troubleshooting steps:" -ForegroundColor Yellow
    Write-Host "1. Check the backend window (should be open) for any error messages" -ForegroundColor White
    Write-Host "2. Try manually starting backend: .\start_backend_8000.bat" -ForegroundColor White
    Write-Host "3. Check if port 8000 is in use: netstat -an | findstr :8000" -ForegroundColor White
    Write-Host "4. Check backend_stdout.log for errors" -ForegroundColor White
    Write-Host "" -ForegroundColor Red
    Write-Host "The backend window should show:" -ForegroundColor Cyan
    Write-Host "  'INFO: Uvicorn running on http://0.0.0.0:8000'" -ForegroundColor Gray
    Write-Host "" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Start Frontend
Write-Host ""
Write-Host "[3/4] Starting Frontend on port 5176..." -ForegroundColor Green
$frontendDir = "$ROOT\frontend_clean"

if (-not (Test-Path "$frontendDir\package.json")) {
    Write-Host "[ERROR] Frontend directory not found!" -ForegroundColor Red
    Write-Host "        Expected: $frontendDir" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if node_modules exists
if (-not (Test-Path "$frontendDir\node_modules")) {
    Write-Host "[WARN] node_modules not found. Installing dependencies..." -ForegroundColor Yellow
    Push-Location $frontendDir
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] npm install failed!" -ForegroundColor Red
        Pop-Location
        Read-Host "Press Enter to exit"
        exit 1
    }
    Pop-Location
}

$frontendScript = @"
cd /d $frontendDir
echo Starting original Owlin frontend on port 5176...
npm run dev
pause
"@

Start-Process cmd -ArgumentList "/k", $frontendScript -WindowStyle Normal

# Wait for frontend to start
Write-Host "[4/4] Waiting for frontend to start..." -ForegroundColor Yellow
$FRONTEND_READY = $false
for ($i = 1; $i -le 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5176" -TimeoutSec 1 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $FRONTEND_READY = $true
            Write-Host "[OK] Frontend is ready!" -ForegroundColor Green
            break
        }
    } catch {
        Write-Host "        Waiting... ($i seconds)" -ForegroundColor Gray
    }
}

# Final status
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   🎉 OWLIN IS READY!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ Backend:  http://localhost:8000" -ForegroundColor Green
Write-Host "✅ Frontend: http://localhost:5176/invoices?dev=1" -ForegroundColor Green
Write-Host ""

if ($FRONTEND_READY) {
    Write-Host "Opening browser..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    Start-Process "http://localhost:5176/invoices?dev=1"
} else {
    Write-Host "[WARN] Frontend may still be starting. Check the frontend window." -ForegroundColor Yellow
    Write-Host "       You can manually open: http://localhost:5176/invoices?dev=1" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Two windows are open:" -ForegroundColor Cyan
Write-Host "1. Backend (port 8000) - Keep this running" -ForegroundColor White
Write-Host "2. Frontend (port 5176) - Keep this running" -ForegroundColor White
Write-Host ""
Write-Host "If you see 'Backend is offline' in the browser:" -ForegroundColor Yellow
Write-Host "- Wait a few more seconds for backend to fully start" -ForegroundColor White
Write-Host "- Check the backend window for any errors" -ForegroundColor White
Write-Host "- Try refreshing the page" -ForegroundColor White
Write-Host ""
Read-Host "Press Enter to exit"

