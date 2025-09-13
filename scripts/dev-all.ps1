# OWLIN App - Start Both Servers (Windows)
# Run this from project root to start both backend and frontend

Write-Host "🚀 Starting OWLIN App (Backend + Frontend)..." -ForegroundColor Green

# Kill any existing processes on ports 3000 and 8001
Write-Host "`n🔪 Killing existing processes on ports 3000 and 8001..." -ForegroundColor Yellow
$ErrorActionPreference = "SilentlyContinue"
Get-NetTCPConnection -LocalPort 3000,8001 -State Listen | ForEach-Object { 
    Stop-Process -Id $_.OwningProcess -Force 
}
$ErrorActionPreference = "Stop"

# Set environment variables
Write-Host "`n🔧 Setting up environment..." -ForegroundColor Yellow
$env:PYTHONPATH = (Get-Location).Path
Write-Host "✅ PYTHONPATH set to: $env:PYTHONPATH" -ForegroundColor Green

# Start backend in new window
Write-Host "`n🐍 Starting backend server..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList '-NoExit','-Command','python -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8001 --log-level debug' -WindowStyle Normal

# Wait a moment for backend to start
Start-Sleep -Seconds 2

# Setup frontend
Write-Host "`n⚛️ Setting up frontend..." -ForegroundColor Yellow
Set-Location frontend

# Create .env.local if it doesn't exist
if (!(Test-Path .env.local)) {
    "NEXT_PUBLIC_API_BASE=http://127.0.0.1:8001" | Out-File -Encoding ascii -FilePath .env.local
    Write-Host "✅ Created .env.local" -ForegroundColor Green
}

# Install dependencies if needed
if (!(Test-Path node_modules)) {
    Write-Host "📦 Installing frontend dependencies..." -ForegroundColor Yellow
    npm install
}

# Start frontend
Write-Host "`n🌐 Starting frontend server..." -ForegroundColor Yellow
Write-Host "Opening http://localhost:3000/invoices in your browser..." -ForegroundColor Cyan
Write-Host "`nPress Ctrl+C to stop the frontend server" -ForegroundColor Yellow
Write-Host "Backend is running in a separate window" -ForegroundColor Yellow

# Start frontend (this will block)
npm run dev
