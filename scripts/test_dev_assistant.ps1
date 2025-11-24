# Test Dev Debug Assistant Installation
# Verifies all required tools and dependencies are available

$ErrorActionPreference = "Continue"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Owlin Dev Debug Assistant - Installation Test" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$allGood = $true

# Test Python installation
Write-Host "Testing Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✓ Python installed: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Python not found" -ForegroundColor Red
    $allGood = $false
}

# Test Python tools
Write-Host "`nTesting Python linting tools..." -ForegroundColor Yellow

# MyPy
try {
    $mypyVersion = mypy --version 2>&1
    Write-Host "  ✓ MyPy installed: $mypyVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ MyPy not found. Install with: pip install mypy" -ForegroundColor Red
    $allGood = $false
}

# Ruff
try {
    $ruffVersion = ruff --version 2>&1
    Write-Host "  ✓ Ruff installed: $ruffVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Ruff not found. Install with: pip install ruff" -ForegroundColor Red
    $allGood = $false
}

# Pytest
try {
    $pytestVersion = pytest --version 2>&1
    Write-Host "  ✓ Pytest installed: $pytestVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Pytest not found. Install with: pip install pytest" -ForegroundColor Red
    $allGood = $false
}

# Test Node.js
Write-Host "`nTesting Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    Write-Host "  ✓ Node.js installed: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Node.js not found" -ForegroundColor Red
    $allGood = $false
}

# Test TypeScript (in frontend_clean)
Write-Host "`nTesting TypeScript tools..." -ForegroundColor Yellow
$frontendDir = Join-Path $PSScriptRoot ".." "frontend_clean"
if (Test-Path $frontendDir) {
    Push-Location $frontendDir
    
    try {
        $tscVersion = npx tsc --version 2>&1
        Write-Host "  ✓ TypeScript installed: $tscVersion" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ TypeScript not found. Run: npm install" -ForegroundColor Red
        $allGood = $false
    }
    
    try {
        $eslintVersion = npx eslint --version 2>&1
        Write-Host "  ✓ ESLint installed: $eslintVersion" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ ESLint not found. Run: npm install" -ForegroundColor Red
        $allGood = $false
    }
    
    Pop-Location
} else {
    Write-Host "  ✗ frontend_clean directory not found" -ForegroundColor Red
    $allGood = $false
}

# Test Ollama (optional)
Write-Host "`nTesting Ollama (optional for AI explanations)..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "  ✓ Ollama is running" -ForegroundColor Green
    
    # Check for CodeLlama model
    $hasCodeLlama = $response.models | Where-Object { $_.name -like "codellama*" }
    if ($hasCodeLlama) {
        Write-Host "  ✓ CodeLlama model available" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ CodeLlama model not found. Run: ollama pull codellama:7b" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠ Ollama not running (will use template fallback)" -ForegroundColor Yellow
}

# Test backend API
Write-Host "`nTesting Owlin backend..." -ForegroundColor Yellow
try {
    $healthResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/health" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "  ✓ Backend is running" -ForegroundColor Green
    
    # Test dev tools endpoint
    try {
        $devStatus = Invoke-RestMethod -Uri "http://localhost:8000/api/dev/status" -TimeoutSec 2 -ErrorAction Stop
        Write-Host "  ✓ Dev Tools API is accessible" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ Dev Tools API not accessible" -ForegroundColor Red
        $allGood = $false
    }
} catch {
    Write-Host "  ⚠ Backend not running. Start with: uvicorn backend.main:app --reload" -ForegroundColor Yellow
}

# Test frontend dev server
Write-Host "`nTesting frontend dev server..." -ForegroundColor Yellow
try {
    $frontendResponse = Invoke-WebRequest -Uri "http://localhost:5173" -TimeoutSec 2 -ErrorAction Stop -UseBasicParsing
    Write-Host "  ✓ Frontend dev server is running" -ForegroundColor Green
} catch {
    Write-Host "  ⚠ Frontend dev server not running. Start with: cd frontend_clean && npm run dev" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
if ($allGood) {
    Write-Host "  ✓ All required tools are installed!" -ForegroundColor Green
    Write-Host "  Ready to use Dev Debug Assistant" -ForegroundColor Green
} else {
    Write-Host "  ✗ Some required tools are missing" -ForegroundColor Red
    Write-Host "  Install missing tools before using Dev Debug Assistant" -ForegroundColor Red
}
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Quick Start Instructions
Write-Host "Quick Start:" -ForegroundColor Yellow
Write-Host "  1. Start backend: uvicorn backend.main:app --reload --port 8000"
Write-Host "  2. Start frontend: cd frontend_clean && npm run dev"
Write-Host "  3. Open browser: http://localhost:5173/dev/debug"
Write-Host ""
Write-Host "For full documentation, see: DEV_DEBUG_ASSISTANT_README.md" -ForegroundColor Cyan

if ($allGood) {
    exit 0
} else {
    exit 1
}

