# Test-Footer-Both-Ports.ps1
# Validation script for footer visibility on both dev (8080) and production (8000) ports

$ErrorActionPreference = "Stop"

Write-Host "===================================" -ForegroundColor Cyan
Write-Host "Footer Validation Test" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Check component exists
Write-Host "[1/5] Checking component files..." -ForegroundColor Yellow
$requiredFiles = @(
    "source_extracted\tmp_lovable\src\components\invoices\InvoicesFooterBar.tsx",
    "source_extracted\tmp_lovable\src\state\invoicesStore.ts"
)

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "  ✓ $file" -ForegroundColor Green
    } else {
        Write-Host "  ✗ MISSING: $file" -ForegroundColor Red
        exit 1
    }
}
Write-Host ""

# Test 2: Check backend routes
Write-Host "[2/5] Checking backend routes..." -ForegroundColor Yellow
$backendFile = "backend\routes\invoices_submit.py"
if (Test-Path $backendFile) {
    Write-Host "  ✓ $backendFile" -ForegroundColor Green
    
    $content = Get-Content $backendFile -Raw
    if ($content -match "SESSION_CLEAR" -and $content -match "SESSION_SUBMIT") {
        Write-Host "  ✓ Audit logging present" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Audit logging missing" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  ✗ MISSING: $backendFile" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Test 3: Verify vite config
Write-Host "[3/5] Checking vite config..." -ForegroundColor Yellow
$viteConfig = Get-Content "source_extracted\tmp_lovable\vite.config.ts" -Raw
if ($viteConfig -match 'outDir:\s*"out"') {
    Write-Host "  ✓ Build output set to 'out'" -ForegroundColor Green
} else {
    Write-Host "  ✗ Build output not set to 'out'" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Test 4: Check Invoices.tsx integration
Write-Host "[4/5] Checking Invoices page integration..." -ForegroundColor Yellow
$invoicesPage = Get-Content "source_extracted\tmp_lovable\src\pages\Invoices.tsx" -Raw
$checks = @(
    @{ Pattern = "import.*InvoicesFooterBar"; Name = "Footer import" },
    @{ Pattern = "import.*useInvoicesStore"; Name = "Store import" },
    @{ Pattern = "InvoicesFooterBar"; Name = "Footer component usage" },
    @{ Pattern = "getPendingCount"; Name = "Pending count" },
    @{ Pattern = "getReadyCount"; Name = "Ready count" },
    @{ Pattern = "handleClearSession"; Name = "Clear handler" },
    @{ Pattern = "handleSubmit"; Name = "Submit handler" }
)

foreach ($check in $checks) {
    if ($invoicesPage -match $check.Pattern) {
        Write-Host "  ✓ $($check.Name)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ MISSING: $($check.Name)" -ForegroundColor Red
        exit 1
    }
}

# Check test ID in footer component
$footerComponent = Get-Content "source_extracted\tmp_lovable\src\components\invoices\InvoicesFooterBar.tsx" -Raw
if ($footerComponent -match 'data-testid="invoices-footer-bar"') {
    Write-Host "  ✓ Test ID attribute in component" -ForegroundColor Green
} else {
    Write-Host "  ✗ MISSING: Test ID attribute in component" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Test 5: Manual validation instructions
Write-Host "[5/5] Manual validation steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "DEV MODE (Port 8080):" -ForegroundColor Cyan
Write-Host "  1. cd source_extracted\tmp_lovable" -ForegroundColor White
Write-Host "  2. npm run dev" -ForegroundColor White
Write-Host "  3. Open: http://127.0.0.1:8080/invoices" -ForegroundColor White
Write-Host "  4. Check footer is visible at bottom" -ForegroundColor White
Write-Host ""
Write-Host "PRODUCTION MODE (Port 8000):" -ForegroundColor Cyan
Write-Host "  1. .\Build-And-Deploy-Frontend.ps1" -ForegroundColor White
Write-Host "  2. python -m uvicorn backend.main:app --port 8000" -ForegroundColor White
Write-Host "  3. Open: http://127.0.0.1:8000/invoices" -ForegroundColor White
Write-Host "  4. Check footer is visible at bottom" -ForegroundColor White
Write-Host ""
Write-Host "CONSOLE VALIDATION:" -ForegroundColor Cyan
Write-Host "  Open browser DevTools console and run:" -ForegroundColor White
Write-Host "  document.querySelectorAll('[data-testid=`"invoices-footer-bar`"]').length" -ForegroundColor Gray
Write-Host "  Should return: 1" -ForegroundColor White
Write-Host ""
Write-Host "  __OWLIN_DEBUG?.invoices?.pendingInSession" -ForegroundColor Gray
Write-Host "  __OWLIN_DEBUG?.invoices?.readyCount" -ForegroundColor Gray
Write-Host "  Should return: current counts" -ForegroundColor White
Write-Host ""

Write-Host "===================================" -ForegroundColor Green
Write-Host "✓ AUTOMATED CHECKS PASSED" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green
Write-Host ""
Write-Host "Proceed with manual validation on both ports." -ForegroundColor Yellow

