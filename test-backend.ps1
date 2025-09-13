# Test Backend API Endpoints
Write-Host "🧪 Testing OWLIN Backend API..." -ForegroundColor Green

$baseUrl = "http://127.0.0.1:8001"

# Test 1: Basic connectivity
Write-Host "`n1. Testing basic connectivity..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/" -Method GET -TimeoutSec 5
    Write-Host "✅ Backend is responding (Status: $($response.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "❌ Backend not responding: $_" -ForegroundColor Red
    Write-Host "Make sure backend is running: python -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8001" -ForegroundColor Yellow
    exit 1
}

# Test 2: OpenAPI endpoint
Write-Host "`n2. Testing OpenAPI endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/openapi.json" -Method GET -TimeoutSec 5
    Write-Host "✅ OpenAPI endpoint working (Status: $($response.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "❌ OpenAPI endpoint failed: $_" -ForegroundColor Red
}

# Test 3: Manual endpoints
Write-Host "`n3. Testing manual endpoints..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/manual/unpaired" -Method GET -TimeoutSec 5
    Write-Host "✅ Manual unpaired endpoint working (Status: $($response.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "❌ Manual unpaired endpoint failed: $_" -ForegroundColor Red
}

Write-Host "`n🎉 Backend tests complete!" -ForegroundColor Green
Write-Host "If all tests passed, your backend is ready for the frontend overlay!" -ForegroundColor Cyan
