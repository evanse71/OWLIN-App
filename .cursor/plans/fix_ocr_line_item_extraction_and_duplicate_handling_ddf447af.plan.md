---
name: Fix OCR line item extraction and duplicate handling
overview: "Fix three critical issues: (1) Line items showing QTY=0 and Total=£0 due to table extraction/parsing failures, (2) Duplicate documents not triggering OCR retry when invoice is missing, and (3) Better handling of stuck processing states with timeouts and error detection."
todos:
  - id: fix-duplicate-ocr-retry
    content: Add automatic OCR retry for duplicate documents with 'error' status and no invoice in backend/main.py
    status: completed
  - id: add-invoice-exists-check
    content: Add check_invoice_exists() helper function in backend/app/db.py
    status: completed
  - id: enhance-duplicate-response
    content: Enhance duplicate response in backend/main.py to include doc_status and has_invoice flags
    status: completed
  - id: improve-frontend-duplicate
    content: Improve frontend duplicate handling in Invoices.tsx to use has_invoice flag and handle error status immediately
    status: completed
  - id: add-document-status-endpoint
    content: Add GET /api/documents/{doc_id}/status endpoint in backend/main.py for checking stuck processing states
    status: completed
  - id: add-processing-timeout
    content: Add processing timeout detection in frontend upload.ts (2+ minutes = check document status)
    status: completed
  - id: fix-table-extraction
    content: Fix table extractor quantity/price extraction in backend/ocr/table_extractor.py based on diagnostic log evidence
    status: completed
  - id: improve-parsing-functions
    content: Improve _parse_quantity() and _parse_price() in backend/services/ocr_service.py to handle more edge cases
    status: completed
---

# Fix OCR Line Item Extraction and Duplicate Handling

## Issues Identified

1. **Line items showing QTY=0, Total=£0** - Table extractor is returning empty/invalid quantity and price strings that parse to 0
2. **Duplicate documents not handled properly** - When duplicate document exists but no invoice was created (OCR failed), system doesn't trigger retry
3. **OCR taking too long** - Documents stuck in 'processing' state for 110+ seconds without proper timeout/error handling

## Implementation Plan

### 1. Fix Line Item Quantity/Price Extraction

**File: `backend/services/ocr_service.py`**

- The diagnostic logging we added will show what raw values are being extracted
- **Hypothesis A**: Table extractor returns empty strings for quantity/price
  - Check `backend/ocr/table_extractor.py` to see how it extracts these values from table cells
  - Fix cell extraction logic if it's not finding quantity/price columns correctly
- **Hypothesis B**: Values are extracted but in wrong format (e.g., "£123.45" not being parsed)
  - Improve `_parse_quantity()` and `_parse_price()` to handle more formats
  - Add fallback parsing for edge cases
- **Hypothesis C**: Table extractor isn't finding the table at all
  - Check if table detection is working
  - Add fallback extraction methods

**Action**: After reviewing backend logs from the diagnostic logging, fix the root cause in table extraction or parsing logic.

### 2. Improve Duplicate Document Handling

**File: `backend/main.py` (lines 2066-2078)**

When duplicate document is detected:

- Check document status from database
- If status is 'error' and no invoice exists, automatically trigger OCR retry
- If status is 'processing', return status with indication that OCR is in progress
- Add `has_invoice` flag to duplicate response to help frontend decide next action

**Changes**:

```python
# After line 2068 (existing_doc check)
# Query document status and check if invoice exists
doc_status = existing_doc.get('status', 'processing')
# Check if invoice exists for this doc_id
invoice_exists = check_invoice_exists(existing_doc["id"])

response = {
    "doc_id": existing_doc["id"],
    "status": "duplicate",
    "doc_status": doc_status,  # Add actual document status
    "has_invoice": invoice_exists,  # Add invoice existence flag
    "message": "File already uploaded",
    ...
}

# If status is 'error' and no invoice, trigger OCR retry automatically
if doc_status == 'error' and not invoice_exists:
    logger.info(f"[UPLOAD] Duplicate document with error status - triggering OCR retry for doc_id={existing_doc['id']}")
    asyncio.create_task(_run_ocr_background(existing_doc["id"], existing_doc.get("stored_path")))
```

**File: `backend/app/db.py`**

Add helper function:

```python
def check_invoice_exists(doc_id: str) -> bool:
    """Check if an invoice exists for the given document ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM invoices WHERE doc_id = ?", (doc_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0
```

### 3. Improve Frontend Duplicate Handling

**File: `frontend_clean/src/pages/Invoices.tsx` (lines 627-668)**

- Already fixed: Check `inv.docId` instead of `inv.id` for duplicate invoice matching
- Add handling for `has_invoice` flag from backend
- If duplicate document has `doc_status: 'error'` and `has_invoice: false`, show error state with retry button immediately
- If `doc_status: 'processing'`, continue polling but with better timeout

**Changes**:

```typescript
if (result.metadata.raw?.status === 'duplicate' && uploadMetadataId) {
  const hasInvoice = result.metadata.raw?.has_invoice ?? false
  const docStatus = result.metadata.raw?.doc_status
  
  // Check if invoice exists by docId
  const invoiceExists = invoices.some((inv) => String(inv.docId || '') === uploadMetadataId)
  
  if (invoiceExists || hasInvoice) {
    // Complete immediately
  } else if (docStatus === 'error') {
    // Show error state immediately with retry button
    // Don't wait for polling
  } else {
    // Continue polling but with timeout
  }
}
```

### 4. Add Processing Timeout and Error Detection

**File: `frontend_clean/src/lib/upload.ts`**

- Add timeout detection: if status is 'processing' for more than 2 minutes, check document status via separate endpoint
- If document status is 'error', stop polling and show error state
- Add max processing time constant (e.g., 180 seconds)

**File: `backend/main.py`**

- Add endpoint to check document status directly: `GET /api/documents/{doc_id}/status`
- Returns document status, error message, and whether invoice exists
- Used by frontend to check stuck processing states

### 5. Improve Table Extractor Quantity/Price Extraction

**File: `backend/ocr/table_extractor.py`**

- Review how quantities and prices are extracted from table cells
- Ensure cell_data is properly populated with raw values
- Add validation to ensure quantity/price strings are not empty before returning LineItem
- Improve column detection for quantity and price columns

**Note**: This requires runtime evidence from the diagnostic logging we added. The fix will depend on what the logs show.

## Testing Strategy

1. Upload a file with known line items and verify quantities/prices are extracted correctly
2. Upload a duplicate file where OCR previously failed - verify retry is triggered
3. Upload a file and let it process - verify timeout handling works correctly
4. Check backend logs for the diagnostic warnings about qty=0/total=0 to identify root cause

## Dependencies

- Backend logs from diagnostic logging to identify why quantities/prices are 0
- Understanding of table structure in the invoice PDFs to fix column detection