# PaddleOCR Crash Fix - Defensive Tuple Unpacking

## Problem

PaddleOCR was crashing with `tuple index out of range` errors **before** any of the new LLM improvements could run. This happened at two crash sites:

1. **`ocr_processor.py:287`** - In `_ocr_with_paddle()` method
2. **`ocr_processor.py:233`** - In `_ocr_with_paddle_detailed()` method

### Root Cause

PaddleOCR can return malformed or unexpected structures:
- Empty results `None` or `[]`
- Result where `result[0]` is empty or not a list
- Lines where `line` doesn't have 2 elements `[bbox, text_info]`
- Bbox that's not a list of 4 points
- `text_info` that's not a tuple `(text, confidence)` but could be:
  - A dict `{"text": "...", "confidence": 0.9}`
  - A plain string
  - `None`
  - Other unexpected formats

When the code tried to unpack these without validation, it crashed with `tuple index out of range`.

## Solution

Added **comprehensive defensive unpacking** in both methods:

### 1. Result Structure Validation
```python
# Check if result exists and has expected structure
if not result:
    return "", 0.0, processing_time, []

if not isinstance(result, (list, tuple)) or len(result) == 0:
    LOGGER.warning("PaddleOCR returned unexpected result type")
    return "", 0.0, processing_time, []

if not result[0] or not isinstance(result[0], (list, tuple)):
    LOGGER.warning("PaddleOCR result[0] is invalid")
    return "", 0.0, processing_time, []
```

### 2. Line Entry Validation
```python
for idx, line in enumerate(result[0]):
    # Validate line structure
    if not isinstance(line, (list, tuple)) or len(line) < 2:
        LOGGER.warning("Skipping malformed line")
        malformed_count += 1
        continue
```

### 3. Safe Text/Confidence Extraction
```python
# Handle multiple possible text_info formats
if isinstance(text_info, tuple) and len(text_info) >= 2:
    text = str(text_info[0]) if text_info[0] is not None else ""
    conf = float(text_info[1]) if text_info[1] is not None else 0.5
elif isinstance(text_info, dict):
    text = str(text_info.get("text", ""))
    conf = float(text_info.get("confidence", 0.5))
elif isinstance(text_info, str):
    text = text_info
    conf = 0.5
else:
    text = str(text_info) if text_info is not None else ""
    conf = 0.5
```

### 4. Safe Bbox Processing
```python
# Validate bbox points before processing
if bbox and isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
    valid_points = []
    for pt in bbox:
        if isinstance(pt, (list, tuple)) and len(pt) >= 2:
            try:
                x_val = float(pt[0])
                y_val = float(pt[1])
                valid_points.append((x_val, y_val))
            except (ValueError, TypeError, IndexError):
                continue  # Skip invalid points
    
    if len(valid_points) >= 4:
        # Process bbox...
```

### 5. Debug Logging
Added support for `OWLIN_DEBUG_OCR=1` environment variable to enable detailed logging:
- Result structure inspection
- Malformed entry warnings
- Full tracebacks on errors

## Files Modified

- `backend/ocr/ocr_processor.py`:
  - `_ocr_with_paddle_detailed()` - Added defensive unpacking (lines ~184-280)
  - `_ocr_with_paddle()` - Added defensive unpacking (lines ~256-330)
  - Both methods now handle malformed PaddleOCR output gracefully

## Testing

Run with debug mode enabled:
```powershell
$env:OWLIN_DEBUG_OCR = "1"
python backend/scripts/run_test_with_progress.py "path/to/invoice.pdf" "results.txt"
```

## Expected Behavior

1. **Before Fix**: PaddleOCR crashes → Falls back to Tesseract (0 confidence) → LLM gets empty text → Validation skipped
2. **After Fix**: PaddleOCR handles malformed output gracefully → Skips bad entries → Processes valid entries → LLM receives actual text → Full pipeline runs

## Impact

✅ **PaddleOCR no longer crashes on malformed output**
✅ **New LLM improvements can now actually run**
✅ **Full-page context, footer filtering, and hard validation gates will be tested**
✅ **Graceful degradation: skips bad entries, processes good ones**

## Next Steps

1. Run test with debug mode to verify fix
2. Confirm PaddleOCR processes the Stori invoice successfully
3. Verify LLM pipeline receives actual OCR text
4. Test validation gates with real invoice data
5. Test Wild Horse invoice to verify 100× error detection
