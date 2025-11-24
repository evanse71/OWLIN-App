$ErrorActionPreference = "Stop"

# Production runner with optimized uvicorn settings
if (-not $env:VITE_API_BASE_URL) { $env:VITE_API_BASE_URL = "http://127.0.0.1:8000" }
if (-not $env:OWLIN_SINGLE_PORT) { $env:OWLIN_SINGLE_PORT = "1" }

# Build frontend
Write-Host "Building frontend..." -ForegroundColor Yellow
Push-Location tmp_lovable
npm ci
npm run build
Pop-Location

# Start with production settings
Write-Host "Starting OWLIN in production mode..." -ForegroundColor Green
uvicorn test_backend_simple:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 10 --proxy-headers --access-log --log-level info
