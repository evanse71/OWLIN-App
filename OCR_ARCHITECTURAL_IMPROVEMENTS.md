# OCR Backend Architectural Improvements

## Executive Summary

This document describes the architectural improvements made to the OCR backend based on expert analysis. The changes transform the system from a fragile "regex-guessing" approach to a robust "spatial reasoning" architecture.

---

## Problem Analysis

### The Core Issue: Loss of Spatial Information

The original implementation had a critical weakness in `table_extractor.py`:

**Before**: The `_fallback_line_grouping()` method received only a flat string (`ocr_text`), throwing away all X/Y coordinate information from PaddleOCR.

**Consequence**: The system tried to distinguish "Quantity" from "Unit Price" based purely on regex patterns (e.g., "does it have a decimal?"), which fails for edge cases like:
- Quantity: 10.5 (hours worked)
- Price: 10 (flat fee)
- Product names containing "Unit" (e.g., "Storage Unit")

### Why "Stori" Worked (But Was Fragile)

The Stori invoice likely worked due to:
1. Clean preprocessing in Python 3.11 feeding better text to PaddleOCR
2. Fortuitous alignment with the hard-coded exclusion list

**Fragility**: The exclusion list contained generic words like 'unit', 'rate', 'description' that could appear in legitimate product names, causing false positives.

---

## Improvements Implemented

### 1. ✅ Relaxed Price Regex Patterns (Quick Win)

**File**: `backend/ocr/table_extractor.py`

**Problem**: The regex required exactly 2 decimal places (`\d{2}`), failing for:
- UK B2B invoices with 3-4 decimal unit prices (fuel, bulk beverages)
- Round totals with 0 decimals

**Solution**: Updated patterns to handle 0-4 decimal places:

```python
self._price_patterns = [
    r'[£$€]\s?[\d,]+\.(\d{2}|\d{3}|\d{4})\b',  # Currency + 2-4 decimals: £123.4567
    r'[£$€]\s?[\d,]+\b',                        # Currency + integer: £123
    r'[\d,]+\.\d{2,4}\b',                       # 123.45 or 123.456 or 123.4567
    r'[\d,]+\.?\d*',                            # Fallback: 123.45 or 123
]
```

### 2. ✅ Safe Exclusion Keywords (Quick Win)

**File**: `backend/ocr/table_extractor.py`

**Problem**: Generic words like 'unit', 'rate', 'description' were hard-excluded, causing false positives for products like "Storage Unit" or "Rate Card".

**Solution**: 
- Removed generic single words from exclusion list
- Kept only exact phrases that would NEVER appear in product names
- Added smart matching: exact match or word boundary for short keywords

```python
exclusion_keywords = [
    # Exact phrases only
    'invoice no', 'invoice number', 'vat registration no',
    'subtotal', 'sub-total', 'grand total',
    'balance due', 'amount due',
    # Company suffixes
    'ltd.', 'limited.', 'plc.', 'inc.',
]
```

### 3. ✅ Pass Grayscale to PaddleOCR (Medium Win)

**File**: `backend/image_preprocess.py`

**Problem**: The preprocessing pipeline applied binary thresholding (`cv2.adaptiveThreshold`) and passed the result to PaddleOCR. This creates jagged edges that lower PaddleOCR's confidence.

**Why This Matters**: PaddleOCR is a deep learning model trained on grayscale/color images with anti-aliasing. Binary images hurt its performance.

**Solution**:
- `preprocess_bgr_page()` now returns enhanced grayscale (CLAHE applied) instead of binary
- Added `get_binary_for_structure_detection()` helper for OpenCV operations that need binary
- Table extractor applies binary threshold ONLY for structure detection (lines/contours), not for OCR

```python
def preprocess_bgr_page(img_bgr: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Returns enhanced grayscale (NOT binary) for better PaddleOCR performance.
    Binary thresholding is done separately only when needed for OpenCV operations.
    """
    # ... deskew, denoise, CLAHE ...
    return enhanced, meta  # Returns grayscale, not binary
```

