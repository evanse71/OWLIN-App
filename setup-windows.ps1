# OWLIN App - Windows Setup Script
# Run this in PowerShell as Administrator

Write-Host "🚀 Setting up OWLIN App on Windows..." -ForegroundColor Green

# 1. Check if Node.js is installed
Write-Host "`n📦 Checking Node.js installation..." -ForegroundColor Yellow
try {
    $nodeVersion = node -v
    $npmVersion = npm -v
    Write-Host "✅ Node.js $nodeVersion and npm $npmVersion are installed" -ForegroundColor Green
} catch {
    Write-Host "❌ Node.js not found. Installing..." -ForegroundColor Red
    Write-Host "Please run: winget install OpenJS.NodeJS.LTS --silent" -ForegroundColor Yellow
    Write-Host "Then restart PowerShell and run this script again." -ForegroundColor Yellow
    exit 1
}

# 2. Kill any processes on ports 3000 and 8001
Write-Host "`n🔪 Killing processes on ports 3000 and 8001..." -ForegroundColor Yellow
try {
    Get-NetTCPConnection -LocalPort 3000,8001 -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
        $pid = (Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).Id
        if ($pid) { 
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            Write-Host "✅ Killed process $pid on port $($_.LocalPort)" -ForegroundColor Green
        }
    }
} catch {
    Write-Host "ℹ️ No processes found on ports 3000/8001" -ForegroundColor Blue
}

# 3. Set up environment variables
Write-Host "`n🔧 Setting up environment variables..." -ForegroundColor Yellow
$env:PYTHONPATH = (Get-Location).Path
Write-Host "✅ PYTHONPATH set to: $env:PYTHONPATH" -ForegroundColor Green

# 4. Install frontend dependencies
Write-Host "`n📦 Installing frontend dependencies..." -ForegroundColor Yellow
Set-Location frontend
try {
    npm install
    Write-Host "✅ Frontend dependencies installed" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to install frontend dependencies" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}

# 5. Create .env.local file
Write-Host "`n📝 Creating .env.local file..." -ForegroundColor Yellow
"NEXT_PUBLIC_API_BASE=http://127.0.0.1:8001" | Out-File -Encoding ascii -FilePath .env.local
Write-Host "✅ .env.local created with API base URL" -ForegroundColor Green

# 6. Go back to root directory
Set-Location ..

Write-Host "`n🎉 Setup complete! Next steps:" -ForegroundColor Green
Write-Host "1. Start backend: python -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8001" -ForegroundColor Cyan
Write-Host "2. Start frontend: cd frontend && npm run dev" -ForegroundColor Cyan
Write-Host "3. Open: http://localhost:3000/invoices" -ForegroundColor Cyan
Write-Host "`n🔍 Test the overlay by clicking 'Manual Invoice' or 'Manual Delivery Note' buttons!" -ForegroundColor Yellow
