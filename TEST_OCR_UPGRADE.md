# OCR Upgrade Phase 3 - Test Instructions

## Quick Test Commands

Run these in PowerShell (backend on port 8000):

### 1. Red Dragon Invoice Test

```powershell
$inv = "2e1c65d2-ea57-4fc5-ab6c-5ed67d45dabc__26.08INV.jpeg"
$resp = Invoke-RestMethod -Uri "http://localhost:8000/api/dev/ocr-test?filename=$inv" -TimeoutSec 90
Write-Host "line_items_count: $($resp.line_items_count)"
Write-Host "sum_line_total: $($resp.sum_line_total)"
Write-Host "value_coverage: $($resp.value_coverage)"
Write-Host "parity_rating: $($resp.parity_rating)"
$resp | ConvertTo-Json -Depth 10
```

**Expected:**
- line_items_count ≥ 4
- sum_line_total ≥ 209.31
- value_coverage > 0.14 (target: 0.5-0.8)

### 2. Stori PDF Test

```powershell
$inv = "511c1001-be82-4b12-a942-84dd6cf54aa5__Storiinvoiceonly1_Fresh_20251204_212828.pdf"
$resp = Invoke-RestMethod -Uri "http://localhost:8000/api/dev/ocr-test?filename=$inv" -TimeoutSec 90
Write-Host "supplier_name: $($resp.supplier_name)"
Write-Host "line_items_count: $($resp.line_items_count)"
Write-Host "sum_line_total: $($resp.sum_line_total)"
Write-Host "value_coverage: $($resp.value_coverage)"
```

**Expected:**
- supplier_name correct
- line_items_count > 0
- sum_line_total reasonable
- value_coverage > 0.0

## All 8 Modules Implemented ✅

Ready to test!
