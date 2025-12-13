# OWLIN - Desktop Launcher for Windows PowerShell
# Double-click this file to start the full Owlin development environment

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  OWLIN - Full Development Launcher" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "package.json")) {
    Write-Host "ERROR: package.json not found!" -ForegroundColor Red
    Write-Host "Please run this from the Owlin project root directory." -ForegroundColor Red
    Read-Host "Press Enter to continue"
    exit 1
}

if (-not (Test-Path "backend/final_single_port.py")) {
    Write-Host "ERROR: backend/final_single_port.py not found!" -ForegroundColor Red
    Write-Host "Please run this from the Owlin project root directory." -ForegroundColor Red
    Read-Host "Press Enter to continue"
    exit 1
}

Write-Host "Starting Owlin development environment..." -ForegroundColor Green
Write-Host ""

# Start Next.js in a new PowerShell window
Write-Host "[1/2] Starting Next.js frontend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; npm run dev" -WindowStyle Normal

# Wait a moment for Next.js to start
Start-Sleep -Seconds 5

# Start FastAPI backend in a new PowerShell window
Write-Host "[2/2] Starting FastAPI backend with proxy..." -ForegroundColor Yellow
$envCommand = @"
cd '$PWD'
`$env:UI_MODE='PROXY_NEXT'
`$env:NEXT_BASE='http://127.0.0.1:3000'
`$env:LLM_BASE='http://127.0.0.1:11434'
`$env:OWLIN_PORT='8001'
python -m backend.final_single_port
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $envCommand -WindowStyle Normal

# Wait a moment for backend to start
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  SUCCESS! Owlin is starting up..." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Frontend: http://127.0.0.1:3000" -ForegroundColor White
Write-Host "Backend:  http://127.0.0.1:8001" -ForegroundColor White
Write-Host ""
Write-Host "Opening the app in your browser..." -ForegroundColor Yellow
Write-Host ""

# Open the app in the default browser
Start-Process "http://127.0.0.1:8001"

Write-Host ""
Write-Host "Both services are starting in separate PowerShell windows." -ForegroundColor Cyan
Write-Host "Close those windows to stop the services." -ForegroundColor Cyan
Write-Host ""
Read-Host "Press Enter to close this launcher"
