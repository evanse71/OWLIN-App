# Price Extraction & Balancing - Testing Guide

## ✅ What Was Implemented

### 1. Enhanced Price Extraction (`_extract_prices_from_line_end()`)
- **Location**: `backend/ocr/table_extractor.py` (lines 1888-1944)
- **Features**:
  - Focuses on last 40 characters of each line (where prices typically appear)
  - Handles currency symbols: £, $, €
  - Handles thousands separators: `1,234.50` or `1234.50`
  - Enforces exactly 2 decimal places
  - Validates prices are between 0 and 10,000
  - Returns `(unit_price, total_price)` tuple

### 2. Price Backfill Logic
- **Location**: `backend/ocr/table_extractor.py` (lines 2093-2114)
- **Features**:
  - Computes `total_price = qty × unit_price` when `total_price` is missing
  - Safety checks: qty ≤ 100, unit_price < 10,000, computed total < 100,000
  - Marks backfilled prices in `cell_data["price_backfill"]`
  - Applies 5% confidence reduction (×0.95) for backfilled prices
  - Logs backfill operations for debugging

### 3. Enhanced Batch Tester Parity Summary
- **Location**: `backend/scripts/batch_test_ocr.py` (lines 93-120)
- **Features**:
  - Prominent parity breakdown display at top of summary
  - Counts: Excellent, Good, Ok, Poor, Unknown
  - Handles missing `parity_rating` gracefully
  - Clear formatting with mismatch percentage thresholds

---

## 🧪 Testing Instructions

### Prerequisites
1. **Backend must be running** on port 8000
   ```powershell
   # Check if backend is running
   netstat -an | findstr ":8000"
   
   # If not running, start it:
   python backend/main.py
   # OR
   .\start_backend_5176.ps1
   ```

2. **Test files available** in `data/uploads/`
   ```powershell
   python backend/scripts/batch_test_ocr.py --list
   ```

---

## Test A: Red Dragon Invoice (Single File)

### Command
```powershell
$invRedDragon = "2e1c65d2-ea57-4fc5-ab6c-5ed67d45dabc__26.08INV.jpeg"
Invoke-RestMethod -Uri "http://localhost:8000/api/dev/ocr-test?filename=$invRedDragon" | ConvertTo-Json -Depth 10
```

### What to Check

#### 1. Line Items - Price Extraction
Look at `line_items` array:
```json
{
  "line_items": [
    {
      "description": "ORANGE JUICE",
      "quantity": "1",
      "unit_price": "69.31",      // ✅ Should be populated
      "total_price": "69.31",     // ✅ Should be populated
      "confidence": 0.85
    }
  ]
}
```

**Expected improvements:**
- More `unit_price` fields populated (if prices exist in OCR text)
- More `total_price` fields populated
- If `unit_price` exists but `total_price` is empty → should be backfilled

#### 2. Backfill Indicators
Check for `cell_data` with backfill markers:
```json
{
  "cell_data": {
    "line_index": 5,
    "raw_line": "...",
    "method": "line_fallback",
    "price_backfill": "computed_total_from_qty_unit"  // ✅ Indicates backfill
  }
}
```

#### 3. Sum Line Total
```json
{
  "sum_line_total": 69.31  // ✅ Should increase if more prices extracted
}
```

**Before**: Might have been `69.31` (only Orange Juice)
**After**: Could be higher if other lines now have prices

#### 4. Parity Metrics
```json
{
  "total_mismatch_pct": 0.953,  // ✅ Should decrease if more prices found
  "parity_rating": "poor"       // ✅ May improve to "ok" or "good"
}
```

**Interpretation:**
- If still `"poor"` → That's OK! It means the invoice genuinely doesn't have prices on most lines (just volume info, prices on separate doc, etc.)
- If improves to `"ok"`/`"good"` → Great! More prices were successfully extracted

---

## Test B: Batch Tester (All Files)

### Command
```powershell
python backend/scripts/batch_test_ocr.py --all
```

### Expected Output

#### 1. Parity Breakdown (at top)
```
Parity Quality Breakdown:
  Excellent (<1% mismatch): 12
  Good (<3% mismatch):      8
  Ok (<8% mismatch):        5
  Poor (>=8% mismatch):     3
  Unknown:                  2
```

