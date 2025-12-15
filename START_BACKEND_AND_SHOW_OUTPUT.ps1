# PowerShell script to start backend and show output
cd "C:\Users\tedev\FixPack_2025-11-02_133105"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Starting Owlin Backend on Port 8000" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Activate virtual environment
Write-Host "[1/4] Activating virtual environment..." -ForegroundColor Yellow
& ".\.venv\Scripts\Activate.ps1"

# Set environment variables
Write-Host "[2/4] Setting environment variables..." -ForegroundColor Yellow
$env:OWLIN_ENV = "dev"
$env:FEATURE_OCR_PIPELINE_V2 = "true"
$env:PYTHONPATH = $PWD.Path

# Ensure directories exist
Write-Host "[3/4] Ensuring directories exist..." -ForegroundColor Yellow
if (-not (Test-Path "data")) { New-Item -ItemType Directory -Path "data" | Out-Null }
if (-not (Test-Path "data\uploads")) { New-Item -ItemType Directory -Path "data\uploads" | Out-Null }
if (-not (Test-Path "data\logs")) { New-Item -ItemType Directory -Path "data\logs" | Out-Null }

# Start backend
Write-Host "[4/4] Starting backend on port 8000..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Backend will start now. Look for:" -ForegroundColor Green
Write-Host "  INFO:     Uvicorn running on http://0.0.0.0:8000" -ForegroundColor Green
Write-Host "  INFO:     Application startup complete." -ForegroundColor Green
Write-Host ""
Write-Host "If you see errors, copy the full traceback and share it." -ForegroundColor Yellow
Write-Host "Press CTRL+C to stop the server." -ForegroundColor Yellow
Write-Host ""

python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

