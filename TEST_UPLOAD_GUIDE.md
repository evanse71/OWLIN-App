# Owlin Upload Testing Guide

## System Status: ✅ READY FOR TESTING

**Frontend**: http://localhost:5176/invoices?dev=1  
**Backend**: http://localhost:8000 (test_backend_simple.py)  
**Backend Status**: ✅ Healthy  
**OCR Engines**: All installed and available  

---

## Quick Test Upload

### Option 1: UI Upload (Recommended)
1. Go to: http://localhost:5176/invoices?dev=1
2. Click the file upload area (or drag and drop)
3. Select any:
   - PDF invoice
   - JPG/PNG image of invoice
   - HEIC photo from iPhone
   - Delivery note (any format)
4. Watch for card to appear with:
   - Supplier name
   - Invoice date
   - Total value
   - Line items
   - Confidence score

### Option 2: API Upload (PowerShell)

```powershell
# Upload a PDF
$filePath = "C:\path\to\your\invoice.pdf"
$uri = "http://localhost:8000/api/upload"

# Read file
$fileBytes = [System.IO.File]::ReadAllBytes($filePath)
$fileName = [System.IO.Path]::GetFileName($filePath)

# Create multipart form data
$boundary = [System.Guid]::NewGuid().ToString()
$LF = "`r`n"

$bodyLines = (
    "--$boundary",
    "Content-Disposition: form-data; name=`"file`"; filename=`"$fileName`"",
    "Content-Type: application/pdf$LF",
    [System.Text.Encoding]::GetEncoding("iso-8859-1").GetString($fileBytes),
    "--$boundary--$LF"
) -join $LF

$headers = @{
    "Content-Type" = "multipart/form-data; boundary=$boundary"
}

# Upload
$response = Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -Body $bodyLines
$response | ConvertTo-Json
```

### Option 3: Simple curl (if available)

```powershell
curl -X POST http://localhost:8000/api/upload -F "file=@invoice.pdf"
```

---

## Expected Results

### Successful Upload Response
```json
{
  "doc_id": "abc-123-...",
  "filename": "invoice.pdf",
  "status": "processing",
  "format": ".pdf",
  "size_bytes": 45678,
  "hash": "a1b2c3d4"
}
```

### Duplicate Upload Response
```json
{
  "doc_id": "abc-123-...",
  "filename": "invoice.pdf",
  "status": "duplicate",
  "message": "File already uploaded",
  "existing_doc_id": "abc-123-...",
  "format": ".pdf"
}
```

### File Too Large (>25MB)
```json
{
  "detail": "File too large (27.5MB). Maximum size: 25MB"
}
```

### Unsupported Format
```json
{
  "detail": "Unsupported file format. Allowed: PDF, JPG, PNG, HEIC"
}
```

---

## Testing Checklist

### File Format Tests
- [ ] Upload PDF invoice → Card appears
- [ ] Upload JPG receipt → Card appears
- [ ] Upload PNG screenshot → Card appears
- [ ] Upload HEIC iPhone photo → Converts to PNG, card appears
- [ ] Upload .txt file → Returns 400 error
- [ ] Upload .doc file → Returns 400 error

### Validation Tests
- [ ] Upload 30MB file → Returns 413 error (too large)
- [ ] Upload same file twice → Second returns "duplicate" status
- [ ] Upload different files → Each gets unique doc_id

### OCR Accuracy Tests
- [ ] Simple invoice → Extracts supplier, date, total
- [ ] Table invoice → Extracts line items
- [ ] Thermal receipt → Processes with Tesseract
- [ ] Multi-page PDF → Processes first page
- [ ] Delivery note → Classifies as delivery_note

### UI Tests
- [ ] Backend status shows green checkmark
- [ ] Upload area accepts drag-and-drop
- [ ] Upload shows "processing" status
- [ ] Card appears after OCR completes
- [ ] Card shows extracted data
- [ ] Line items visible in card

---

## Troubleshooting

### Backend shows "Unreachable"
- Check backend is running: `Test-NetConnection localhost -Port 8000`
- Verify health endpoint: `Invoke-RestMethod http://localhost:8000/api/health`
- Check CORS settings in `source_extracted/test_backend_simple.py`

### OCR not working
- Run: `python check_ocr_engines.py`
- Verify all engines show `[OK]`
- Check backend started with PYTHONPATH: `$env:PYTHONPATH = "."`

### Upload fails
- Check file size < 25MB
- Verify format is PDF, JPG, PNG, or HEIC
- Test health endpoint first
- Check backend logs in `backend_stdout.log`

---

## Next Phase: Advanced Features

To fully match the Owlin System Bible spec, implement:

1. **Supplier Normalization** (Section 2.5)
   - rapidfuzz matching
   - Embedding fallback

2. **Match Engine** (Section 2.6)
   - Invoice ↔ Delivery Note pairing
   - Date window ± 3 days
   - Line-item matching

3. **Issue Detector** (Section 2.6)
   - Price mismatches
   - Quantity discrepancies
   - Missing items

4. **Forecast Engine** (Section 2.7)
   - OLS regression
   - Price trend prediction
   - 95% confidence bands

5. **Owlin Agent** (Section 6)
   - Credit suggestions
   - Issue recommendations
   - Local LLM integration

---

## Current Limitations

- **OCR Engine Selection**: Currently uses PaddleOCR by default, Tesseract fallback works
- **docTR**: Not implemented (mentioned in spec)
- **Calamari**: Not implemented (mentioned in spec)
- **Multi-page**: Processes first page only
- **DuckDB**: Not implemented (mentioned in spec for analytics)

---

## Success Criteria Met

✅ Backend running and healthy  
✅ Frontend connected  
✅ Upload endpoint ready  
✅ File validation working  
✅ SHA-256 deduplication ready  
✅ HEIC conversion ready  
✅ OCR engines installed  
✅ Database schema updated  
✅ Document classification ready  
✅ Invoice/delivery note cards ready  

**System is ready for real-world invoice testing!**

