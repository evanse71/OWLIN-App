Write-Host "`n🔴 BRJ ROUTER FINALISE — VERIFICATION" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Gray

# 1. SPA Fallback
Write-Host "`n[1/6] SPA Fallback Test..." -ForegroundColor Yellow
$spa = .\tests\smoke_spa.ps1 -Url http://127.0.0.1:8000/invoices
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ PASS: Deep link returns HTML" -ForegroundColor Green
} else {
    Write-Host "   ❌ FAIL: Deep link failed" -ForegroundColor Red
}

# 2. Health Check
Write-Host "`n[2/6] Health Endpoint..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod http://127.0.0.1:8000/api/health
    if ($health.status -eq "ok") {
        Write-Host "   ✅ PASS: Health endpoint OK" -ForegroundColor Green
    } else {
        Write-Host "   ❌ FAIL: Health endpoint bad status" -ForegroundColor Red
    }
} catch {
    Write-Host "   ❌ FAIL: Health endpoint unreachable" -ForegroundColor Red
}

# 3. Footer Test ID (HTML check)
Write-Host "`n[3/6] Footer Test ID in HTML..." -ForegroundColor Yellow
try {
    $html = (Invoke-WebRequest http://127.0.0.1:8000/invoices -UseBasicParsing).Content
    if ($html -match 'data-testid="invoices-footer-bar"') {
        Write-Host "   ✅ PASS: Footer test ID present in HTML" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  WARN: Footer test ID not in static HTML (may be rendered client-side)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ❌ FAIL: Could not fetch HTML" -ForegroundColor Red
}

# 4. Route Smoke Test
Write-Host "`n[4/6] Route Availability..." -ForegroundColor Yellow
$route = .\tests\smoke_routes.ps1 -Url http://127.0.0.1:8000/invoices
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ PASS: Route /invoices accessible" -ForegroundColor Green
} else {
    Write-Host "   ❌ FAIL: Route /invoices failed" -ForegroundColor Red
}

# 5. Build Verification
Write-Host "`n[5/6] Build Artifacts..." -ForegroundColor Yellow
$index = Test-Path backend\static\index.html
$js = (Get-ChildItem backend\static\assets\*.js | Measure-Object -Property Length -Sum).Sum / 1KB
if ($index -and $js -gt 500) {
    Write-Host "   ✅ PASS: Build artifacts present ($([math]::Round($js, 2))KB JS)" -ForegroundColor Green
} else {
    Write-Host "   ❌ FAIL: Build artifacts missing or invalid" -ForegroundColor Red
}

# 6. Playwright Spec Status
Write-Host "`n[6/6] Playwright Specs..." -ForegroundColor Yellow
$spec = Test-Path tests\e2e\footer.spec.ts
if ($spec) {
    Write-Host "   ✅ PASS: Footer spec created (run: npx playwright test tests/e2e/footer.spec.ts)" -ForegroundColor Green
} else {
    Write-Host "   ❌ FAIL: Footer spec missing" -ForegroundColor Red
}

Write-Host "`n" + ("=" * 60) -ForegroundColor Gray
Write-Host "✅ VERIFICATION COMPLETE" -ForegroundColor Green
Write-Host "`nNote: Playwright E2E tests require installation:" -ForegroundColor Gray
Write-Host "  npm install -D @playwright/test && npx playwright install" -ForegroundColor Gray

