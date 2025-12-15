# Ready for Live OCR Testing ✅

**Date**: 2025-12-02  
**Status**: All diagnostic infrastructure in place

## What's Been Applied

### Core Fixes
1. ✅ DPI increased from 200 to 300
2. ✅ Feature flags enabled (PREPROC, LAYOUT, TABLES)
3. ✅ Import error fixed (CandidateFeatureSummary)
4. ✅ Enhanced logging throughout pipeline

### Diagnostic Tools
1. ✅ Auto-restart script (`backend/auto_start.ps1`)
2. ✅ Quick test script (`quick_test.ps1`)
3. ✅ Enhanced OCR endpoint with upload listing
4. ✅ Table extraction diagnostics

### Available Test Data
- **52 PDFs** in `data/uploads/`
- Multiple Stori invoices (perfect for table testing)
- Sample invoices and attachments

---

## How to Test (Step-by-Step)

### Step 1: Start Backend (Auto-Restart)
```powershell
# Open a new PowerShell terminal
cd C:\Users\tedev\FixPack_2025-11-02_133105
.\backend\auto_start.ps1
```

**What to expect**:
- Backend starts on port 8000
- Auto-restarts if it crashes
- Shows startup logs

### Step 2: Run Quick Test
```powershell
# In another PowerShell terminal
.\quick_test.ps1
```

**What it does**:
1. Checks backend health
2. Lists available PDFs
3. Picks a Stori invoice
4. Runs OCR test
5. Shows results
6. Saves full JSON to `ocr_test_result.json`

### Step 3: Check Results

**In the test output**, look for:
- ✅ `Line Items: X` (should be > 0)
- ✅ `Supplier: Stori Beer & Wine CYF`
- ✅ `Total: £XXX.XX`
- ✅ Sample line items displayed

**In backend logs**, look for:
- `[PAGE_PROC]` - Page rasterization (should show ~2-5MB images)
- `[TABLE_DETECT]` - Table detection attempts
- `[TABLE_EXTRACT]` - Line items extracted
- `[TABLE_FAIL]` - If table extraction failed (explains why)
- `[FALLBACK]` - If regex fallback was used

---

## What to Share for Debugging

If line items are empty (count = 0), share:

### 1. Full JSON Response
```powershell
Get-Content ocr_test_result.json -Raw
```

### 2. Backend Console Logs
Copy the relevant section showing:
- `[OCR_TEST]` - File being tested
- `[PAGE_PROC]` - Page processing
- `[TABLE_DETECT]` - Table detection
- `[TABLE_EXTRACT]` or `[TABLE_FAIL]` - Extraction results
- Any PaddleOCR warnings/errors

### 3. Specific Fields to Check
From the JSON:
- `page_count` - Should be 1 for single-page invoices
- `raster_dpi_used` - Should be 300
- `feature_flags` - All should be `true`
- `raw_paddleocr_pages[0].blocks` - Should have multiple blocks
- `ocr_result.line_items_count` - Should be > 0

---

## Manual Testing (Alternative)

If quick_test.ps1 doesn't work:

### List PDFs
```powershell
curl "http://localhost:8000/api/dev/ocr-test?list_uploads=true"
```

### Test Specific PDF
```powershell
$filename = "4f3314c6-fc96-4302-9c04-ec52725918a8__Storiinvoiceonly1.pdf"
$response = Invoke-RestMethod -Uri "http://localhost:8000/api/dev/ocr-test?filename=$filename"
$response | ConvertTo-Json -Depth 10 | Out-File "ocr_test_result.json"
Get-Content ocr_test_result.json -Raw
```

---

## Diagnostic Log Markers

| Marker | Meaning |
|--------|---------|
| `[OCR_TEST]` | File being tested, size |
| `[PAGE_PROC]` | Page rasterized, size in MB |
| `[TABLE_DETECT]` | Table detection attempt, cells found |
| `[TABLE_EXTRACT]` | Line items extracted from table |
| `[TABLE_FAIL]` | Table data empty, shows raw text |
| `[FALLBACK]` | Regex fallback used, shows raw OCR |
| `[LINE_ITEMS]` | Final line item count |

---

## Expected Behavior

### If Everything Works:
- Backend starts without errors
- Test completes in 10-30 seconds
- Line items > 0
- Supplier, date, total extracted
- Logs show `[TABLE_EXTRACT]` with item counts

### If Table Extraction Fails:
- Line items = 0
- Logs show `[TABLE_FAIL]` with reason
- Logs show `[FALLBACK]` attempt
- JSON has `raw_paddleocr_pages` with blocks but no line items

---

## Files Created

1. `backend/auto_start.ps1` - Auto-restart backend
2. `quick_test.ps1` - Quick OCR test
3. `test_ocr_endpoint.ps1` - Comprehensive test
4. `verify_fixes.py` - Verify all fixes applied
5. `test_ocr_diagnostics.py` - Infrastructure tests
6. `test_dpi_comparison.py` - DPI impact test

---

## Next Steps After Testing

1. **If line items work**: Great! Test with more PDFs
2. **If line items are empty**: Share JSON + logs for targeted fix
3. **If backend crashes**: Auto-restart will handle it, but share error

---

**Status**: ✅ Ready for live testing  
**Action**: Run `.\backend\auto_start.ps1` then `.\quick_test.ps1`

