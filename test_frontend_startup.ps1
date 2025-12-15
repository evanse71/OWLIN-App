# Test Frontend Startup - Capture All Output
$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Frontend Startup Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$frontendDir = "C:\Users\tedev\FixPack_2025-11-02_133105\frontend_clean"

if (-not (Test-Path $frontendDir)) {
    Write-Host "ERROR: Frontend directory not found: $frontendDir" -ForegroundColor Red
    exit 1
}

Write-Host "Frontend directory: $frontendDir" -ForegroundColor Yellow
Write-Host ""

# Change to frontend directory
Push-Location $frontendDir

Write-Host "[1] Checking Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    Write-Host "  Node.js: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Node.js not found!" -ForegroundColor Red
    Pop-Location
    exit 1
}

Write-Host ""
Write-Host "[2] Checking npm..." -ForegroundColor Yellow
try {
    $npmVersion = npm --version 2>&1
    Write-Host "  npm: $npmVersion" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: npm not found!" -ForegroundColor Red
    Pop-Location
    exit 1
}

Write-Host ""
Write-Host "[3] Starting Vite dev server on port 5176..." -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Try to start the server and capture output
$process = Start-Process -FilePath "npm" -ArgumentList "run","dev","--","--port","5176" -NoNewWindow -PassThru -RedirectStandardOutput "vite_output.txt" -RedirectStandardError "vite_errors.txt"

Write-Host "Started npm process (PID: $($process.Id))" -ForegroundColor Yellow
Write-Host "Waiting 10 seconds for server to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host ""
Write-Host "[4] Checking if port 5176 is listening..." -ForegroundColor Yellow
$portCheck = netstat -ano | Select-String "5176.*LISTENING"
if ($portCheck) {
    Write-Host "  SUCCESS: Port 5176 is LISTENING!" -ForegroundColor Green
    $portCheck | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
} else {
    Write-Host "  FAILED: Port 5176 is NOT listening" -ForegroundColor Red
}

Write-Host ""
Write-Host "[5] Checking for Node processes..." -ForegroundColor Yellow
$nodeProcs = Get-Process -Name node -ErrorAction SilentlyContinue
if ($nodeProcs) {
    Write-Host "  Node.js processes found:" -ForegroundColor Green
    $nodeProcs | ForEach-Object { Write-Host "    PID: $($_.Id) - Started: $($_.StartTime)" -ForegroundColor Gray }
} else {
    Write-Host "  No Node.js processes running" -ForegroundColor Red
}

Write-Host ""
Write-Host "[6] Checking output files..." -ForegroundColor Yellow
if (Test-Path "vite_output.txt") {
    Write-Host "  vite_output.txt exists" -ForegroundColor Green
    Write-Host "  Last 20 lines:" -ForegroundColor Yellow
    Get-Content "vite_output.txt" -Tail 20 | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
} else {
    Write-Host "  vite_output.txt not found" -ForegroundColor Yellow
}

if (Test-Path "vite_errors.txt") {
    $errorContent = Get-Content "vite_errors.txt" -Raw
    if ($errorContent -and $errorContent.Trim().Length -gt 0) {
        Write-Host ""
        Write-Host "  vite_errors.txt contains errors:" -ForegroundColor Red
        Get-Content "vite_errors.txt" | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Test Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Pop-Location