#### 2. Per-File Details
```
Filename                         Status  Items  Conf   Method    Parity  Mismatch%  Time
----------------------------------------------------------------------------------------
...__26.08INV.jpeg               ✅ ok    3      0.833  fallback  poor    95.3%      2.1s
invoice_clean.pdf                ✅ ok    15     0.912  table     excellent 0.2%     3.4s
```

### What to Analyze

#### High Confidence + Good Parity = Production Ready ✅
```
Items: 15, Conf: 0.912, Parity: excellent, Mismatch: 0.2%
```
→ This document type is **production-ready**

#### High Confidence + Poor Parity = Missing Prices ⚠️
```
Items: 8, Conf: 0.850, Parity: poor, Mismatch: 85.3%
```
→ Structure is good, but prices aren't on the page. Either:
- Delivery note / pick list (no prices)
- Prices in format we don't handle yet (e.g., stacked columns)

#### Unknown Parity = No Totals Found ❓
```
Items: 5, Conf: 0.750, Parity: unknown, Mismatch: -
```
→ Couldn't find totals in footer, or no line items with prices

---

## 📊 Interpreting Results

### Scenario 1: Most Invoices Are Good/Excellent
```
Excellent: 15
Good: 8
Ok: 3
Poor: 2
Unknown: 1
```
**Verdict**: ✅ **System is production-ready** for most document types

### Scenario 2: Mixed Results by Supplier
```
Supplier A invoices: All excellent/good
Supplier B invoices: All poor/unknown
```
**Verdict**: ✅ **Supplier A is production-ready**, Supplier B needs targeted improvements

### Scenario 3: Most Are Poor/Unknown
```
Excellent: 2
Good: 3
Ok: 5
Poor: 15
Unknown: 5
```
**Verdict**: ⚠️ **Need to investigate**:
- Are these delivery notes (no prices)?
- Are prices in a different format?
- Do we need column-based extraction instead of line-based?

---

## 🔍 Debugging Tips

### Check if Backfill is Working
Look for log messages:
```
[LINE_FALLBACK] Backfilled total_price: 4.0 × 50.0 = 200.00
```

### Check Price Extraction
Look for extracted prices in logs:
```
[LINE_FALLBACK] Extracted item 1: qty=1, desc='ORANGE JUICE...', unit=69.31, total=69.31
```

### Verify Parity Computation
Check that `sum_line_total` includes backfilled prices:
- Sum all `total_price` values from `line_items`
- Compare to `sum_line_total` in response
- Should match (within rounding)

---

## 📝 Next Steps Based on Results

### If Most Invoices Are Good/Excellent
✅ **You're done!** System is production-ready.

### If Specific Suppliers Are Poor
**Next prompt**: "Improve price extraction for [Supplier X] invoices that use [specific format]"

### If Prices Are in Stacked Columns
**Next prompt**: "Add column-based price extraction for invoices with separate Qty/Price/Total columns"

### If Many Are Unknown
**Next prompt**: "Improve footer total extraction to handle [specific format]"

---

## 🎯 Success Criteria

✅ **Red Dragon test**:
- Orange Juice line still extracts `unit_price: "69.31"`, `total_price: "69.31"`
- If other lines have prices in OCR → they're now extracted
- Backfill works for lines with qty + unit_price but no total_price

✅ **Batch tester**:
- Shows clear parity breakdown
- Handles missing ratings gracefully
- Provides actionable insights per supplier/doc type

✅ **No regressions**:
- Existing "excellent" parity invoices remain excellent
- Item counts and confidence scores are similar or better

---

## 📋 Quick Reference

### Key Files Modified
1. `backend/ocr/table_extractor.py`
   - `_extract_prices_from_line_end()` (new method)
   - `fallback_extract_from_lines()` (updated price extraction + backfill)

2. `backend/scripts/batch_test_ocr.py`
   - `print_summary()` (enhanced parity display)

### Key Metrics to Watch
- `parity_rating`: excellent / good / ok / poor / unknown
- `total_mismatch_pct`: Percentage difference between sum and header total
- `sum_line_total`: Sum of all line item totals (includes backfilled)
- `cell_data["price_backfill"]`: Indicates computed vs extracted prices

---

**Status**: ✅ **Implementation Complete - Ready for Testing**
