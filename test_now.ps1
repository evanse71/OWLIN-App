# Comprehensive OCR Test - Works even if backend needs restart
param(
    [string]$TestPdf = ""
)

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "COMPREHENSIVE OCR TEST" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# Ensure we're in the right directory
$projectRoot = "C:\Users\tedev\FixPack_2025-11-02_133105"
if ((Get-Location).Path -ne $projectRoot) {
    Write-Host "Changing to project directory: $projectRoot" -ForegroundColor Yellow
    Set-Location $projectRoot
}

# Step 1: Check if backend is running
Write-Host "[STEP 1] Checking backend status..." -ForegroundColor Cyan
$backendRunning = $false
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/api/health" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✅ Backend is running" -ForegroundColor Green
    Write-Host "   Status: $($health.status)" -ForegroundColor Gray
    $backendRunning = $true
} catch {
    Write-Host "❌ Backend is NOT running" -ForegroundColor Red
    Write-Host ""
    Write-Host "To start backend, run in another terminal:" -ForegroundColor Yellow
    Write-Host "   .\backend\auto_start.ps1" -ForegroundColor White
    Write-Host ""
    Write-Host "Or manually:" -ForegroundColor Yellow
    Write-Host "   python -m uvicorn backend.main:app --port 8000 --reload" -ForegroundColor White
    Write-Host ""
    exit 1
}

# Step 2: List available PDFs
Write-Host ""
Write-Host "[STEP 2] Listing available PDFs..." -ForegroundColor Cyan
try {
    $listResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/dev/ocr-test?list_uploads=true" -ErrorAction Stop
    Write-Host "✅ Found $($listResponse.count) PDFs" -ForegroundColor Green
    
    # Pick test PDF
    if ($TestPdf -eq "") {
        # Try to find a Stori invoice
        $TestPdf = $listResponse.available_pdfs | Where-Object { $_ -like "*Stori*" } | Select-Object -First 1
        if (-not $TestPdf) {
            $TestPdf = $listResponse.available_pdfs[0]
        }
    }
    
    Write-Host "   Selected PDF: $TestPdf" -ForegroundColor Cyan
    
} catch {
    Write-Host "❌ Error listing PDFs: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "   Response: $($_.ErrorDetails.Message)" -ForegroundColor Gray
    exit 1
}

# Step 3: Test OCR
Write-Host ""
Write-Host "[STEP 3] Running OCR test on: $TestPdf" -ForegroundColor Cyan
Write-Host "   (This may take 10-30 seconds...)" -ForegroundColor Yellow
Write-Host ""

try {
    $startTime = Get-Date
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/dev/ocr-test?filename=$TestPdf" -ErrorAction Stop
    $elapsed = ((Get-Date) - $startTime).TotalSeconds
    
    Write-Host "✅ OCR Test Complete! (took $([math]::Round($elapsed, 1))s)" -ForegroundColor Green
    Write-Host ""
    Write-Host "=" * 80 -ForegroundColor Cyan
    Write-Host "RESULTS" -ForegroundColor Cyan
    Write-Host "=" * 80 -ForegroundColor Cyan
    Write-Host ""
    
    # System Info
    Write-Host "System:" -ForegroundColor Yellow
    Write-Host "  Status: $($response.status)"
    Write-Host "  Page Count: $($response.page_count)"
    Write-Host "  DPI Used: $($response.raster_dpi_used)"
    Write-Host "  Processing Time: $([math]::Round($elapsed, 1))s"
    Write-Host ""
    
    # Feature Flags
    Write-Host "Feature Flags:" -ForegroundColor Yellow
    Write-Host "  Preprocessing: $($response.feature_flags.preproc)"
    Write-Host "  Layout Detection: $($response.feature_flags.layout)"
    Write-Host "  Table Extraction: $($response.feature_flags.tables)"
    Write-Host ""
    
    # Extraction Results
    Write-Host "Extraction:" -ForegroundColor Yellow
    Write-Host "  Supplier: $($response.ocr_result.supplier)"
    Write-Host "  Date: $($response.ocr_result.date)"
    Write-Host "  Total: £$($response.ocr_result.total)"
    Write-Host "  Confidence: $($response.ocr_result.confidence)"
    Write-Host "  Line Items: $($response.ocr_result.line_items_count)" -ForegroundColor $(if ($response.ocr_result.line_items_count -gt 0) { "Green" } else { "Red" })
    Write-Host ""
    
    # Line Items
    if ($response.ocr_result.line_items_count -gt 0) {
        Write-Host "Sample Line Items:" -ForegroundColor Green
        $response.ocr_result.line_items | Select-Object -First 5 | ForEach-Object {
            Write-Host "  - $($_.desc): $($_.qty) x £$($_.unit_price) = £$($_.total)"
        }
    } else {
        Write-Host "⚠️  NO LINE ITEMS EXTRACTED!" -ForegroundColor Red
        Write-Host ""
        Write-Host "Diagnostic Info:" -ForegroundColor Yellow
        Write-Host "  - Check backend logs for [TABLE_FAIL] or [FALLBACK] markers"
        Write-Host "  - raw_paddleocr_pages count: $($response.raw_paddleocr_pages.Count)"
        if ($response.raw_ocr_text_sample) {
            Write-Host "  - OCR text detected: Yes ($(($response.raw_ocr_text_sample).Length) chars)"
        } else {
            Write-Host "  - OCR text detected: No"
        }
    }
    
    # Save full response
    $outputFile = "ocr_test_result_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
    $response | ConvertTo-Json -Depth 10 | Out-File $outputFile
    Write-Host ""
    Write-Host "Full response saved to: $outputFile" -ForegroundColor Cyan
    
    # Next steps
    Write-Host ""
    Write-Host "=" * 80 -ForegroundColor Cyan
    Write-Host "NEXT STEPS" -ForegroundColor Cyan
    Write-Host "=" * 80 -ForegroundColor Cyan
    Write-Host ""
    
    if ($response.ocr_result.line_items_count -eq 0) {
        Write-Host "To debug empty line items:" -ForegroundColor Yellow
        Write-Host "1. Check backend console logs for these markers:"
        Write-Host "   [PAGE_PROC] - Page rasterization"
        Write-Host "   [TABLE_DETECT] - Table detection attempts"
        Write-Host "   [TABLE_EXTRACT] - Line item extraction"
        Write-Host "   [TABLE_FAIL] - Why table extraction failed"
        Write-Host "   [FALLBACK] - Regex fallback attempts"
        Write-Host ""
        Write-Host "2. Review $outputFile for:"
        Write-Host "   - raw_paddleocr_pages[0].blocks (should have table blocks)"
        Write-Host "   - raw_ocr_text_sample (should have invoice text)"
        Write-Host ""
        Write-Host "3. Share with debugging partner:"
        Write-Host "   - Backend console logs (copy [TABLE_*] markers)"
        Write-Host "   - $outputFile"
        Write-Host "   - PDF filename: $TestPdf"
    } else {
        Write-Host "✅ Line items extracted successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Test with more PDFs:" -ForegroundColor Yellow
        Write-Host "   .\test_now.ps1 -TestPdf 'another-file.pdf'"
    }
    
} catch {
    Write-Host "❌ Error testing OCR: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ErrorDetails) {
        Write-Host "   Details: $($_.ErrorDetails.Message)" -ForegroundColor Gray
    }
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "1. Check backend is still running"
    Write-Host "2. Check backend logs for errors"
    Write-Host "3. Try a different PDF: .\test_now.ps1 -TestPdf 'filename.pdf'"
    exit 1
}

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan

