# Start Backend with Python 3.11
# Run this after setup_python311.ps1

Write-Host "🚀 Starting Owlin Backend with Python 3.11..." -ForegroundColor Green

# Activate Python 3.11 venv
if (-not (Test-Path ".venv311\Scripts\Activate.ps1")) {
    Write-Host "❌ Python 3.11 venv not found! Run setup_python311.ps1 first" -ForegroundColor Red
    exit 1
}

& .\.venv311\Scripts\Activate.ps1

# Verify PaddleOCR
Write-Host "`n[CHECK] Verifying PaddleOCR..." -ForegroundColor Yellow
python -c "from paddleocr import PaddleOCR; print('✅ PaddleOCR ready')" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  PaddleOCR check failed, but continuing..." -ForegroundColor Yellow
}

# Start backend
Write-Host "`n[START] Starting Uvicorn on port 8000..." -ForegroundColor Yellow
Write-Host "  → Backend will auto-reload on code changes" -ForegroundColor Cyan
Write-Host "  → Press Ctrl+C to stop`n" -ForegroundColor Cyan

python -m uvicorn backend.main:app --port 8000 --reload --host 0.0.0.0

