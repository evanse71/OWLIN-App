# Quick Frontend Status Check
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Frontend & Backend Status" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Frontend (port 5176)
$frontend = Get-NetTCPConnection -LocalPort 5176 -ErrorAction SilentlyContinue
if ($frontend) {
    Write-Host "✓ Frontend dev server: RUNNING on port 5176" -ForegroundColor Green
    try {
        $test = Invoke-WebRequest -Uri "http://localhost:5176" -TimeoutSec 2 -ErrorAction Stop
        Write-Host "  → Serving HTML content" -ForegroundColor Gray
    } catch {
        Write-Host "  → Not responding properly" -ForegroundColor Yellow
    }
} else {
    Write-Host "✗ Frontend dev server: NOT RUNNING" -ForegroundColor Red
    Write-Host "  → Start it with: cd source_extracted\tmp_lovable && npm run dev" -ForegroundColor Yellow
}

Write-Host ""

# Check Backend (port 8000)
$backend = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($backend) {
    Write-Host "✓ Backend API: RUNNING on port 8000" -ForegroundColor Green
    try {
        $test = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -TimeoutSec 2 -ErrorAction Stop
        Write-Host "  → Health check OK" -ForegroundColor Gray
    } catch {
        Write-Host "  → Health check failed" -ForegroundColor Yellow
    }
} else {
    Write-Host "✗ Backend API: NOT RUNNING" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CORRECT URL TO ACCESS:" -ForegroundColor Yellow
Write-Host "  http://localhost:5176/invoices" -ForegroundColor Cyan
Write-Host ""
Write-Host "WRONG URL (will show JSON):" -ForegroundColor Red
Write-Host "  http://localhost:8000/invoices" -ForegroundColor Red
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "If you still see JSON:" -ForegroundColor Yellow
Write-Host "  1. Make sure you're on port 5176 (NOT 8000)" -ForegroundColor White
Write-Host "  2. Hard refresh: Ctrl+Shift+R" -ForegroundColor White
Write-Host "  3. Clear cache: Ctrl+Shift+Delete" -ForegroundColor White
Write-Host "  4. Try incognito window" -ForegroundColor White
Write-Host ""

