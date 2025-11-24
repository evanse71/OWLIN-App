# Venue-Rollout.ps1
# One-command venue deployment and verification
# Run on fresh venue machine after extracting bundle

param(
    [string]$InstallPath = "C:\Owlin",
    [string]$BundlePath = "",
    [switch]$SkipExtract,
    [switch]$InstallService,
    [string]$PythonPath = "C:\Python313\python.exe"
)

$ErrorActionPreference = "Stop"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "OWLIN VENUE ROLLOUT" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Step 1: Extract bundle (if needed)
if (-not $SkipExtract) {
    if (-not $BundlePath) {
        Write-Host "ERROR: -BundlePath required (or use -SkipExtract)" -ForegroundColor Red
        exit 1
    }
    
    if (-not (Test-Path $BundlePath)) {
        Write-Host "ERROR: Bundle not found: $BundlePath" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "[1/6] Extracting bundle..." -ForegroundColor Yellow
    Write-Host "  Source: $BundlePath" -ForegroundColor Gray
    Write-Host "  Target: $InstallPath" -ForegroundColor Gray
    
    if (Test-Path $InstallPath) {
        Write-Host "  ⚠ Install path exists, backing up..." -ForegroundColor Yellow
        $backup = "$InstallPath.backup_$((Get-Date).ToString('yyyyMMdd_HHmmss'))"
        Rename-Item $InstallPath $backup
    }
    
    New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
    Expand-Archive -Path $BundlePath -DestinationPath $InstallPath -Force
    Write-Host "  ✓ Bundle extracted" -ForegroundColor Green
} else {
    Write-Host "[1/6] Skipping extraction (using existing files)" -ForegroundColor Yellow
}

# Step 2: Verify installation
Write-Host "`n[2/6] Verifying installation..." -ForegroundColor Yellow
$required = @(
    "$InstallPath\backend\main.py",
    "$InstallPath\backend\app\db.py",
    "$InstallPath\Prove-Hardening.ps1",
    "$InstallPath\Monitor-Production.ps1"
)

$missing = @()
foreach ($file in $required) {
    if (-not (Test-Path $file)) {
        $missing += $file
        Write-Host "  ✗ Missing: $file" -ForegroundColor Red
    }
}

if ($missing.Count -gt 0) {
    Write-Host "ERROR: Installation incomplete" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ All required files present" -ForegroundColor Green

# Step 3: Initialize database
Write-Host "`n[3/6] Initializing database..." -ForegroundColor Yellow
if (-not (Test-Path "$InstallPath\data")) {
    New-Item -ItemType Directory -Path "$InstallPath\data" -Force | Out-Null
    Write-Host "  ✓ Data directory created" -ForegroundColor Green
} else {
    Write-Host "  ✓ Data directory exists" -ForegroundColor Green
}

# Step 4: Start backend (or install service)
Write-Host "`n[4/6] Starting backend..." -ForegroundColor Yellow
if ($InstallService) {
    Write-Host "  Installing as Windows service..." -ForegroundColor Gray
    & "$InstallPath\Install-Service.ps1" -InstallPath $InstallPath -PythonPath $PythonPath
} else {
    Write-Host "  Starting manually (press Ctrl+C to stop later)..." -ForegroundColor Gray
    Push-Location $InstallPath
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "python -m uvicorn backend.main:app --port 8000" -PassThru | Out-Null
    Pop-Location
    Start-Sleep -Seconds 8
}
Write-Host "  ✓ Backend started" -ForegroundColor Green

# Step 5: Run hardening proof
Write-Host "`n[5/6] Running verification..." -ForegroundColor Yellow
Push-Location $InstallPath
$proofResult = & ".\Prove-Hardening.ps1"
$proofExitCode = $LASTEXITCODE
Pop-Location

if ($proofExitCode -eq 0) {
    Write-Host "  ✓ All gates passed" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Some gates failed (exit code: $proofExitCode)" -ForegroundColor Yellow
    Write-Host "  Review output above for details" -ForegroundColor Gray
}

# Step 6: Browser check
Write-Host "`n[6/6] Manual verification steps..." -ForegroundColor Yellow
Write-Host "  1. Open browser: http://127.0.0.1:8000/invoices" -ForegroundColor White
Write-Host "  2. Open DevTools console, run:" -ForegroundColor White
Write-Host "     document.querySelectorAll('[data-testid=`"invoices-footer-bar`"]').length" -ForegroundColor Gray
Write-Host "     (expect: 1)" -ForegroundColor Gray
Write-Host "  3. Upload a test PDF → verify card + line items" -ForegroundColor White
Write-Host "  4. Start monitoring:" -ForegroundColor White
Write-Host "     cd $InstallPath" -ForegroundColor Gray
Write-Host "     .\Monitor-Production.ps1" -ForegroundColor Gray

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "VENUE ROLLOUT COMPLETE" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Health Check:" -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod http://127.0.0.1:8000/api/health/details -TimeoutSec 10
    Write-Host "  db_wal: $($health.db_wal)" -ForegroundColor $(if($health.db_wal){"Green"}else{"Red"})
    Write-Host "  ocr_max_concurrency: $($health.ocr_max_concurrency)" -ForegroundColor Gray
    Write-Host "  app_version: $($health.app_version)" -ForegroundColor Gray
} catch {
    Write-Host "  ⚠ Health check failed: $_" -ForegroundColor Yellow
}

Write-Host "`nNext Steps:" -ForegroundColor Cyan
Write-Host "  Monitor: .\Monitor-Production.ps1" -ForegroundColor White
Write-Host "  Access:  http://127.0.0.1:8000/invoices" -ForegroundColor White
Write-Host ""

if ($proofExitCode -eq 0) {
    exit 0
} else {
    exit 1
}

