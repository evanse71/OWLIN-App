# Windows NSSM Service Setup for Owlin Single-Port
# Run as Administrator

$ErrorActionPreference = "Stop"

Write-Host "🔧 Setting up Owlin as Windows Service..." -ForegroundColor Green

# Check if running as Administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "❌ This script must be run as Administrator" -ForegroundColor Red
    exit 1
}

# Check if NSSM is installed
if (-not (Get-Command nssm -ErrorAction SilentlyContinue)) {
    Write-Host "📥 Downloading NSSM..." -ForegroundColor Yellow
    
    # Download NSSM
    $nssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
    $nssmZip = "$env:TEMP\nssm.zip"
    $nssmDir = "$env:TEMP\nssm"
    
    Invoke-WebRequest -Uri $nssmUrl -OutFile $nssmZip
    Expand-Archive -Path $nssmZip -DestinationPath $nssmDir -Force
    
    # Copy NSSM to system directory
    $nssmExe = Get-ChildItem -Path $nssmDir -Recurse -Name "nssm.exe" | Select-Object -First 1
    Copy-Item "$nssmDir\$nssmExe" "C:\Windows\System32\nssm.exe"
    
    Write-Host "✅ NSSM installed" -ForegroundColor Green
}

# Get current directory (project root)
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = (Get-Command python).Source

Write-Host "📁 Project root: $projectRoot" -ForegroundColor Cyan
Write-Host "🐍 Python executable: $pythonExe" -ForegroundColor Cyan

# Stop existing service if running
Write-Host "🛑 Stopping existing Owlin service..." -ForegroundColor Yellow
nssm stop "OwlinService" 2>$null
nssm remove "OwlinService" confirm 2>$null

# Create new service
Write-Host "🔧 Creating Owlin service..." -ForegroundColor Yellow
nssm install "OwlinService" $pythonExe
nssm set "OwlinService" Parameters "-m backend.final_single_port"
nssm set "OwlinService" AppDirectory $projectRoot
nssm set "OwlinService" DisplayName "Owlin Single-Port Service"
nssm set "OwlinService" Description "Owlin Single-Port Application Service"
nssm set "OwlinService" Start SERVICE_AUTO_START

# Set environment variables
nssm set "OwlinService" AppEnvironmentExtra "OWLIN_PORT=8001" "LLM_BASE=http://127.0.0.1:11434" "LOG_LEVEL=INFO"

# Set logging
$logDir = "$projectRoot\logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
nssm set "OwlinService" AppStdout "$logDir\owlin.out.log"
nssm set "OwlinService" AppStderr "$logDir\owlin.err.log"
nssm set "OwlinService" AppRotateFiles 1
nssm set "OwlinService" AppRotateOnline 1
nssm set "OwlinService" AppRotateBytes 10485760  # 10MB

# Start service
Write-Host "🚀 Starting Owlin service..." -ForegroundColor Yellow
nssm start "OwlinService"

# Wait for service to start
Start-Sleep -Seconds 5

# Check service status
$serviceStatus = Get-Service "OwlinService" -ErrorAction SilentlyContinue
if ($serviceStatus -and $serviceStatus.Status -eq "Running") {
    Write-Host "✅ Owlin service is running!" -ForegroundColor Green
    Write-Host "🌐 Service URL: http://127.0.0.1:8001" -ForegroundColor Cyan
    Write-Host "📊 Service status: $($serviceStatus.Status)" -ForegroundColor Cyan
} else {
    Write-Host "❌ Failed to start Owlin service" -ForegroundColor Red
    Write-Host "Check logs at: $logDir" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🔧 Service Management Commands:" -ForegroundColor Yellow
Write-Host "  Start:   nssm start OwlinService" -ForegroundColor Gray
Write-Host "  Stop:    nssm stop OwlinService" -ForegroundColor Gray
Write-Host "  Restart: nssm restart OwlinService" -ForegroundColor Gray
Write-Host "  Remove:  nssm remove OwlinService confirm" -ForegroundColor Gray
Write-Host "  Status:  Get-Service OwlinService" -ForegroundColor Gray
