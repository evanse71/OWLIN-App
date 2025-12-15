# Test Backend Connection
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Testing Backend Connection" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if port 8000 is listening
Write-Host "1. Checking if port 8000 is listening..." -ForegroundColor Yellow
$port = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($port) {
    Write-Host "   [OK] Port 8000 is listening" -ForegroundColor Green
} else {
    Write-Host "   [FAIL] Port 8000 is NOT listening" -ForegroundColor Red
    Write-Host "   Backend is not running!" -ForegroundColor Red
    Write-Host ""
    Write-Host "   To start the backend, run:" -ForegroundColor Yellow
    Write-Host "   .\start_backend_now.ps1" -ForegroundColor White
    exit 1
}

Write-Host ""

# Test routes status endpoint
Write-Host "2. Testing /api/routes/status endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/routes/status" -Method GET -TimeoutSec 5
    Write-Host "   [OK] Backend is responding!" -ForegroundColor Green
    Write-Host "   Total Routes: $($response.total_routes)" -ForegroundColor Gray
    Write-Host "   Chat Router Loaded: $($response.chat_router_loaded)" -ForegroundColor Gray
    Write-Host "   Chat Endpoint Available: $($response.chat_endpoint_available)" -ForegroundColor Gray
} catch {
    Write-Host "   [FAIL] Backend not responding: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Test chat status endpoint
Write-Host "3. Testing /api/chat/status endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/chat/status" -Method GET -TimeoutSec 5
    Write-Host "   [OK] Chat endpoint is accessible!" -ForegroundColor Green
    Write-Host "   Status: $($response.status)" -ForegroundColor Gray
    Write-Host "   Ollama Available: $($response.ollama_available)" -ForegroundColor Gray
} catch {
    Write-Host "   [WARN] Chat endpoint error: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "   This might be OK if Ollama is not running" -ForegroundColor Gray
}

Write-Host ""

# Test invoices endpoint
Write-Host "4. Testing /api/invoices endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/invoices?dev=1" -Method GET -TimeoutSec 5
    Write-Host "   [OK] Invoices endpoint is accessible!" -ForegroundColor Green
    Write-Host "   Returned $($response.Count) invoices" -ForegroundColor Gray
} catch {
    Write-Host "   [WARN] Invoices endpoint error: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Backend Status: READY" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Frontend should now be able to connect!" -ForegroundColor Green
Write-Host "Access at: http://localhost:5176" -ForegroundColor Yellow
Write-Host ""
