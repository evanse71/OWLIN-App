$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting OWLIN Single-Port Demo" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green

if (-not $env:VITE_API_BASE_URL) { 
    $env:VITE_API_BASE_URL = "http://127.0.0.1:8000" 
}

Write-Host "📦 Building frontend with API URL: $env:VITE_API_BASE_URL" -ForegroundColor Yellow

Push-Location tmp_lovable
npm ci
npm run build
Pop-Location

Write-Host "🌐 Starting FastAPI server on port 8000..." -ForegroundColor Yellow
Write-Host "   Frontend: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "   API: http://127.0.0.1:8000/api/health" -ForegroundColor Cyan
Write-Host "   Upload: http://127.0.0.1:8000/api/upload" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray

python test_backend_simple.py
