# STORI Integration Complete

## What Was Done

1. **Created STORI Vendor Extractor**
   - File: `backend/ocr/vendors/stori_extractor.py`
   - Parses STORI invoices with PRODUCT/QTY/RATE/VAT/AMOUNT table format
   - Extracts date, subtotal, VAT, total, and line items

2. **Integrated into OCR Pipeline**
   - Modified `backend/services/ocr_service.py`
   - Auto-detects STORI invoices by looking for "Stori Beer & Wine" or "VAT Invoice" + "Bala" cues
   - Uses STORI extractor when detected, falls back to generic parser otherwise

3. **Validation Script**
   - File: `check_stori_data.py`
   - Run after upload to verify extraction

## Testing Instructions

### 1. Restart Backend
Stop and restart your backend server to load the changes.

### 2. Upload STORI PDF
Upload the STORI PDF via `/app` interface.

### 3. Verify Extraction
Run the validation script:
```bash
python check_stori_data.py
```

Or manually check database:
```sql
-- Recent invoices
SELECT id, supplier, date, value, status 
FROM invoices 
ORDER BY rowid DESC 
LIMIT 5;

-- Line items (replace <ID> with invoice ID from above)
SELECT invoice_id, description, qty, unit_price, total, confidence
FROM invoice_line_items 
WHERE invoice_id='<ID>'
ORDER BY line_number;
```

## Expected Results for STORI Sample

- **Supplier**: "Stori Beer & Wine CYF"
- **Date**: 2025-08-21
- **Value**: ~289.17 (pounds)
- **Line Items** (2 items):
  1. "Gwynt Black Dragon case of 12" - Qty: 8, Unit: £24.79, Total: £198.32
  2. "Barti Spiced 70cl" - Qty: 2, Unit: £21.33, Total: £42.66

## Smoke UI

The smoke UI at `/app` will automatically display the extracted data. The UI already handles multiple field names and will show:
- Supplier name
- Invoice date
- Total value
- Line items with description, qty, unit price, and totals

If `subtotal` or `vat` fields are present in the response, they will be rendered automatically (UI tolerates missing fields).

