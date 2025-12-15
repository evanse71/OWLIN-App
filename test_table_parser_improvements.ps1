# Test Table Parser Improvements
# Tests the improved table parser on the Stori invoice

Write-Host "`n🧪 Testing Table Parser Improvements`n" -ForegroundColor Cyan

# Check if backend is running
Write-Host "[1/4] Checking backend status..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/api/health" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✅ Backend is running`n" -ForegroundColor Green
} catch {
    Write-Host "❌ Backend not running. Please start it first:`n" -ForegroundColor Red
    Write-Host "  cd C:\Users\tedev\FixPack_2025-11-02_133105" -ForegroundColor Gray
    Write-Host "  & .\.venv311\Scripts\Activate.ps1" -ForegroundColor Gray
    Write-Host "  python -m uvicorn backend.main:app --port 8000 --reload`n" -ForegroundColor Gray
    exit 1
}

# Test the Stori invoice
Write-Host "[2/4] Testing Stori invoice..." -ForegroundColor Yellow
$filename = "112be37d-afe1-4fe6-8eed-723ccbd70b58__Storiinvoiceonly1.pdf"

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/dev/ocr-test?filename=$filename" -TimeoutSec 180 -ErrorAction Stop
    Write-Host "✅ OCR processing complete`n" -ForegroundColor Green
} catch {
    Write-Host "❌ OCR test failed: $_`n" -ForegroundColor Red
    exit 1
}

# Analyze results
Write-Host "[3/4] Analyzing results..." -ForegroundColor Yellow

# Check header fields
Write-Host "`n📋 Header Fields:" -ForegroundColor Cyan
Write-Host "  Supplier: $($response.ocr_result.supplier)" -ForegroundColor White
Write-Host "  Date: $($response.ocr_result.date)" -ForegroundColor White
Write-Host "  Total: £$($response.ocr_result.total)" -ForegroundColor White
Write-Host "  Invoice No: $($response.ocr_result.invoice_no)" -ForegroundColor White
Write-Host "  Confidence: $($response.ocr_result.confidence)" -ForegroundColor White

# Check table extraction
$tableBlock = $response.raw_paddleocr_pages[0].blocks | Where-Object { $_.type -eq "table" }

if ($tableBlock) {
    Write-Host "`n📊 Table Extraction:" -ForegroundColor Cyan
    Write-Host "  Method: $($tableBlock.table_data.method_used)" -ForegroundColor White
    Write-Host "  Line Items Count: $($tableBlock.table_data.line_items.Count)" -ForegroundColor White
    Write-Host "  Confidence: $($tableBlock.table_data.confidence)" -ForegroundColor White
    
    if ($tableBlock.table_data.line_items.Count -gt 0) {
        Write-Host "`n  Line Items:" -ForegroundColor Cyan
        $tableBlock.table_data.line_items | ForEach-Object {
            Write-Host "    • $($_.description)" -ForegroundColor Gray
            Write-Host "      Qty: $($_.quantity) | Unit: £$($_.unit_price) | Total: £$($_.total_price)" -ForegroundColor Gray
        }
    }
}

# Validation
Write-Host "`n[4/4] Validation:" -ForegroundColor Yellow

$passed = 0
$failed = 0

# Test 1: Supplier correct
if ($response.ocr_result.supplier -match "Stori Beer") {
    Write-Host "  ✅ Supplier correct" -ForegroundColor Green
    $passed++
} else {
    Write-Host "  ❌ Supplier incorrect: $($response.ocr_result.supplier)" -ForegroundColor Red
    $failed++
}

# Test 2: Total correct
if ($response.ocr_result.total -eq 289.17) {
    Write-Host "  ✅ Total correct (£289.17)" -ForegroundColor Green
    $passed++
} else {
    Write-Host "  ❌ Total incorrect: £$($response.ocr_result.total)" -ForegroundColor Red
    $failed++
}

# Test 3: Date correct
if ($response.ocr_result.date -match "2025-08-21") {
    Write-Host "  ✅ Date correct (2025-08-21)" -ForegroundColor Green
    $passed++
} else {
    Write-Host "  ❌ Date incorrect: $($response.ocr_result.date)" -ForegroundColor Red
    $failed++
}

