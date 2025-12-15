# Test Frontend Startup Script
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Frontend Startup Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$frontendDir = Join-Path $PSScriptRoot "frontend_clean"
Write-Host "Frontend directory: $frontendDir" -ForegroundColor Yellow

# Check if directory exists
if (-not (Test-Path $frontendDir)) {
    Write-Host "ERROR: Frontend directory not found!" -ForegroundColor Red
    exit 1
}

# Check Node.js
Write-Host "`n[1] Checking Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version
    Write-Host "  Node.js version: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Node.js not found!" -ForegroundColor Red
    exit 1
}

# Check npm
Write-Host "`n[2] Checking npm..." -ForegroundColor Yellow
try {
    $npmVersion = npm --version
    Write-Host "  npm version: $npmVersion" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: npm not found!" -ForegroundColor Red
    exit 1
}

# Check package.json
Write-Host "`n[3] Checking package.json..." -ForegroundColor Yellow
$packageJson = Join-Path $frontendDir "package.json"
if (Test-Path $packageJson) {
    Write-Host "  package.json found" -ForegroundColor Green
} else {
    Write-Host "  ERROR: package.json not found!" -ForegroundColor Red
    exit 1
}

# Check node_modules
Write-Host "`n[4] Checking node_modules..." -ForegroundColor Yellow
$nodeModules = Join-Path $frontendDir "node_modules"
if (Test-Path $nodeModules) {
    Write-Host "  node_modules exists" -ForegroundColor Green
    
    # Check if vite is installed
    $vitePath = Join-Path $nodeModules "vite"
    if (Test-Path $vitePath) {
        Write-Host "  Vite is installed" -ForegroundColor Green
    } else {
        Write-Host "  WARNING: Vite not found in node_modules" -ForegroundColor Yellow
        Write-Host "  Installing dependencies..." -ForegroundColor Yellow
        Push-Location $frontendDir
        npm install
        Pop-Location
    }
} else {
    Write-Host "  WARNING: node_modules not found" -ForegroundColor Yellow
    Write-Host "  Installing dependencies..." -ForegroundColor Yellow
    Push-Location $frontendDir
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ERROR: npm install failed!" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    Pop-Location
}

# Check port 5176
Write-Host "`n[5] Checking port 5176..." -ForegroundColor Yellow
$portInUse = Get-NetTCPConnection -LocalPort 5176 -State Listen -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "  WARNING: Port 5176 is already in use!" -ForegroundColor Yellow
    Write-Host "  Killing processes on port 5176..." -ForegroundColor Yellow
    $portInUse | ForEach-Object {
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
} else {
    Write-Host "  Port 5176 is available" -ForegroundColor Green
}

# Start the server
Write-Host "`n[6] Starting Vite dev server..." -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Starting Frontend on Port 5176" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Once you see 'Local: http://localhost:5176/'," -ForegroundColor Green
Write-Host "open: http://localhost:5176/invoices?dev=1" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

Push-Location $frontendDir
npm run dev

