# Test OCR Endpoint with Enhanced Features
Write-Host "=" * 80
Write-Host "TESTING ENHANCED OCR ENDPOINT"
Write-Host "=" * 80

# Test 1: List available PDFs
Write-Host "`n[TEST 1] Listing available PDFs..."
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/dev/ocr-test?list_uploads=true" -ErrorAction Stop
    Write-Host "✅ Found $($response.count) PDFs"
    if ($response.count -gt 0) {
        Write-Host "   Sample PDFs:"
        $response.available_pdfs | Select-Object -First 5 | ForEach-Object { Write-Host "      - $_" }
    }
    $testPdf = $response.available_pdfs | Where-Object { $_ -like "*Stori*" } | Select-Object -First 1
    if (-not $testPdf) {
        $testPdf = $response.available_pdfs[0]
    }
    Write-Host "`n   Selected test PDF: $testPdf"
} catch {
    Write-Host "❌ Error listing PDFs: $($_.Exception.Message)"
    Write-Host "   Is backend running? Try: python -m uvicorn backend.main:app --port 8000 --reload"
    exit 1
}

# Test 2: Test OCR on selected PDF
if ($testPdf) {
    Write-Host "`n[TEST 2] Testing OCR on: $testPdf"
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/api/dev/ocr-test?filename=$testPdf" -ErrorAction Stop
        
        Write-Host "✅ OCR Test Complete"
        Write-Host "   Status: $($response.status)"
        Write-Host "   Page Count: $($response.page_count)"
        Write-Host "   DPI Used: $($response.raster_dpi_used)"
        Write-Host "   Feature Flags:"
        Write-Host "      Preproc: $($response.feature_flags.preproc)"
        Write-Host "      Layout: $($response.feature_flags.layout)"
        Write-Host "      Tables: $($response.feature_flags.tables)"
        Write-Host "   OCR Result:"
        Write-Host "      Supplier: $($response.ocr_result.supplier)"
        Write-Host "      Date: $($response.ocr_result.date)"
        Write-Host "      Total: $($response.ocr_result.total)"
        Write-Host "      Line Items: $($response.ocr_result.line_items_count)"
        Write-Host "      Confidence: $($response.ocr_result.confidence)"
        
        if ($response.ocr_result.line_items_count -gt 0) {
            Write-Host "`n   Sample Line Items:"
            $response.ocr_result.line_items | Select-Object -First 3 | ForEach-Object {
                Write-Host "      - $($_.desc): $($_.qty) x $($_.unit_price) = $($_.total)"
            }
        }
        
        # Save full response
        $outputFile = "ocr_test_output_$($testPdf.Replace('.pdf', '')).json"
        $response | ConvertTo-Json -Depth 10 | Out-File $outputFile
        Write-Host "`n   Full response saved to: $outputFile"
        
    } catch {
        Write-Host "❌ Error testing OCR: $($_.Exception.Message)"
        if ($_.ErrorDetails) {
            Write-Host "   Details: $($_.ErrorDetails.Message)"
        }
    }
}

# Test 3: Test with wrong filename
Write-Host "`n[TEST 3] Testing error handling (wrong filename)..."
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/dev/ocr-test?filename=nonexistent.pdf" -ErrorAction Stop
    Write-Host "   Response: $($response.error)"
    Write-Host "   Hint: $($response.hint)"
} catch {
    Write-Host "   Expected error received (good)"
}

Write-Host "`n" + "=" * 80
Write-Host "TESTING COMPLETE"
Write-Host "=" * 80
Write-Host "`nNext Steps:"
Write-Host "1. Check backend console logs for [TABLE_EXTRACT], [TABLE_FAIL], [FALLBACK] markers"
Write-Host "2. Review the saved JSON file for raw_paddleocr_pages data"
Write-Host "3. If line_items_count is 0, check logs for why table extraction failed"