# Test 4: Invoice number NOT invented
if ($response.ocr_result.invoice_no -and $response.ocr_result.invoice_no -notmatch "INV-[a-f0-9]{8}") {
    Write-Host "  ✅ Invoice number from header (not invented)" -ForegroundColor Green
    $passed++
} else {
    Write-Host "  ⚠️  Invoice number may be invented: $($response.ocr_result.invoice_no)" -ForegroundColor Yellow
    # Don't fail - might be legitimately missing
}

# Test 5: Text-based parsing used
if ($tableBlock.table_data.method_used -eq "text_based_parsing") {
    Write-Host "  ✅ Using text-based parsing" -ForegroundColor Green
    $passed++
} else {
    Write-Host "  ⚠️  Method: $($tableBlock.table_data.method_used)" -ForegroundColor Yellow
}

# Test 6: Exactly 2 line items
if ($tableBlock.table_data.line_items.Count -eq 2) {
    Write-Host "  ✅ Exactly 2 line items extracted" -ForegroundColor Green
    $passed++
} else {
    Write-Host "  ❌ Expected 2 line items, got $($tableBlock.table_data.line_items.Count)" -ForegroundColor Red
    $failed++
}

# Test 7: Line items have descriptions
$hasDescriptions = $true
foreach ($item in $tableBlock.table_data.line_items) {
    if (-not $item.description -or $item.description.Length -lt 5) {
        $hasDescriptions = $false
        break
    }
}
if ($hasDescriptions) {
    Write-Host "  ✅ All line items have descriptions" -ForegroundColor Green
    $passed++
} else {
    Write-Host "  ❌ Some line items missing descriptions" -ForegroundColor Red
    $failed++
}

# Test 8: Line items have quantities
$hasQuantities = $true
foreach ($item in $tableBlock.table_data.line_items) {
    if (-not $item.quantity) {
        $hasQuantities = $false
        break
    }
}
if ($hasQuantities) {
    Write-Host "  ✅ All line items have quantities" -ForegroundColor Green
    $passed++
} else {
    Write-Host "  ❌ Some line items missing quantities" -ForegroundColor Red
    $failed++
}

# Test 9: Line items have prices (unit or total)
$hasPrices = $true
foreach ($item in $tableBlock.table_data.line_items) {
    if (-not $item.unit_price -and -not $item.total_price) {
        $hasPrices = $false
        break
    }
}
if ($hasPrices) {
    Write-Host "  ✅ All line items have prices" -ForegroundColor Green
    $passed++
} else {
    Write-Host "  ❌ Some line items missing prices" -ForegroundColor Red
    $failed++
}

# Test 10: No summary rows (check descriptions don't contain summary keywords)
$hasSummaryRows = $false
$summaryKeywords = @('subtotal', 'vat', 'total', 'balance', 'due')
foreach ($item in $tableBlock.table_data.line_items) {
    $desc = $item.description.ToLower()
    foreach ($keyword in $summaryKeywords) {
        if ($desc -match $keyword) {
            $hasSummaryRows = $true
            Write-Host "  ❌ Found summary row in line items: $($item.description)" -ForegroundColor Red
            break
        }
    }
}
if (-not $hasSummaryRows) {
    Write-Host "  ✅ No summary rows in line items" -ForegroundColor Green
    $passed++
} else {
    $failed++
}

# Summary
Write-Host "`n" -NoNewline
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Gray
Write-Host "Results: " -NoNewline -ForegroundColor Cyan
Write-Host "$passed passed" -NoNewline -ForegroundColor Green
Write-Host ", " -NoNewline
Write-Host "$failed failed" -ForegroundColor Red
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Gray

if ($failed -eq 0) {
    Write-Host "`n🎉 All tests passed! Table parser improvements working correctly.`n" -ForegroundColor Green
} else {
    Write-Host "`n⚠️  Some tests failed. Review the output above for details.`n" -ForegroundColor Yellow
}

# Save full response for inspection
$response | ConvertTo-Json -Depth 10 | Out-File "table_parser_test_results.json"
Write-Host "Full results saved to: table_parser_test_results.json`n" -ForegroundColor Gray

