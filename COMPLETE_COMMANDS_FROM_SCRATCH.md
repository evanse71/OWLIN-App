# Complete Commands From Scratch - OCR Testing

## Terminal 1: Start Backend

```powershell
# Navigate to project
cd C:\Users\tedev\FixPack_2025-11-02_133105

# Start backend with auto-restart
.\backend\auto_start.ps1
```

**Keep this running** - shows backend logs

---

## Terminal 2: Run Tests

```powershell
# Navigate to project
cd C:\Users\tedev\FixPack_2025-11-02_133105

# Test 1: List available PDFs
curl "http://localhost:8000/api/dev/ocr-test?list_uploads=true"

# Test 2: Test OCR on a Stori invoice
$filename = "112be37d-afe1-4fe6-8eed-723ccbd70b58__Storiinvoiceonly1.pdf"
$response = Invoke-RestMethod -Uri "http://localhost:8000/api/dev/ocr-test?filename=$filename"

# Show results
Write-Host "Line items: $($response.ocr_result.line_items_count)"
Write-Host "Supplier: $($response.ocr_result.supplier)"
Write-Host "Total: $($response.ocr_result.total)"

# Save full JSON
$response | ConvertTo-Json -Depth 10 | Out-File "ocr_test_result.json"

# View the file
Get-Content ocr_test_result.json
```

---

## Current Status (After All Fixes)

### ✅ Fixed
- DPI: 200 → 300
- Feature flags: All enabled
- Import error: CandidateFeatureSummary added
- Endpoint: SPA route order fixed
- Import paths: `ocr.` → `backend.ocr.`

### ⚠️ Current Issue
**OCR extraction still failing**:
- `ocr_text: ""`
- `line_items_count: 1` (but empty item)
- `supplier: "Unknown Supplier"`
- `total: 0.0`

**But**:
- Preprocessed image exists (12.9 MB)
- Layout detector module exists
- Imports work

### Next Diagnostic Steps

Check backend logs in Terminal 1 for:
- `[LAYOUT]` - Layout detection results
- `[LAYOUT_IMPORT_FAIL]` - Import errors
- `[LAYOUT_FAIL]` - Runtime errors
- `[TABLE_DETECT]` - Table detection
- Any PaddleOCR errors

---

## All Commands Summary

```powershell
# TERMINAL 1 - Backend
cd C:\Users\tedev\FixPack_2025-11-02_133105
.\backend\auto_start.ps1

# TERMINAL 2 - Testing (wait 10 seconds after Terminal 1 starts)
cd C:\Users\tedev\FixPack_2025-11-02_133105

# Quick test script (recommended)
.\test_now.ps1

# OR manual commands:
curl "http://localhost:8000/api/dev/ocr-test?list_uploads=true"
$filename = "112be37d-afe1-4fe6-8eed-723ccbd70b58__Storiinvoiceonly1.pdf"
Invoke-RestMethod -Uri "http://localhost:8000/api/dev/ocr-test?filename=$filename" | ConvertTo-Json -Depth 10 | Out-File "result.json"
Get-Content result.json
```

---

## What to Share for Further Debugging

1. **Backend logs from Terminal 1** during the test - especially:
   - `[LAYOUT]` markers
   - `[TABLE_DETECT]` markers
   - Any errors or warnings

2. **Full JSON from ocr_test_result.json**

3. **Confirm**: Does `backend/ocr/layout_detector.py` exist and work?
   ```powershell
   python -c "from backend.ocr.layout_detector import detect_document_layout; print('✅ Works')"
   ```

---

**Status**: Import paths fixed, waiting for backend reload to test  
**Next**: Check backend logs to see if layout detection is now working

