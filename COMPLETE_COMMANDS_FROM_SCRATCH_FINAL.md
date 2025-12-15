# Complete Commands From Scratch - FINAL VERSION

## All Fixes Applied ✅

1. DPI: 200 → 300
2. Feature flags: All enabled
3. Import paths: Fixed (`ocr.` → `backend.ocr.`)
4. Endpoint: Enhanced with upload listing
5. Route order: Fixed (SPA fallback moved to end)
6. PaddleOCR: Parameters updated for new API
7. Logging: Enhanced throughout

---

## Terminal 1: Backend (if not already running)

```powershell
cd C:\Users\tedev\FixPack_2025-11-02_133105
python -m uvicorn backend.main:app --port 8000 --reload
```

**Keep this running** - shows backend logs

---

## Terminal 2: Run Tests

```powershell
cd C:\Users\tedev\FixPack_2025-11-02_133105

# Test 1: List available PDFs
curl "http://localhost:8000/api/dev/ocr-test?list_uploads=true"

# Test 2: Run OCR on Stori invoice
$filename = "112be37d-afe1-4fe6-8eed-723ccbd70b58__Storiinvoiceonly1.pdf"
$response = Invoke-RestMethod -Uri "http://localhost:8000/api/dev/ocr-test?filename=$filename"

# Show results
Write-Host "Line Items: $($response.ocr_result.line_items_count)"
Write-Host "Supplier: $($response.ocr_result.supplier)"
Write-Host "Total: $($response.ocr_result.total)"
Write-Host "Confidence: $($response.ocr_result.confidence)"

# Save full JSON
$response | ConvertTo-Json -Depth 10 | Out-File "ocr_test_final.json"
Get-Content ocr_test_final.json
```

---

## Or Use Test Script

```powershell
cd C:\Users\tedev\FixPack_2025-11-02_133105
.\test_now.ps1
```

---

## What to Check in Backend Logs (Terminal 1)

After running the test, look for:
- `[PAGE_PROC] Page 1/1: page_001.png, size=25.37MB` ✅
- `[LAYOUT] Detected X blocks` (should be > 1)
- `PaddleOCR loaded successfully` (should appear now)
- `[TABLE_DETECT] Extracted X line items` (should be > 0)
- `[TABLE_EXTRACT] First item sample` (should have data)

---

## Current Known Issue

**Layout detection only finding 1 block** (entire page as one table cell)

This causes:
- OCR to scan 260MB image (entire page)
- No structured table extraction
- Empty cell text

**Possible causes**:
1. Layout detector using OpenCV fallback (not finding table structure)
2. Preprocessed image too processed (lost structure)
3. Need better table detection algorithm

---

## Next Diagnostic Commands

```powershell
# Check preprocessed vs original image
python -c "
from PIL import Image
orig = Image.open('data/uploads/112be37d-afe1-4fe6-8eed-723ccbd70b58__storiinvoiceonly1/pages/page_001.png')
prep = Image.open('data/uploads/112be37d-afe1-4fe6-8eed-723ccbd70b58__storiinvoiceonly1/pages/page_001.pre.png')
print(f'Original: {orig.size}, mode: {orig.mode}')
print(f'Preprocessed: {prep.size}, mode: {prep.mode}')
"

# Test PaddleOCR on original (non-preprocessed) image
python -c "
from paddleocr import PaddleOCR
ocr = PaddleOCR(use_textline_orientation=True, lang='en')
result = ocr.predict('data/uploads/112be37d-afe1-4fe6-8eed-723ccbd70b58__storiinvoiceonly1/pages/page_001.png')
print(f'Original image: Detected {len(result)} regions')
"
```

---

## Summary

**Infrastructure**: ✅ All working  
**PaddleOCR**: ✅ Loads successfully  
**Issue**: Layout detection finding only 1 block → OCR fails on huge image  
**Next**: Test PaddleOCR on original vs preprocessed image to see which works better