### 4. ✅ Spatial Column Clustering (Architectural Win)

**Files**: 
- `backend/ocr/table_extractor.py` (new methods)
- `backend/ocr/ocr_processor.py` (word-level extraction)
- `backend/ocr/owlin_scan_pipeline.py` (wiring)

**The Game Changer**: Instead of parsing flat text, we now use X/Y coordinates to identify columns.

#### How It Works

1. **Extract Word Positions**: PaddleOCR returns bounding boxes for each word. We extract:
   - Text content
   - X-center coordinate
   - Y-center coordinate

2. **Cluster Columns by X-Position**: 
   - Collect X-centers of all numeric words (likely qty/price/total)
   - Use histogram peak detection to find column boundaries
   - Identify gaps > 50 pixels as column separators

3. **Assign Column Roles**:
   ```
   [Description (wide)] | [Qty (narrow)] | [Unit Price (narrow)] | [Total (narrow)]
   ```

4. **Group Words into Rows by Y-Position**:
   - Words within 15 pixels vertically are in the same row
   - Sort rows top-to-bottom

5. **Parse Line Items**:
   - For each row, group words by column
   - Extract description from left column
   - Extract numeric values from appropriate columns
   - No more regex guessing - we KNOW which column a number came from!

#### Key Methods Added

```python
def _cluster_columns_by_x_position(self, words_with_positions):
    """Histogram-based column detection"""
    
def _assign_word_to_column(self, x_center, column_ranges):
    """Assign word to column based on X-coordinate"""
    
def _fallback_line_grouping_spatial(self, image, ocr_blocks):
    """Spatial-aware parsing using word positions"""
```

#### Priority System

The table extractor now has a 3-tier priority system:

1. **PRIORITY 1**: Spatial clustering (if OCR blocks with positions available)
2. **PRIORITY 2**: Text-based parsing (if only OCR text available)
3. **PRIORITY 3**: Structure-aware (if grid lines detected)

```python
# In extract_table()
if ocr_blocks and len(ocr_blocks) > 5:
    # Use spatial clustering - THE ARCHITECTURAL WIN
    line_items = self._fallback_line_grouping_spatial(table_img, ocr_blocks)
    method_used = "spatial_clustering"
elif ocr_text and len(ocr_text.strip()) > 50:
    # Fallback to text-based
    line_items = self._fallback_line_grouping(table_img, ocr_text)
    method_used = "text_based_parsing"
else:
    # Last resort: structure detection
    ...
```

---

## Technical Implementation Details

### PaddleOCR Word-Level Extraction

**File**: `backend/ocr/ocr_processor.py`

Added `_ocr_with_paddle_detailed()` method that extracts word blocks:

```python
def _ocr_with_paddle_detailed(self, image, block_type):
    """
    Returns: (text, confidence, processing_time, word_blocks)
    where word_blocks is List[Dict] with 'text', 'bbox', 'confidence'
    """
    # PaddleOCR returns: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    # Convert to: [x, y, w, h]
    word_blocks.append({
        'text': text,
        'bbox': [x_min, y_min, x_max - x_min, y_max - y_min],
        'confidence': conf
    })
```

### OCRResult Enhancement

Added `word_blocks` field to `OCRResult` dataclass:

```python
@dataclass
class OCRResult:
    # ... existing fields ...
    word_blocks: List[Dict[str, Any]] = None  # Spatial info for table extraction
```

### Pipeline Integration

**File**: `backend/ocr/owlin_scan_pipeline.py`

The pipeline now passes word blocks to table extraction:

```python
# Extract word_blocks from OCR result
ocr_blocks = getattr(ocr_result, 'word_blocks', None)

# Pass to table extractor
table_result = extract_table_from_block(image, block_info, ocr_result.ocr_text, ocr_blocks)
```

---

