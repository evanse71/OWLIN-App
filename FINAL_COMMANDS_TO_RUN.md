# Final Commands to Run - Complete Testing Sequence

## Current Status

**Backend**: Running in Terminal 7 (port 8000)  
**Endpoint**: Working (lists 54 PDFs)  
**Issue**: PaddleOCR not extracting text from images

---

## Commands to Run Now (Terminal 2)

### 1. Navigate to Project
```powershell
cd C:\Users\tedev\FixPack_2025-11-02_133105
```

### 2. Test PaddleOCR Loads
```powershell
python -c "from paddleocr import PaddleOCR; ocr = PaddleOCR(use_textline_orientation=True, lang='en'); print('PaddleOCR loads OK')"
```

### 3. Test OCR on Preprocessed Image
```powershell
python -c "from paddleocr import PaddleOCR; ocr = PaddleOCR(use_textline_orientation=True, lang='en'); result = ocr.predict('data/uploads/112be37d-afe1-4fe6-8eed-723ccbd70b58__storiinvoiceonly1/pages/page_001.pre.png'); print('Detected:', len(result), 'regions')"
```

### 4. Test Layout Detection
```powershell
python -c "from backend.ocr.layout_detector import detect_document_layout; from pathlib import Path; result = detect_document_layout(Path('data/uploads/112be37d-afe1-4fe6-8eed-723ccbd70b58__storiinvoiceonly1/pages/page_001.pre.png'), 1, True); print('Blocks:', len(result.blocks))"
```

### 5. Run Full OCR Test
```powershell
$filename = "112be37d-afe1-4fe6-8eed-723ccbd70b58__Storiinvoiceonly1.pdf"
$response = Invoke-RestMethod -Uri "http://localhost:8000/api/dev/ocr-test?filename=$filename"

Write-Host "Results:"
Write-Host "  Line Items: $($response.ocr_result.line_items_count)"
Write-Host "  Supplier: $($response.ocr_result.supplier)"
Write-Host "  Total: $($response.ocr_result.total)"
Write-Host "  Confidence: $($response.ocr_result.confidence)"

# Save full response
$response | ConvertTo-Json -Depth 10 | Out-File "final_ocr_test.json"
Write-Host "  Saved to: final_ocr_test.json"
```

### 6. Check Backend Logs
In Terminal 7 (backend), look for:
- `PaddleOCR loaded successfully` (should appear after reload)
- `[LAYOUT] Detected X blocks` (should be > 1)
- `[TABLE_DETECT] Extracted X line items` (should be > 0)
- Any errors or warnings

---

## Alternative: Test with Simple Image

If the preprocessed image is corrupted, test with the original PNG:

```powershell
python -c "from paddleocr import PaddleOCR; ocr = PaddleOCR(use_textline_orientation=True, lang='en'); result = ocr.predict('data/uploads/112be37d-afe1-4fe6-8eed-723ccbd70b58__storiinvoiceonly1/pages/page_001.png'); print('Detected:', len(result), 'regions')"
```

---

## What to Share for Final Fix

1. **Output from command 2** (PaddleOCR loads?)
2. **Output from command 3** (OCR detects text?)
3. **Output from command 4** (Layout detects blocks?)
4. **Backend logs** from Terminal 7 after running command 5
5. **final_ocr_test.json** contents

---

## Expected After All Fixes

```
PaddleOCR loads OK
Detected: 15 regions
Blocks: 8
Results:
  Line Items: 12
  Supplier: Stori Beer & Wine CYF
  Total: 123.45
  Confidence: 0.85
```

---

## All Fixes Applied So Far

1. ✅ DPI 200→300
2. ✅ Feature flags enabled
3. ✅ Import paths fixed (`ocr.` → `backend.ocr.`)
4. ✅ Endpoint enhanced
5. ✅ Route order fixed
6. ✅ PaddleOCR parameters updated
7. ✅ Logging enhanced

---

**Status**: Ready for final testing  
**Action**: Run commands 1-6 above and share results

