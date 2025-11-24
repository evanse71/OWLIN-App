# Quick-Deploy.ps1
# Fast build and deploy - skips npm install

$ErrorActionPreference = "Stop"

Write-Host "Quick Deploy to Port 8000..." -ForegroundColor Cyan

Push-Location "source_extracted\tmp_lovable"
npm run build
Pop-Location

Copy-Item "source_extracted\tmp_lovable\out\*" -Destination "backend\static\" -Recurse -Force

Write-Host "✓ Deployed" -ForegroundColor Green
Write-Host "Run: python -m uvicorn backend.main:app --port 8000" -ForegroundColor Yellow

