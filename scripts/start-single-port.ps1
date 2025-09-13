# OWLIN Single-Port Setup
# Run this to start the complete app on one port (8001)

Write-Host "🚀 Starting OWLIN Single-Port App..." -ForegroundColor Green

# Kill any existing processes on port 8001
Write-Host "`n🔪 Killing existing processes on port 8001..." -ForegroundColor Yellow
$ErrorActionPreference = "SilentlyContinue"
Get-NetTCPConnection -LocalPort 8001 -State Listen | ForEach-Object { 
    Stop-Process -Id $_.OwningProcess -Force 
}
$ErrorActionPreference = "Stop"

# Set environment variables
Write-Host "`n🔧 Setting up environment..." -ForegroundColor Yellow
$env:PYTHONPATH = (Get-Location).Path
Write-Host "✅ PYTHONPATH set to: $env:PYTHONPATH" -ForegroundColor Green

# Check if out directory exists, create test file if not
if (!(Test-Path "out")) {
    Write-Host "📁 Creating out directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path "out" -Force | Out-Null
}

if (!(Test-Path "out\index.html")) {
    Write-Host "📄 Creating test index.html..." -ForegroundColor Yellow
    # The test file should already be created by the setup
}

# Start the single-port server
Write-Host "`n🌐 Starting single-port server..." -ForegroundColor Yellow
Write-Host "Opening http://localhost:8001 in your browser..." -ForegroundColor Cyan
Write-Host "`nPress Ctrl+C to stop the server" -ForegroundColor Yellow

# Start the server
python -m uvicorn backend.single_port_app:app --host 0.0.0.0 --port 8001 --reload
