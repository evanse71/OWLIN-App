# Diagnostic Steps for Table Extraction Pipeline

This document outlines the diagnostic steps to identify why data isn't showing on cards after upload.

## Changes Implemented

### 1. Enhanced Logging in `backend/ocr/owlin_scan_pipeline.py`

**Layout Detection Logging (Step 2):**
- Added logging before processing blocks to show total count
- Added per-block logging showing type, bbox, and OCR text length

**Table Extraction Logging (Step 1):**
- Enhanced logging when table extraction is triggered
- Logs result count, method used, and confidence
- Logs table_data structure and line_items count
- Logs first item sample for verification
- Logs when extraction is skipped and why

### 2. Diagnostic Scripts Created

**`test_table_pipeline.py`** - Tests the full pipeline:
- Layout detection verification
- Table extraction verification
- Shows extracted line items

**`check_database_line_items.py`** - Database verification:
- Checks latest invoice and line items
- Can check specific doc_id
- Shows detailed line item information

## Diagnostic Workflow

### Step 1: Upload a Test Document

Upload a document through the UI and note the `doc_id` from the response or logs.

### Step 2: Check Backend Logs

Look for these log prefixes in your backend logs:

```
[LAYOUT] Processing X blocks from layout detection
[LAYOUT] Block 0: type='table', bbox=(...), ocr_text_len=...
[TABLE_EXTRACT] Triggering extraction for table block, bbox=(...)
[TABLE_EXTRACT] Result: X items, method=..., conf=...
[TABLE_EXTRACT] table_data keys: [...], line_items count: X
[TABLE_EXTRACT] First item sample: {...}
```

**What to look for:**
- Are any blocks detected as type='table'?
- Is table extraction being triggered?
- How many line items are extracted?
- Are there any errors in the extraction?

### Step 3: Run Database Check

```bash
python check_database_line_items.py
```

Or for a specific document:
```bash
python check_database_line_items.py <doc_id>
```

**What to check:**
- Is the invoice stored?
- Is `line_item_count` > 0?
- Are the line items properly formatted?

### Step 4: Test Pipeline Directly

```bash
python test_table_pipeline.py data/uploads/your_test_file.pdf
```

This will show:
- Layout detection results
- Table extraction results
- Extracted line items

### Step 5: Check API Response

```bash
curl "http://localhost:8000/api/upload/status?doc_id=YOUR_DOC_ID" | jq
```

Or use the Python script:
```python
import requests
import json

doc_id = "YOUR_DOC_ID"
response = requests.get(f"http://localhost:8000/api/upload/status?doc_id={doc_id}")
data = response.json()
print(json.dumps(data, indent=2))
```

**What to check:**
- Does the response include `parsed` data?
- Does it include `items` array?
- Are the items properly formatted?

### Step 6: Check OCR Output File

The OCR output is stored in `data/uploads/<doc_id>/ocr_output.json`. You can inspect it:

```python
import json
from pathlib import Path

doc_id = "YOUR_DOC_ID"
ocr_file = Path(f"data/uploads/{doc_id}/ocr_output.json")

if ocr_file.exists():
    with open(ocr_file) as f:
        data = json.load(f)
    
    if data.get("pages"):
        page = data["pages"][0]
        blocks = page.get("blocks", [])
        print(f"Total blocks: {len(blocks)}")
        
        for i, block in enumerate(blocks):
            if block.get("type") == "table":
                td = block.get("table_data")
                if td and isinstance(td, dict):
                    print(f"Block {i} (table): {len(td.get('line_items', []))} line items")
```

## Common Issues and Solutions

### Issue 1: No table blocks detected
**Symptoms:** `[LAYOUT]` logs show no blocks with `type='table'`
**Possible causes:**
- Layout detector not working
- Document doesn't have clear table structure
- LayoutParser model not loaded

**Check:**
- Are there any blocks detected at all?
- What types are the blocks?
- Check `backend/ocr/layout_detector.py` logs

### Issue 2: Table extraction returns 0 items
**Symptoms:** `[TABLE_EXTRACT]` shows `line_items count: 0`
**Possible causes:**
- Table structure detection failing
- OCR text not being parsed correctly
- Cell grouping logic failing

**Check:**
- What method was used? (`method_used` in logs)
- Was fallback used? (`fallback_used` in logs)
- Check `backend/ocr/table_extractor.py` logs

### Issue 3: Items extracted but not stored
**Symptoms:** Pipeline logs show items, but database has 0 line items
**Possible causes:**
- `insert_line_items()` not being called
- Field name mismatch
- Database transaction failure

**Check:**
- Look for `[STORE]` logs in `ocr_service.py`
- Verify field mapping in `backend/app/db.py:318-338`
- Check database for any errors

### Issue 4: Items stored but not showing on frontend
**Symptoms:** Database has items, but cards are empty
**Possible causes:**
- API not returning items
- Frontend not fetching correctly
- Data format mismatch

**Check:**
- Test API endpoint directly
- Check frontend network requests
- Verify API response format matches frontend expectations

## Next Steps After Diagnosis

Once you identify where the pipeline breaks:

1. **If layout detection fails:** Improve `layout_detector.py` or adjust detection thresholds
2. **If table extraction fails:** Improve `table_extractor.py` parsing logic
3. **If storage fails:** Fix field mapping or database schema
4. **If frontend fails:** Fix API response format or frontend data handling

## Files Modified

- `backend/ocr/owlin_scan_pipeline.py` - Enhanced logging
- `test_table_pipeline.py` - New diagnostic script
- `check_database_line_items.py` - New database check script
- `DIAGNOSTIC_STEPS.md` - This document

