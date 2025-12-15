---
name: Improve price extraction and balancing
overview: Improve line-item price extraction in the fallback extractor to handle currency symbols, thousands separators, and add price backfill logic (qty × unit_price = total_price). Update batch tester to show parity breakdown summary.
todos: []
---

# Improve Price Extraction & Balancing

## Overview

Enhance price extraction in the fallback line extractor to better capture unit_price and total_price from OCR text, and add backfill logic to compute missing totals. Use Red Dragon invoice as regression test case.

## Implementation Steps

### STEP 1: Improve Price Regex Patterns

**File**: `backend/ocr/table_extractor.py`

**Location**: `fallback_extract_from_lines()` method, around line 1975-2004

**Changes**:

1. Replace current simple pattern `r'(\d+[\.,]\d{2})'` with more robust patterns that:

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Handle currency symbols: `£`, `$`, `€` (optional prefix)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Handle thousands separators: `1,234.50`, `1234.50`
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Enforce exactly 2 decimal places to avoid picking up random numbers
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Focus on prices at the END of the line (not in description)

2. Create new price extraction function:
   ```python
   def _extract_prices_from_line_end(self, line: str) -> Tuple[Optional[float], Optional[float]]:
       """
       Extract unit_price and total_price from the end of a line.
       
       Patterns to match:
       - "69.31 69.31" → (69.31, 69.31)
       - "£1,234.50" → (None, 1234.50)
       - "50.00 200.00" → (50.00, 200.00)
       
       Returns:
           Tuple of (unit_price, total_price) where either may be None
       """
   ```

3. Pattern strategy:

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Look for 1-2 price-like numbers at the end (last 30-40 characters of line)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Pattern: `r'[£$€]?\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?)'` (with word boundary)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Normalize: remove currency symbols, replace commas with nothing, ensure 2 decimals
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Validate: prices should be > 0 and < 10000 (reasonable for line items)

4. Keep existing logic:

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - If 2 prices found → (unit_price, total_price)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - If 1 price found → (None, total_price)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - If 0 prices found → (None, None)

**Test**: Red Dragon "ORANGE JUICE" line should still extract `unit_price: "69.31"`, `total_price: "69.31"`

---

### STEP 2: Add Price Backfill Logic

**File**: `backend/ocr/table_extractor.py`

**Location**: After price extraction in `fallback_extract_from_lines()`, around line 2020-2040

**Changes**:

1. Add backfill pass after creating LineItem but before appending to list:
   ```python
   # Price backfill: compute total_price from qty × unit_price if missing
   if line_item.quantity and line_item.unit_price and not line_item.total_price:
       try:
           qty_val = float(line_item.quantity)
           unit_val = float(line_item.unit_price.replace('£', '').replace(',', '').strip())
           if qty_val > 0 and unit_val > 0 and qty_val <= 100 and unit_val < 10000:
               computed_total = qty_val * unit_val
               line_item.total_price = f"{computed_total:.2f}"
               # Mark in cell_data for debugging
               if not line_item.cell_data:
                   line_item.cell_data = {}
               line_item.cell_data["price_backfill"] = "computed_total_from_qty_unit"
               LOGGER.debug(f"[LINE_FALLBACK] Backfilled total_price: {qty_val} × {unit_val} = {computed_total:.2f}")
       except (ValueError, TypeError):
           pass  # Skip if values can't be parsed
   ```

2. Safety checks:

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Only backfill if both qty and unit_price are present and valid
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Skip if computed total would be > 100000 (likely error)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Skip if qty or unit_price are 0 or negative

3. Update confidence calculation:

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Backfilled prices should have slightly lower confidence than extracted prices
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Consider confidence adjustment: `confidence *= 0.95` for backfilled items

**Test**: Lines with `qty=4, unit_price=50.00, total_price=""` should become `total_price="200.00"`

---

### STEP 3: Verify Parity Computation Updates

**Files**:

- `backend/main.py` (dev endpoint, around line 2902-2942)
- `backend/ocr/owlin_scan_pipeline.py` (main pipeline, around line 1391-1449)

**Verification**:

1. Ensure `sum_line_total` computation includes backfilled prices
2. Check that parity metrics update correctly when more prices are found
3. Verify `parity_rating` and `flags` reflect improved extraction

**No code changes needed** - existing parity logic should automatically pick up improved prices

---

### STEP 4: Update Batch Tester Parity Summary

**File**: `backend/scripts/batch_test_ocr.py`

**Location**: `print_summary()` function, around line 93-120

**Changes**:

1. Enhance parity breakdown display:

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Already counts parity ratings (lines 111-120)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Add more prominent display at top of summary
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Format: Clear table showing counts per rating

2. Update summary output:
   ```python
   # At top of summary, after total counts:
   print(f"\nParity Quality Breakdown:")
   print(f"  Excellent (<1% mismatch): {parity_counts['excellent']}")
   print(f"  Good (<3% mismatch):      {parity_counts['good']}")
   print(f"  Ok (<8% mismatch):        {parity_counts['ok']}")
   print(f"  Poor (>=8% mismatch):     {parity_counts['poor']}")
   print(f"  Unknown:                  {parity_counts['unknown']}")
   ```

3. Handle missing parity gracefully:

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - If `parity_rating` is missing from response, default to "unknown"
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Don't crash if `total_mismatch_pct` is None

**Test**: Running `python backend/scripts/batch_test_ocr.py --all` should show clear parity breakdown

---

## Testing Strategy

### Regression Tests

1. **Red Dragon Invoice** (existing working case):

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Orange Juice line should still extract prices correctly
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Pepsi lines should now extract prices if present in OCR
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Parity should improve if more prices are found

2. **Wild Horse Invoices**:

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Should still extract supplier/customer correctly
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Line items should still filter out footer text
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Prices should extract if present

3. **Batch Test**:

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Run `python backend/scripts/batch_test_ocr.py --all`
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Verify no regressions (items count, confidence should be similar or better)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Check parity breakdown shows reasonable distribution

### Acceptance Criteria

- Red Dragon Orange Juice line: Still extracts `unit_price: "69.31"`, `total_price: "69.31"`
- Price backfill: Lines with qty + unit_price but no total_price get computed total
- Parity improvement: More invoices move from "poor" to "ok"/"good" if prices are backfilled
- No regressions: Existing "excellent" parity invoices remain excellent
- Batch tester: Shows clear parity breakdown summary

---

## Files to Modify

1. `backend/ocr/table_extractor.py`

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Improve `_extract_prices_from_line_end()` or inline price extraction (line ~1975)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Add price backfill logic (after line ~2020)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Update confidence calculation for backfilled prices

2. `backend/scripts/batch_test_ocr.py`

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                - Enhance `print_summary()` to show parity breakdown prominently (line ~93)

---

## Implementation Notes

- Keep all existing filters (quantity sanity, header/meta skip, product keyword bias)
- Price extraction should be conservative (prefer false negatives over false positives)
- Backfill should only happen when we're confident in qty and unit_price values
- Maintain backward compatibility with existing response format