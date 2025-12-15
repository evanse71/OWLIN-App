---
name: Fix Bounding Box Display in InvoiceVisualizer
overview: ""
todos: []
---

# Fix Bounding Box Display in InvoiceVisualizer

## Problem Analysis

The "Show Boxes" button in InvoiceVisualizer isn't displaying bounding boxes because:

1. **Type Definition Missing**: `InvoiceLineItem` type in `frontend_clean/src/types/invoice.ts` doesn't include `bbox` field
2. **Normalization Loss**: `normalizeInvoice()` function in `frontend_clean/src/lib/api.ts` creates new line item objects but doesn't preserve the `bbox` field from backend responses
3. **Data Flow**: Backend correctly stores and returns bbox data (verified in `backend/app/db.py`), but it's lost during frontend normalization

## Solution

### 1. Update Type Definition

**File**: `frontend_clean/src/types/invoice.ts`

- Add `bbox?: number[]` to `InvoiceLineItem` interface
- Format: `[x, y, w, h]` in pixels (matches backend format)

### 2. Fix Normalization Function

**File**: `frontend_clean/src/lib/api.ts`

- In `normalizeInvoice()`, preserve `bbox` field when creating line items
- Handle both `item.bbox` and `item.bbox` from raw backend data
- Ensure bbox is passed through unchanged if present

### 3. Verify Backend Data Flow

**Files to check**:

- `backend/app/db.py` - `get_line_items_for_invoice()` and `get_line_items_for_doc()` already return bbox
- `backend/main.py` - `/api/invoices/{invoice_id}` endpoint already includes line_items with bbox
- Verify OCR processing stores bbox correctly (should already be working based on code review)

### 4. Test InvoiceVisualizer Component

**File**: `frontend_clean/src/components/invoices/InvoiceVisualizer.tsx`

- Component already correctly filters items with bbox: `itemsWithBBoxes = lineItems.filter((item) => { const bbox = item.bbox; return bbox && Array.isArray(bbox) && bbox.length >= 4 })`
- Component already correctly renders boxes when `showBoxes` is true
- No changes needed to component logic

## Implementation Details

### Change 1: Add bbox to InvoiceLineItem type

```typescript
interface InvoiceLineItem {
  // ... existing fields ...
  confidence?: number | null
  bbox?: number[]  // [x, y, w, h] in original image pixels
}
```

### Change 2: Preserve bbox in normalizeInvoice

In the line items mapping section:

```typescript
lineItems.push({
  // ... existing fields ...
  confidence: item.confidence || null,
  bbox: item.bbox || undefined,  // Preserve bbox if present
})
```

## Verification Steps

1. Upload a new invoice with OCR processing
2. Verify bbox data is stored in database (check `invoice_line_items.bbox` column)
3. Verify API response includes bbox in line_items
4. Verify frontend receives bbox in normalized invoice data
5. Verify InvoiceVisualizer displays bounding boxes when "Show Boxes" is clicked
6. Verify boxes align correctly with invoice image content

## Production Readiness

- No dummy data - uses real OCR extraction results
- Handles missing bbox gracefully (component already filters items without bbox)
- Backward compatible (bbox is optional field)
- No breaking changes to existing functionality