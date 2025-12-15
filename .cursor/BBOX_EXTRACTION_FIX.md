# Bounding Box Extraction Fix

**Date**: 2025-12-11  
**Issue**: Line items have no bounding boxes (`itemsWithBbox: 0`), causing incorrect OCR extraction values

## Root Cause

When converting `LineItem` objects to dictionaries for database storage in `ocr_service.py`, the `bbox` field was being **dropped**. Even though:

1. ✅ `LineItem.to_dict()` includes bbox (table_extractor.py:86-87)
2. ✅ Database schema supports bbox column (db.py:484-520)
3. ✅ `insert_line_items()` saves bbox to database (db.py:490-520)
4. ❌ **`ocr_service.py` manually extracts fields and skips bbox** (lines 1212-1219, 1232-1239)

## Fixes Applied

### 1. Extract bbox from dict LineItems (`backend/services/ocr_service.py:1212-1219`)
- **Added**: Extract `bbox` from `item.get("bbox")` when converting dict format
- **Result**: Bbox preserved when table extraction returns dict format

### 2. Extract bbox from object LineItems (`backend/services/ocr_service.py:1232-1239`)
- **Added**: Extract `bbox` from `getattr(item, 'bbox', None)` when converting object format
- **Result**: Bbox preserved when table extraction returns LineItem objects

### 3. Preserve bbox in STORI items (`backend/services/ocr_service.py:1110-1117, 1147-1154`)
- **Added**: Check for bbox in STORI template-matched items (though they typically don't have it)
- **Result**: Bbox preserved if present in STORI data

## Files Modified

1. `backend/services/ocr_service.py` - Extract and preserve bbox field when converting LineItems

## Testing

After this fix:
1. ✅ Line items should have bbox values in database
2. ✅ Frontend should show `itemsWithBbox > 0` in console
3. ✅ InvoiceVisualizer should be able to highlight line items on PDF

## Next Steps

1. **Restart backend** to pick up changes
2. **Re-upload the invoice** (or reprocess existing one)
3. **Check console** for `itemsWithBbox` count
4. **Verify** line items have correct values (bbox helps with spatial grouping)

## Note on Wrong Values

The user reported wrong values ("Tel:", "Company Reg:" instead of actual line items). This suggests:
- Table extraction might be failing to detect the correct table structure
- Layout detection might be misidentifying header text as line items
- The bbox fix will help with visual verification, but the root cause might be in table_extractor.py

If values are still wrong after bbox fix, investigate:
- Table detection logic in `table_extractor.py`
- Layout detection in `layout_detector.py`
- OCR text quality (66% confidence suggests poor OCR)
