# Quick Start for PowerShell Users
# Run this: .\START_HERE.ps1

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   🦉 OWLIN Quick Start (PowerShell)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "frontend_clean\package.json")) {
    Write-Host "[ERROR] Please run this from the project root directory!" -ForegroundColor Red
    Write-Host "        Current directory: $PWD" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Choose an option:" -ForegroundColor Yellow
Write-Host "1. Start everything (Backend + Frontend)" -ForegroundColor White
Write-Host "2. Start Backend only (port 8000)" -ForegroundColor White
Write-Host "3. Start Frontend only (port 5176)" -ForegroundColor White
Write-Host "4. Check port status" -ForegroundColor White
Write-Host ""
$choice = Read-Host "Enter choice (1-4)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "Starting everything..." -ForegroundColor Green
        & ".\Start-Owlin-5176.ps1"
    }
    "2" {
        Write-Host ""
        Write-Host "Starting backend on port 8000..." -ForegroundColor Green
        if (-not (Test-Path ".venv\Scripts\activate.bat")) {
            Write-Host "[ERROR] Virtual environment not found!" -ForegroundColor Red
            Read-Host "Press Enter to exit"
            exit 1
        }
        $script = @"
cd /d $PWD
call .venv\Scripts\activate.bat
set PYTHONPATH=$PWD
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
pause
"@
        Start-Process cmd -ArgumentList "/k", $script
        Write-Host "[OK] Backend window opened. Wait for 'Uvicorn running on http://0.0.0.0:8000'" -ForegroundColor Green
    }
    "3" {
        Write-Host ""
        Write-Host "Starting frontend on port 5176..." -ForegroundColor Green
        Push-Location "frontend_clean"
        Write-Host "Running: npm run dev" -ForegroundColor Yellow
        npm run dev
        Pop-Location
    }
    "4" {
        Write-Host ""
        & ".\Check-Ports.ps1"
    }
    default {
        Write-Host "[ERROR] Invalid choice" -ForegroundColor Red
    }
}

