# Test OCR with Python 3.11 Backend
# Make sure backend is running first (start_backend_python311.ps1)

Write-Host "🧪 Testing OCR with Python 3.11 Backend..." -ForegroundColor Green

# Wait for backend to be ready
Write-Host "`n[1/3] Waiting for backend to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0
while ($attempt -lt $maxAttempts) {
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:8000/api/health" -TimeoutSec 2 -ErrorAction Stop
        Write-Host "✅ Backend is ready!" -ForegroundColor Green
        break
    } catch {
        $attempt++
        if ($attempt -ge $maxAttempts) {
            Write-Host "❌ Backend not responding after 60 seconds" -ForegroundColor Red
            Write-Host "   Make sure backend is running: .\start_backend_python311.ps1" -ForegroundColor Yellow
            exit 1
        }
        Start-Sleep -Seconds 2
        Write-Host "  Waiting... ($attempt/$maxAttempts)" -ForegroundColor Gray
    }
}

# List available PDFs
Write-Host "`n[2/3] Listing available PDFs..." -ForegroundColor Yellow
try {
    $uploads = Invoke-RestMethod -Uri "http://localhost:8000/api/dev/ocr-test?list_uploads=true" -TimeoutSec 10
    Write-Host "✅ Found $($uploads.total) PDFs" -ForegroundColor Green
    if ($uploads.available_pdfs.Count -gt 0) {
        Write-Host "  Sample: $($uploads.available_pdfs[0])" -ForegroundColor Cyan
    }
} catch {
    Write-Host "⚠️  Could not list uploads: $_" -ForegroundColor Yellow
}

# Test OCR on Stori invoice
Write-Host "`n[3/3] Testing OCR on Stori invoice..." -ForegroundColor Yellow
$filename = "112be37d-afe1-4fe6-8eed-723ccbd70b58__Storiinvoiceonly1.pdf"
Write-Host "  File: $filename" -ForegroundColor Cyan
Write-Host "  This may take 30-60 seconds..." -ForegroundColor Cyan

try {
    $startTime = Get-Date
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/dev/ocr-test?filename=$filename" -TimeoutSec 180
    $duration = ((Get-Date) - $startTime).TotalSeconds
    
    Write-Host "`n✅ OCR Test Complete! (took $([math]::Round($duration, 1))s)" -ForegroundColor Green
    Write-Host "`n=== RESULTS ===" -ForegroundColor Cyan
    Write-Host "  Status: $($response.status)" -ForegroundColor White
    Write-Host "  Line Items: $($response.ocr_result.line_items_count)" -ForegroundColor White
    Write-Host "  Supplier: $($response.ocr_result.supplier)" -ForegroundColor White
    Write-Host "  Total: £$($response.ocr_result.total)" -ForegroundColor White
    Write-Host "  Confidence: $($response.ocr_result.confidence)" -ForegroundColor White
    
    $textSample = $response.raw_ocr_text_sample
    if ($textSample -and $textSample.Length -gt 0) {
        Write-Host "`n  OCR Text Sample (first 200 chars):" -ForegroundColor Cyan
        Write-Host "  $($textSample.Substring(0, [Math]::Min(200, $textSample.Length)))" -ForegroundColor Gray
    } else {
        Write-Host "`n  ⚠️  No OCR text extracted" -ForegroundColor Yellow
    }
    
    # Save full response
    $response | ConvertTo-Json -Depth 10 | Out-File "PYTHON311_VICTORY.json"
    Write-Host "`n  Full response saved to: PYTHON311_VICTORY.json" -ForegroundColor Cyan
    
    # Check if we got real data
    if ($response.ocr_result.line_items_count -gt 1 -and $response.ocr_result.supplier -ne "Unknown Supplier") {
        Write-Host "`n🎉 SUCCESS! OCR is working with Python 3.11!" -ForegroundColor Green
    } else {
        Write-Host "`n⚠️  OCR ran but extracted limited data. Check PYTHON311_VICTORY.json for details." -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "`n❌ OCR Test Failed!" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
    Write-Host "`n  Check backend logs for details." -ForegroundColor Yellow
    exit 1
}

Write-Host "`n"

