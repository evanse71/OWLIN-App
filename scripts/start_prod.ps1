# OWLIN Single-Port Production Launcher
# Uses environment variables for configuration

$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting OWLIN Single-Port (Production Mode)" -ForegroundColor Green

# cd to repo root
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")
Set-Location $repoRoot

Write-Host "📁 Working directory: $repoRoot" -ForegroundColor Cyan

# Set production environment variables
$env:OWLIN_PORT = "8001"
$env:LLM_BASE = "http://127.0.0.1:11434"
$env:LOG_LEVEL = "INFO"

Write-Host "`n⚙️  Production Configuration:" -ForegroundColor Yellow
Write-Host "   Port: $env:OWLIN_PORT" -ForegroundColor Cyan
Write-Host "   LLM Base: $env:LLM_BASE" -ForegroundColor Cyan
Write-Host "   Log Level: $env:LOG_LEVEL" -ForegroundColor Cyan

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

# Launch with production settings
Write-Host "`n🌐 Starting FastAPI server (Production Mode)..." -ForegroundColor Yellow
Write-Host "Server: http://127.0.0.1:$env:OWLIN_PORT" -ForegroundColor Cyan
Write-Host "Features: Optimized, Cached, Secure" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow

python -m backend.final_single_port
