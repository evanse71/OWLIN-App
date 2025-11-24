#!/usr/bin/env pwsh
# CI-Style Test Runner for Windows
# Runs API tests (pytest) and E2E tests (Playwright) with artifact collection

$ErrorActionPreference = "Stop"

Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  OCR Pipeline - Full Test Suite Runner" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Step 1: Build frontend and copy to backend/static
Write-Host "[1/5] Building frontend..." -ForegroundColor Yellow
if (Test-Path "package.json") {
    npm run build
    if (Test-Path "out") {
        Write-Host "  ✓ Copying build to backend/static..." -ForegroundColor Green
        if (Test-Path "backend/static") {
            Remove-Item -Recurse -Force "backend/static"
        }
        Copy-Item -Path "out" -Destination "backend/static" -Recurse -Force
        Write-Host "  ✓ Frontend build complete" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ No 'out' directory found, skipping copy" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ⚠ No package.json found, skipping frontend build" -ForegroundColor Yellow
}

Write-Host ""

# Step 2: Start backend server
Write-Host "[2/5] Starting backend server..." -ForegroundColor Yellow
$backendJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    python -m uvicorn backend.main:app --port 8000 --log-level info
}

Write-Host "  ✓ Backend server starting (Job ID: $($backendJob.Id))" -ForegroundColor Green
Write-Host "  Waiting 5 seconds for server to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# Verify server is running
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 10
    Write-Host "  ✓ Server health check passed: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Server health check failed!" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
    Stop-Job -Job $backendJob
    Remove-Job -Job $backendJob
    exit 1
}

Write-Host ""

# Step 3: Run API tests (pytest)
Write-Host "[3/5] Running API tests (pytest)..." -ForegroundColor Yellow
try {
    python -m pytest tests/api/test_invoices_api.py -v -s --tb=short
    Write-Host "  ✓ API tests passed" -ForegroundColor Green
} catch {
    Write-Host "  ✗ API tests failed!" -ForegroundColor Red
    Stop-Job -Job $backendJob
    Remove-Job -Job $backendJob
    exit 1
}

Write-Host ""

# Step 4: Install Playwright browsers (if needed)
Write-Host "[4/5] Ensuring Playwright browsers installed..." -ForegroundColor Yellow
npx playwright install --with-deps chromium 2>&1 | Out-Null
Write-Host "  ✓ Playwright browsers ready" -ForegroundColor Green

Write-Host ""

# Step 5: Run E2E tests (Playwright)
Write-Host "[5/5] Running E2E tests (Playwright)..." -ForegroundColor Yellow
try {
    npx playwright test tests/e2e/invoices.spec.ts --reporter=list
    Write-Host "  ✓ E2E tests passed" -ForegroundColor Green
} catch {
    Write-Host "  ⚠ E2E tests had issues (check output above)" -ForegroundColor Yellow
}

Write-Host ""

# Cleanup: Stop backend server
Write-Host "Stopping backend server..." -ForegroundColor Gray
Stop-Job -Job $backendJob
Remove-Job -Job $backendJob
Write-Host "  ✓ Backend server stopped" -ForegroundColor Green

Write-Host ""
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Test Suite Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Artifacts saved to:" -ForegroundColor White
Write-Host "  - tests/artifacts/api/*.json" -ForegroundColor Cyan
Write-Host "  - tests/artifacts/e2e/*.png" -ForegroundColor Cyan
Write-Host ""

