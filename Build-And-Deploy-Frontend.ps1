# Build-And-Deploy-Frontend.ps1
# Builds frontend and copies to backend/static for single-port (8000) deployment

$ErrorActionPreference = "Stop"

Write-Host "===================================" -ForegroundColor Cyan
Write-Host "Frontend Build & Deploy to Port 8000" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

# Navigate to frontend directory
$frontendDir = "source_extracted\tmp_lovable"
$backendStaticDir = "backend\static"
$buildOutput = "$frontendDir\out"

if (-not (Test-Path $frontendDir)) {
    Write-Host "ERROR: Frontend directory not found: $frontendDir" -ForegroundColor Red
    exit 1
}

Push-Location $frontendDir

try {
    # Step 1: Build frontend
    Write-Host "[1/3] Building frontend..." -ForegroundColor Yellow
    npm run build
    
    if ($LASTEXITCODE -ne 0) {
        throw "Build failed with exit code $LASTEXITCODE"
    }
    
    Write-Host "✓ Build complete" -ForegroundColor Green
    Write-Host ""
    
    # Step 2: Verify build output
    if (-not (Test-Path "out\index.html")) {
        throw "Build output missing: out\index.html not found"
    }
    
    Write-Host "[2/3] Verifying build output..." -ForegroundColor Yellow
    $buildFiles = Get-ChildItem -Path "out" -Recurse -File
    Write-Host "✓ Found $($buildFiles.Count) files in build output" -ForegroundColor Green
    Write-Host ""
    
    # Step 3: Copy to backend/static
    Pop-Location
    
    Write-Host "[3/3] Deploying to backend/static..." -ForegroundColor Yellow
    
    # Create backend/static if it doesn't exist
    if (-not (Test-Path $backendStaticDir)) {
        New-Item -ItemType Directory -Path $backendStaticDir | Out-Null
    }
    
    # Clean existing files
    if (Test-Path "$backendStaticDir\*") {
        Remove-Item -Path "$backendStaticDir\*" -Recurse -Force
        Write-Host "  Cleaned existing files" -ForegroundColor Gray
    }
    
    # Copy build output
    Copy-Item -Path "$buildOutput\*" -Destination $backendStaticDir -Recurse -Force
    
    $deployedFiles = Get-ChildItem -Path $backendStaticDir -Recurse -File
    Write-Host "✓ Deployed $($deployedFiles.Count) files to $backendStaticDir" -ForegroundColor Green
    Write-Host ""
    
    # Success summary
    Write-Host "===================================" -ForegroundColor Green
    Write-Host "✓ DEPLOYMENT COMPLETE" -ForegroundColor Green
    Write-Host "===================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Start backend: python -m uvicorn backend.main:app --port 8000" -ForegroundColor White
    Write-Host "2. Open: http://127.0.0.1:8000/invoices" -ForegroundColor White
    Write-Host ""
    
} catch {
    Write-Host ""
    Write-Host "ERROR: $_" -ForegroundColor Red
    Pop-Location
    exit 1
}

