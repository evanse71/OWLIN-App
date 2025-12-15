# Backend Verification Script
Write-Host "`n🔍 Backend Verification Script" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Check if backend is running
Write-Host "`n1. Checking if backend is running..." -ForegroundColor Yellow
try {
    $health = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -Method GET -TimeoutSec 2 -ErrorAction Stop
    Write-Host "   ✅ Backend is running (Status: $($health.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Backend is NOT running" -ForegroundColor Red
    Write-Host "   Please start it with: python -m uvicorn backend.main:app --port 8000 --reload" -ForegroundColor Yellow
    exit
}

# Test new endpoints
Write-Host "`n2. Testing new endpoints..." -ForegroundColor Yellow

# Test path resolution endpoint
try {
    $test = Invoke-WebRequest -Uri "http://localhost:8000/api/test/path-resolution" -Method GET -TimeoutSec 3 -ErrorAction Stop
    Write-Host "   ✅ Test endpoint works! (NEW code loaded)" -ForegroundColor Green
    $data = $test.Content | ConvertFrom-Json
    Write-Host "      Data uploads exists: $($data.data_uploads_exists)" -ForegroundColor $(if ($data.data_uploads_exists) { "Green" } else { "Red" })
} catch {
    Write-Host "   ❌ Test endpoint not found (OLD code running)" -ForegroundColor Red
    Write-Host "   Backend needs to be restarted!" -ForegroundColor Yellow
}

# Test image endpoint
Write-Host "`n3. Testing image endpoint..." -ForegroundColor Yellow
$testDocId = "3a11b936-5ce0-4035-a0e9-6e1abfa7863b"
try {
    $img = Invoke-WebRequest -Uri "http://localhost:8000/api/ocr/page-image/$testDocId" -Method GET -TimeoutSec 3 -ErrorAction Stop
    Write-Host "   ✅ Image endpoint works! (Status: $($img.StatusCode))" -ForegroundColor Green
} catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 404) {
        Write-Host "   ❌ Image endpoint returns 404" -ForegroundColor Red
        Write-Host "   Check backend terminal for [PAGE_IMAGE] logs" -ForegroundColor Yellow
    } else {
        Write-Host "   ⚠️  Image endpoint error: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Host "`n✅ Verification complete!" -ForegroundColor Green
Write-Host "`nIf endpoints are not working, restart backend:" -ForegroundColor Cyan
Write-Host "   1. Stop backend (Ctrl+C)" -ForegroundColor White
Write-Host "   2. Run: python -m uvicorn backend.main:app --port 8000 --reload" -ForegroundColor Yellow

