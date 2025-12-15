# OCR Issue Identified ✅

**Date**: 2025-12-02  
**Status**: Endpoint working, OCR extraction failing

## Problem Found

### ✅ Endpoint Working
- Upload listing: **54 PDFs found**
- Endpoint responding correctly
- Feature flags enabled (preproc, layout, tables all `true`)
- DPI set to 300

### ❌ OCR Extraction Failing
```json
{
  "ocr_result": {
    "supplier": "Unknown Supplier",
    "total": 0.0,
    "line_items_count": 0,
    "confidence": 0.0175  // Very low!
  },
  "raw_paddleocr_pages": [{
    "blocks": [{
      "ocr_text": "",  // EMPTY!
      "confidence": 0.025,
      "bbox": [0, 0, 0, 0]  // Invalid bbox
    }]
  }]
}
```

## Root Cause

**PaddleOCR is not detecting any text** from the PDF:
1. `ocr_text: ""` - No text extracted
2. `confidence: 0.025` - Extremely low (should be > 0.5)
3. `bbox: [0, 0, 0, 0]` - Invalid bounding box (means no layout detected)
4. Only 1 block with type "Text" - Layout detection returned single full-page block

## Why This Happens

### Issue 1: Layout Detection Disabled
Despite `FEATURE_OCR_V2_LAYOUT = True`, the detection is returning a single full-page block:
```python
# From owlin_scan_pipeline.py:316-319
if not FEATURE_OCR_V2_LAYOUT:
    return [{
        "type": "Text",
        "bbox": [0, 0, 0, 0],  # This is what we're seeing!
    }]
```

**But the flag IS enabled**, so something else is wrong...

### Issue 2: Layout Detection Module Missing
The code tries to import:
```python
from ocr.layout_detector import detect_document_layout
```

This module might not exist or is failing silently.

### Issue 3: PaddleOCR Not Finding Text
Even with a full-page block, PaddleOCR should extract text. Empty result means:
- Image preprocessing failed (image is blank/corrupted)
- PaddleOCR model not loaded correctly
- PDF rasterization failed

## Diagnostic Evidence

**Test PDF**: `112be37d-afe1-4fe6-8eed-723ccbd70b58__Storiinvoiceonly1.pdf`

**Preprocessed image path**:
```
data\uploads\112be37d-afe1-4fe6-8eed-723ccbd70b58__storiinvoiceonly1\pages\page_001.pre.png
```

**This image exists and should contain the rasterized PDF page.**

## Next Steps to Debug

### 1. Check if preprocessed image exists and is valid
```powershell
$imgPath = "data\uploads\112be37d-afe1-4fe6-8eed-723ccbd70b58__storiinvoiceonly1\pages\page_001.pre.png"
Test-Path $imgPath
Get-Item $imgPath | Select-Object Length, LastWriteTime
```

### 2. Check layout_detector module
```powershell
python -c "from ocr.layout_detector import detect_document_layout; print('✅ Module exists')"
```

### 3. Test PaddleOCR directly on the preprocessed image
```python
from paddleocr import PaddleOCR
import cv2

ocr = PaddleOCR(lang='en')
img_path = "data/uploads/112be37d-afe1-4fe6-8eed-723ccbd70b58__storiinvoiceonly1/pages/page_001.pre.png"
result = ocr.predict(img_path)
print(f"Detected {len(result)} text regions")
```

### 4. Check backend logs for errors
Look for:
- `[PAGE_PROC]` - Should show page rasterization
- `[TABLE_DETECT]` - Should show table detection attempts
- Any import errors or exceptions
- PaddleOCR warnings

## Likely Fixes

### Fix 1: Layout Detector Missing
If `ocr.layout_detector` doesn't exist, the code falls back to single full-page block. Need to:
1. Check if `backend/ocr/layout_detector.py` exists
2. If not, layout detection is not working despite flag being enabled

### Fix 2: Preprocessing Corruption
If image exists but is blank/corrupted:
1. Check preprocessing pipeline (deskew, binarization)
2. May need to disable advanced preprocessing temporarily
3. Test with `FEATURE_OCR_V2_PREPROC = False`

### Fix 3: PaddleOCR Model Issue
If PaddleOCR can't load or process:
1. Check PaddleOCR installation
2. Test with simple image first
3. Check model files are downloaded

## Immediate Action

Run these commands to diagnose:

```powershell
# 1. Check preprocessed image
$img = "data\uploads\112be37d-afe1-4fe6-8eed-723ccbd70b58__storiinvoiceonly1\pages\page_001.pre.png"
if (Test-Path $img) {
    Write-Host "✅ Image exists: $($(Get-Item $img).Length) bytes"
} else {
    Write-Host "❌ Image missing!"
}

# 2. Check layout detector
python -c "try:
    from ocr.layout_detector import detect_document_layout
    print('✅ layout_detector exists')
except ImportError as e:
    print(f'❌ layout_detector missing: {e}')
"

# 3. List all files in the processed directory
Get-ChildItem "data\uploads\112be37d-afe1-4fe6-8eed-723ccbd70b58__storiinvoiceonly1" -Recurse | Select-Object FullName, Length
```

---

**Status**: Endpoint fixed, OCR extraction broken  
**Next**: Check preprocessed images and layout_detector module

