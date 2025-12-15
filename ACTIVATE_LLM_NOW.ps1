# Activate LLM-First Invoice Extraction
# PowerShell version

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Activating LLM-First Invoice Extraction" -ForegroundColor Yellow
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[Step 1] Running LLM diagnostics..." -ForegroundColor Green
python check_llm.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] LLM diagnostics failed!" -ForegroundColor Red
    Write-Host "Please fix the issues above before continuing." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "[Step 2] LLM extraction is now ENABLED by default in config.py" -ForegroundColor Green
Write-Host "         FEATURE_LLM_EXTRACTION = True" -ForegroundColor White
Write-Host ""

Write-Host "[Step 3] Clearing OCR cache..." -ForegroundColor Green
if (Test-Path "clear_ocr_cache.py") {
    python clear_ocr_cache.py --all
} else {
    Write-Host "No cache clear script found, skipping..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  LLM Extraction is Ready!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next step: Restart your backend" -ForegroundColor Yellow
Write-Host "  - Run: .\start_backend_5176.bat" -ForegroundColor White
Write-Host "  - Or restart your existing backend terminal" -ForegroundColor White
Write-Host ""
Write-Host "Then upload an invoice and watch 'Unknown Item' disappear!" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to continue"

