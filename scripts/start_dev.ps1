# OWLIN Single-Port Development Launcher
# Uses uvicorn with hot reload and debug logging

$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting OWLIN Single-Port (Development Mode)" -ForegroundColor Green

# cd to repo root
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")
Set-Location $repoRoot

Write-Host "📁 Working directory: $repoRoot" -ForegroundColor Cyan

# Optional: start Ollama
Write-Host "`n🔧 Checking for LLM service..." -ForegroundColor Yellow
try { 
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden 
    Write-Host "✅ Ollama started in background" -ForegroundColor Green
} catch { 
    Write-Host "⚠️  Ollama not found, skipping LLM service" -ForegroundColor Yellow
}

# Build UI if missing
Write-Host "`n🔧 Checking UI build..." -ForegroundColor Yellow
if (-not (Test-Path ".\out\index.html")) {
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        Write-Host "📦 Building UI with npm..." -ForegroundColor Yellow
        npm run build
        Write-Host "✅ UI build complete" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Node.js/npm not found. Serving fallback JSON." -ForegroundColor Yellow
    }
} else {
    Write-Host "✅ UI build found" -ForegroundColor Green
}

# Launch with uvicorn (development mode)
Write-Host "`n🌐 Starting FastAPI server (Development Mode)..." -ForegroundColor Yellow
Write-Host "Server: http://127.0.0.1:8001" -ForegroundColor Cyan
Write-Host "Features: Hot reload, Debug logging" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow

uvicorn backend.final_single_port:app --host 127.0.0.1 --port 8001 --reload --log-level debug
