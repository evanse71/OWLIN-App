# OWLIN - Windows Service Setup (Turnkey Installer)
# Installs Owlin as a Windows Service using NSSM
# Run as Administrator

param(
    [string]$ServiceName = "Owlin",
    [string]$InstallPath = "C:\Owlin",
    [string]$Port = "8001",
    [string]$LLMBase = "http://127.0.0.1:11434",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Write-Info($m){ Write-Host "• $m" -ForegroundColor Gray }
function Write-Ok($m){ Write-Host "✅ $m" -ForegroundColor Green }
function Write-Fail($m){ Write-Host "❌ $m" -ForegroundColor Red }
function Write-Warn($m){ Write-Host "⚠️  $m" -ForegroundColor Yellow }

Write-Host "🚀 OWLIN - Windows Service Setup" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Fail "This script must be run as Administrator"
    Write-Info "Right-click PowerShell and select 'Run as Administrator'"
    exit 1
}

# Check if NSSM is available
$nssmPath = "C:\Owlin\tools\nssm.exe"
if (-not (Test-Path $nssmPath)) {
    Write-Warn "NSSM not found at $nssmPath"
    Write-Info "Download NSSM from https://nssm.cc/download"
    Write-Info "Extract nssm.exe to C:\Owlin\tools\nssm.exe"
    Write-Info "Or place nssm.exe in your PATH"
    exit 1
}

# Check if service already exists
if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
    if ($Force) {
        Write-Warn "Service $ServiceName already exists. Stopping and removing..."
        Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
        & $nssmPath remove $ServiceName confirm
        Start-Sleep -Seconds 2
    } else {
        Write-Fail "Service $ServiceName already exists. Use -Force to replace it."
        exit 1
    }
}

# Verify install path exists
if (-not (Test-Path $InstallPath)) {
    Write-Fail "Install path $InstallPath does not exist"
    Write-Info "Please ensure Owlin is installed at $InstallPath"
    exit 1
}

# Check for required files
$requiredFiles = @(
    "$InstallPath\backend\final_single_port.py",
    "$InstallPath\backend\__init__.py",
    "$InstallPath\requirements.txt"
)

foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        Write-Fail "Required file missing: $file"
        exit 1
    }
}

Write-Ok "All required files found"

# Create logs directory
$logsDir = "$InstallPath\logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
    Write-Info "Created logs directory: $logsDir"
}

# Determine Python executable
$pythonExe = "$InstallPath\.venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
    Write-Warn "Virtual environment not found, using system Python: $pythonExe"
} else {
    Write-Info "Using virtual environment Python: $pythonExe"
}

# Create service
Write-Info "Creating Windows Service: $ServiceName"
& $nssmPath install $ServiceName $pythonExe "-m backend.final_single_port"
& $nssmPath set $ServiceName AppDirectory $InstallPath
& $nssmPath set $ServiceName AppStdout "$logsDir\owlin.out.log"
& $nssmPath set $ServiceName AppStderr "$logsDir\owlin.err.log"
& $nssmPath set $ServiceName Start SERVICE_AUTO_START

# Set environment variables
Write-Info "Setting environment variables..."
$envs = @(
    "OWLIN_PORT=$Port",
    "LLM_BASE=$LLMBase",
    "OWLIN_DB_URL=sqlite:///./owlin.db",
    "PYTHONUNBUFFERED=1"
)
& $nssmPath set $ServiceName AppEnvironmentExtra ($envs -join "`r`n")

# Create .env file for reference
$envContent = @"
OWLIN_PORT=$Port
LLM_BASE=$LLMBase
OWLIN_DB_URL=sqlite:///./owlin.db
PYTHONUNBUFFERED=1
"@
$envContent | Out-File -FilePath "$InstallPath\.env" -Encoding ASCII
Write-Info "Created .env file: $InstallPath\.env"

# Configure firewall rule
Write-Info "Configuring Windows Firewall..."
try {
    New-NetFirewallRule -DisplayName "Owlin $Port" -Direction Inbound -Protocol TCP -LocalPort $Port -Action Allow -ErrorAction SilentlyContinue | Out-Null
    Write-Ok "Firewall rule created for port $Port"
} catch {
    Write-Warn "Could not create firewall rule: $($_.Exception.Message)"
}

# Start service
Write-Info "Starting service..."
Start-Service -Name $ServiceName
Start-Sleep -Seconds 3

# Verify service is running
$service = Get-Service -Name $ServiceName
if ($service.Status -eq "Running") {
    Write-Ok "Service started successfully"
} else {
    Write-Fail "Service failed to start. Status: $($service.Status)"
    Write-Info "Check logs: Get-Content $logsDir\owlin.err.log -Tail 20"
    exit 1
}

# Wait for health check
Write-Info "Waiting for service to become healthy..."
$baseUrl = "http://127.0.0.1:$Port"
$healthUrl = "$baseUrl/api/health"
$ready = $false

for ($i=0; $i -lt 30; $i++) {
    try {
        $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200 -and $response.Content -match '"ok"\s*:\s*true') {
            $ready = $true
            break
        }
    } catch {}
    Start-Sleep -Milliseconds 500
}

if ($ready) {
    Write-Ok "Service is healthy and responding"
} else {
    Write-Warn "Service may not be fully ready yet"
    Write-Info "Check logs: Get-Content $logsDir\owlin.out.log -Tail 20"
}

# Final verification
Write-Host ""
Write-Host "🎉 OWLIN SERVICE INSTALLED SUCCESSFULLY" -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Green
Write-Host ""
Write-Ok "Service Name: $ServiceName"
Write-Ok "Install Path: $InstallPath"
Write-Ok "Port: $Port"
Write-Ok "URL: $baseUrl"
Write-Host ""
Write-Host "📋 Management Commands:" -ForegroundColor Cyan
Write-Host "  Start:   Start-Service $ServiceName" -ForegroundColor White
Write-Host "  Stop:    Stop-Service $ServiceName" -ForegroundColor White
Write-Host "  Status:  Get-Service $ServiceName" -ForegroundColor White
Write-Host "  Logs:    Get-Content $logsDir\owlin.out.log -Tail 20" -ForegroundColor White
Write-Host ""
Write-Host "🌐 Test URLs:" -ForegroundColor Cyan
Write-Host "  Health:  $healthUrl" -ForegroundColor White
Write-Host "  Status:  $baseUrl/api/status" -ForegroundColor White
Write-Host "  App:     $baseUrl" -ForegroundColor White
Write-Host ""

# Test URLs
Write-Host "🔍 Quick Health Check:" -ForegroundColor Yellow
try {
    $health = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 5
    Write-Host "✅ Health: $($health.Content)" -ForegroundColor Green
} catch {
    Write-Host "❌ Health check failed: $($_.Exception.Message)" -ForegroundColor Red
}

try {
    $status = Invoke-WebRequest -Uri "$baseUrl/api/status" -UseBasicParsing -TimeoutSec 5
    Write-Host "✅ Status: $($status.Content)" -ForegroundColor Green
} catch {
    Write-Host "❌ Status check failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "🚀 Owlin is now running as a Windows Service!" -ForegroundColor Green
Write-Host "Open $baseUrl in your browser to access the application." -ForegroundColor Cyan
