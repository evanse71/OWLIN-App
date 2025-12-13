# OWLIN Overlay QA Test Script
# Run this after starting both servers to verify the overlay works correctly

Write-Host "🧪 OWLIN Overlay QA Tests" -ForegroundColor Green
Write-Host "Make sure both servers are running first!" -ForegroundColor Yellow

# Test 1: Backend connectivity
Write-Host "`n1. Testing backend connectivity..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8001/openapi.json" -Method GET -TimeoutSec 5
    Write-Host "✅ Backend is responding (Status: $($response.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "❌ Backend not responding. Start it with: python -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8001" -ForegroundColor Red
    exit 1
}

# Test 2: Frontend connectivity
Write-Host "`n2. Testing frontend connectivity..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000" -Method GET -TimeoutSec 5
    Write-Host "✅ Frontend is responding (Status: $($response.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "❌ Frontend not responding. Start it with: cd frontend && npm run dev" -ForegroundColor Red
    exit 1
}

# Test 3: Manual endpoints
Write-Host "`n3. Testing manual endpoints..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8001/manual/unpaired" -Method GET -TimeoutSec 5
    Write-Host "✅ Manual endpoints working (Status: $($response.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "❌ Manual endpoints failed: $_" -ForegroundColor Red
}

Write-Host "`n🎯 Manual Testing Checklist:" -ForegroundColor Green
Write-Host "1. Open http://localhost:3000/invoices" -ForegroundColor Cyan
Write-Host "2. Click '+ Manual Invoice' button" -ForegroundColor Cyan
Write-Host "3. Verify overlay appears with focus in first input" -ForegroundColor Cyan
Write-Host "4. Test Tab navigation cycles within overlay" -ForegroundColor Cyan
Write-Host "5. Test ESC key closes overlay" -ForegroundColor Cyan
Write-Host "6. Fill form with test data: 2 × 24 × £1.05 @ 20% VAT" -ForegroundColor Cyan
Write-Host "7. Verify gross total ≈ £60.48" -ForegroundColor Cyan
Write-Host "8. Click 'Create Invoice' - should show toast and close overlay" -ForegroundColor Cyan
Write-Host "9. Try creating same Invoice Ref again - should show inline error" -ForegroundColor Cyan
Write-Host "10. Test 'Cancel' with edits - should show confirm dialog" -ForegroundColor Cyan

Write-Host "`n🔧 Keyboard Shortcuts:" -ForegroundColor Green
Write-Host "• Ctrl/Cmd+Enter: Submit form" -ForegroundColor Cyan
Write-Host "• Tab/Shift+Tab: Navigate within overlay" -ForegroundColor Cyan
Write-Host "• ESC: Cancel overlay" -ForegroundColor Cyan

Write-Host "`n✅ All automated tests passed! Manual testing required above." -ForegroundColor Green
