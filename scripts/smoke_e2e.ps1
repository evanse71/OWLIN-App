# OWLIN E2E Smoke Test - PowerShell Version
param(
    [string]$BackendUrl = "http://127.0.0.1:8000"
)

Write-Host "🔍 OWLIN E2E Smoke Test" -ForegroundColor Cyan
Write-Host "=======================" -ForegroundColor Cyan

# Test 1: Backend health check
Write-Host "▶ Backend health" -ForegroundColor Yellow
try {
    $healthResponse = Invoke-RestMethod -Uri "$BackendUrl/api/health" -Method Get -TimeoutSec 5
    if ($healthResponse.status -eq "ok") {
        Write-Host "✅ Backend health: OK" -ForegroundColor Green
    } else {
        Write-Host "❌ Backend health: FAILED" -ForegroundColor Red
        Write-Host "   Make sure backend is running: uvicorn backend.main:app --host 0.0.0.0 --port 8000" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Backend health: FAILED" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "   Make sure backend is running: uvicorn backend.main:app --host 0.0.0.0 --port 8000" -ForegroundColor Red
    exit 1
}

# Test 2: Upload sample PDF
Write-Host "▶ Upload sample PDF" -ForegroundColor Yellow
$testFile = "$env:TEMP\owlin_smoke.pdf"

# Create a minimal PDF for testing
$pdfContent = "%PDF-1.4`n1 0 obj`n<< /Type /Catalog /Pages 2 0 R >>`nendobj`n2 0 obj`n<< /Type /Pages /Count 0 >>`nendobj`ntrailer << /Root 1 0 R >>`n%%EOF"
$pdfContent | Out-File -FilePath $testFile -Encoding ASCII

try {
    # Test upload endpoint
    $form = @{
        file = Get-Item $testFile
    }
    $uploadResponse = Invoke-RestMethod -Uri "$BackendUrl/api/upload" -Method Post -Form $form -TimeoutSec 10
    
    if ($uploadResponse.ok -eq $true) {
        Write-Host "✅ Upload test: OK" -ForegroundColor Green
        Write-Host "   File: $($uploadResponse.filename), Size: $($uploadResponse.bytes) bytes" -ForegroundColor Gray
    } else {
        Write-Host "❌ Upload test: FAILED" -ForegroundColor Red
        Write-Host "   Response: $($uploadResponse | ConvertTo-Json)" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Upload test: FAILED" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "   Check backend logs for upload errors" -ForegroundColor Red
    exit 1
}

# Test 3: CORS configuration
Write-Host "▶ CORS configuration" -ForegroundColor Yellow
try {
    $corsResponse = Invoke-WebRequest -Uri "$BackendUrl/api/health" -Method Options -Headers @{
        "Origin" = "http://localhost:3000"
        "Access-Control-Request-Method" = "POST"
        "Access-Control-Request-Headers" = "Content-Type"
    } -TimeoutSec 5
    
    if ($corsResponse.Headers["Access-Control-Allow-Origin"]) {
        Write-Host "✅ CORS test: OK" -ForegroundColor Green
    } else {
        Write-Host "❌ CORS test: FAILED" -ForegroundColor Red
        Write-Host "   Check CORS configuration in backend" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ CORS test: FAILED" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "   Check CORS configuration in backend" -ForegroundColor Red
    exit 1
}

# Cleanup
Remove-Item $testFile -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "🎉 All E2E smoke tests passed!" -ForegroundColor Green
Write-Host "✅ Backend health: OK" -ForegroundColor Green
Write-Host "✅ Upload endpoint: OK" -ForegroundColor Green
Write-Host "✅ CORS configuration: OK" -ForegroundColor Green
Write-Host ""
Write-Host "The upload path is working end-to-end!" -ForegroundColor Green
