# Auto-restart Uvicorn for OCR debugging
# Keeps backend alive even if it crashes

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "  OWLIN BACKEND AUTO-RESTART" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend will auto-restart if it crashes" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

$restartCount = 0

while ($true) {
    if ($restartCount -gt 0) {
        Write-Host ""
        Write-Host "💥 Backend crashed (restart #$restartCount). Restarting in 3s..." -ForegroundColor Red
        Start-Sleep 3
    }
    
    Write-Host ""
    Write-Host "🚀 Starting Owlin backend (port 8000)..." -ForegroundColor Green
    Write-Host "   URL: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "   Health: http://localhost:8000/api/health" -ForegroundColor Cyan
    Write-Host "   OCR Test: http://localhost:8000/api/dev/ocr-test?list_uploads=true" -ForegroundColor Cyan
    Write-Host ""
    
    try {
        & python -m uvicorn backend.main:app --port 8000 --reload
    } catch {
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    $restartCount++
}

