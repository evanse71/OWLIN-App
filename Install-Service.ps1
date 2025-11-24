# Install-Service.ps1
# Install Owlin Backend as a Windows Service using NSSM
# Requires: nssm.exe in PATH or same directory
# Run as Administrator

param(
    [string]$InstallPath = "C:\Owlin",
    [string]$PythonPath = "C:\Python313\python.exe",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "OWLIN BACKEND - SERVICE INSTALLER" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Must run as Administrator" -ForegroundColor Red
    exit 1
}

# Check for NSSM
$nssm = Get-Command nssm.exe -ErrorAction SilentlyContinue
if (-not $nssm) {
    Write-Host "ERROR: nssm.exe not found in PATH" -ForegroundColor Red
    Write-Host "Download from: https://nssm.cc/download" -ForegroundColor Yellow
    exit 1
}

# Check Python
if (-not (Test-Path $PythonPath)) {
    Write-Host "ERROR: Python not found at $PythonPath" -ForegroundColor Red
    Write-Host "Update -PythonPath parameter or install Python" -ForegroundColor Yellow
    exit 1
}

# Check install path
if (-not (Test-Path "$InstallPath\backend\main.py")) {
    Write-Host "ERROR: Backend code not found at $InstallPath\backend\main.py" -ForegroundColor Red
    Write-Host "Extract Owlin bundle to $InstallPath first" -ForegroundColor Yellow
    exit 1
}

Write-Host "Install Path: $InstallPath" -ForegroundColor Gray
Write-Host "Python: $PythonPath" -ForegroundColor Gray
Write-Host "Port: $Port" -ForegroundColor Gray
Write-Host ""

# Stop/remove existing service if present
Write-Host "[1/4] Checking for existing service..." -ForegroundColor Yellow
$existing = nssm status Owlin-Backend 2>$null
if ($existing) {
    Write-Host "  Stopping existing service..." -ForegroundColor Gray
    nssm stop Owlin-Backend 2>$null | Out-Null
    Start-Sleep -Seconds 2
    Write-Host "  Removing existing service..." -ForegroundColor Gray
    nssm remove Owlin-Backend confirm 2>$null | Out-Null
}
Write-Host "  ✓ Ready for installation" -ForegroundColor Green

# Install service
Write-Host "`n[2/4] Installing service..." -ForegroundColor Yellow
$appCmd = "$PythonPath -m uvicorn backend.main:app --host 127.0.0.1 --port $Port"
nssm install Owlin-Backend $PythonPath "-m" "uvicorn" "backend.main:app" "--host" "127.0.0.1" "--port" "$Port"
Write-Host "  ✓ Service installed" -ForegroundColor Green

# Configure service
Write-Host "`n[3/4] Configuring service..." -ForegroundColor Yellow
nssm set Owlin-Backend AppDirectory "$InstallPath"
nssm set Owlin-Backend AppStdout "$InstallPath\backend_stdout.log"
nssm set Owlin-Backend AppStderr "$InstallPath\backend_stderr.log"
nssm set Owlin-Backend DisplayName "Owlin Invoice OCR Backend"
nssm set Owlin-Backend Description "Owlin invoice processing backend with OCR and AI"
nssm set Owlin-Backend Start SERVICE_DELAYED_AUTO_START
Write-Host "  ✓ Service configured" -ForegroundColor Green

# Start service
Write-Host "`n[4/4] Starting service..." -ForegroundColor Yellow
nssm start Owlin-Backend
Start-Sleep -Seconds 5

# Verify
$status = nssm status Owlin-Backend
if ($status -eq "SERVICE_RUNNING") {
    Write-Host "  ✓ Service started successfully" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Service status: $status" -ForegroundColor Yellow
}

# Health check
Write-Host "`n[VERIFY] Checking health endpoint..." -ForegroundColor Yellow
Start-Sleep -Seconds 3
try {
    $health = Invoke-RestMethod "http://127.0.0.1:$Port/api/health/details" -TimeoutSec 10
    if ($health.db_wal -eq $true) {
        Write-Host "  ✓ Backend responding (db_wal: true)" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Backend responding but db_wal: $($health.db_wal)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠ Backend not yet responding: $_" -ForegroundColor Yellow
    Write-Host "  Give it a few more seconds, then check:" -ForegroundColor Gray
    Write-Host "    http://127.0.0.1:$Port/api/health/details" -ForegroundColor Gray
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "SERVICE INSTALLATION COMPLETE" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Service Commands:" -ForegroundColor Cyan
Write-Host "  Start:   nssm start Owlin-Backend" -ForegroundColor White
Write-Host "  Stop:    nssm stop Owlin-Backend" -ForegroundColor White
Write-Host "  Restart: nssm restart Owlin-Backend" -ForegroundColor White
Write-Host "  Status:  nssm status Owlin-Backend" -ForegroundColor White
Write-Host "  Remove:  nssm remove Owlin-Backend confirm" -ForegroundColor White

Write-Host "`nVerify:" -ForegroundColor Cyan
Write-Host "  http://127.0.0.1:$Port/invoices" -ForegroundColor White

Write-Host ""