## Benefits

### 1. Robustness
- No longer guessing based on regex patterns
- Handles edge cases: decimal quantities, integer prices, ambiguous product names

### 2. Accuracy
- Uses spatial layout to identify columns
- Eliminates false positives from keyword matching

### 3. Flexibility
- Works with "clean" invoices (no grid lines) using whitespace
- Graceful fallback to text-based parsing if spatial info unavailable

### 4. Maintainability
- Clear separation of concerns: spatial clustering vs. text parsing
- Easy to tune column detection parameters (gap threshold, y-tolerance)

---

## Testing Recommendations

### Test Cases to Validate

1. **Decimal Quantities**: Invoice with "10.5 hours" as quantity
2. **Integer Prices**: Invoice with "£10" (no decimals) as unit price
3. **Product Names with Keywords**: "Storage Unit", "Rate Card", "Unit Display"
4. **Clean Invoices**: Modern invoices without grid lines (like Stori)
5. **Multi-Decimal Prices**: UK B2B invoices with 3-4 decimal places
6. **Mixed Layouts**: Invoices with both bordered and borderless tables

### How to Test

```bash
# Run the backend with test invoices
python -m pytest tests/test_table_extraction.py -v

# Or test manually via API
curl -X POST http://localhost:8000/api/ocr/process \
  -F "file=@test_invoice.pdf"
```

---

## Performance Considerations

### Computational Cost

- **Spatial clustering**: O(n log n) for sorting + O(n) for clustering
- **Text-based parsing**: O(n²) for multi-line grouping
- **Spatial is FASTER** than text-based for large tables

### Memory

- Word blocks add ~100 bytes per word
- Typical invoice: 200-500 words = 20-50 KB additional memory
- Negligible impact

---

## Future Enhancements

### 1. K-Means Clustering (Optional)
Replace histogram-based clustering with K-Means for more robust column detection:

```python
from sklearn.cluster import KMeans

def _cluster_columns_kmeans(self, x_coords, n_columns=4):
    kmeans = KMeans(n_clusters=n_columns)
    kmeans.fit(np.array(x_coords).reshape(-1, 1))
    return kmeans.cluster_centers_
```

### 2. Machine Learning Column Classifier
Train a small ML model to classify columns based on:
- X-position
- Text content patterns
- Column width
- Neighboring columns

### 3. Multi-Page Table Handling
Detect tables that span multiple pages and merge line items

---

## Migration Notes

### Backward Compatibility

✅ **Fully backward compatible**
- Old text-based parsing still available as fallback
- Existing API contracts unchanged
- No breaking changes to database schema

### Rollout Strategy

1. **Phase 1**: Deploy with spatial clustering enabled (default)
2. **Phase 2**: Monitor logs for `method_used` field:
   - `spatial_clustering` = new method working
   - `text_based_parsing` = fallback triggered
   - `structure_aware` = grid-based detection
3. **Phase 3**: Tune parameters based on real-world performance

---

## Conclusion

These improvements transform the OCR backend from a **heuristic-based system** to a **layout-aware system**. By preserving and using spatial information, we eliminate the fundamental weakness of "guessing based on text patterns."

The system now reasons about document layout the way a human would: "This number is in the Quantity column because it's positioned between the Description and Unit Price columns."

This is the foundation for handling the long tail of invoice formats without requiring an LLM.

---

## Files Modified

1. `backend/ocr/table_extractor.py` - Core improvements
2. `backend/ocr/ocr_processor.py` - Word-level extraction
3. `backend/image_preprocess.py` - Grayscale for PaddleOCR
4. `backend/ocr/owlin_scan_pipeline.py` - Pipeline integration

## Lines of Code

- Added: ~300 lines (spatial clustering logic)
- Modified: ~150 lines (preprocessing, OCR extraction)
- Removed: ~20 lines (overly restrictive exclusions)

**Net Impact**: More robust, more maintainable, better performance.

