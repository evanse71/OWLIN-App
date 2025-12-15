---
name: Delivery Note Line Items Storage & Retrieval Fix
overview: ""
todos:
  - id: b0388468-2435-40c3-84fe-79f54a62c02e
    content: Implement line item storage in create_manual_delivery_note() function in backend/routes/manual_entry.py
    status: pending
  - id: b1669a39-efb9-442e-a30b-48ec326eee45
    content: Update detect_short_delivery() in backend/services/issue_detector.py to correctly query delivery note line items
    status: pending
  - id: 0d5e683d-d3b0-4ab0-9324-c7f5df49c3f3
    content: Update _calculate_line_item_match_score() in backend/services/match_engine.py to correctly query delivery note line items
    status: pending
  - id: 7d0ce1a6-e088-41a0-91b3-0c0b8975e84e
    content: Create GET /api/delivery-notes/{id} endpoint that returns delivery note details with line items
    status: pending
  - id: c553acdc-c8b2-4d68-a772-bd7abe9b63d6
    content: Add error handling in SmartDiscrepancyWidget.tsx for missing line items
    status: pending
---

# Delivery Note Line Items Storage & Retrieval Fix

## Overview

Fix delivery note line items storage and retrieval to enable accurate discrepancy detection between invoices and delivery notes. This includes fixes for both manual and scanned delivery notes.

## Implementation Plan

### 1. Store Delivery Note Line Items (Backend) ✅ COMPLETED

**File:** `backend/routes/manual_entry.py`

- Implemented line item storage in `create_manual_delivery_note()` function
- Line items stored with `invoice_id = NULL` for delivery notes

### 2. Fix Issue Detector Query (Backend) ✅ COMPLETED

**File:** `backend/services/issue_detector.py`

- Updated query to filter by `invoice_id IS NULL` for delivery notes

### 3. Fix Match Engine Query (Backend) ✅ COMPLETED

**File:** `backend/services/match_engine.py`

- Updated query to filter by `invoice_id IS NULL` for delivery notes

### 4. Add Delivery Note Details Endpoint (Backend) ✅ COMPLETED

**File:** `backend/main.py`

- Created `GET /api/delivery-notes/{id}` endpoint
- Returns delivery note details with line items

### 5. Add Error Handling (Frontend) ✅ COMPLETED

**File:** `frontend_clean/src/components/invoices/SmartDiscrepancyWidget.tsx`

- Added error handling for missing line items

### 6. Fix OCR Service for Delivery Note Line Items (Backend) ⚠️ NEEDS FIX

**File:** `backend/services/ocr_service.py`

- **Location:** Lines 314-317
- **Issue:** When OCR processes delivery notes, it stores line items with `invoice_id = doc_id` instead of `NULL`
- **Impact:** Scanned delivery note line items won't be found by queries filtering `invoice_id IS NULL`
- **Action:** 
- Check `doc_type` from `parsed_data` before storing line items
- Set `invoice_id = None` for delivery notes when calling `insert_line_items()`
- Update logging to reflect correct behavior

### 7. Update `get_line_items_for_doc()` to Handle Delivery Notes (Backend) ⚠️ NEEDS FIX

**File:** `backend/app/db.py`

- **Location:** Lines 372-400
- **Issue:** Function doesn't filter by `invoice_id IS NULL`, so it may return invoice line items when querying delivery notes
- **Action:** 
- Check document type from `documents` table to determine if it's a delivery note
- Filter by `invoice_id IS NULL` when retrieving delivery note line items
- Maintain backward compatibility for existing calls

### 8. Verify `validate_quantity_match()` Works Correctly (Backend) ⚠️ NEEDS VERIFICATION

**File:** `backend/services/quantity_validator.py`

- **Location:** Line 161
- **Action:** 
- Verify the function works correctly after fixing `get_line_items_for_doc()`
- Ensure it correctly retrieves delivery note line items

## Success Criteria

- ✅ Manual delivery notes store line items in database
- ⚠️ Scanned delivery notes store line items with `invoice_id = NULL` (needs fix)
- ✅ Delivery note details endpoint returns line items
- ⚠️ Queries correctly distinguish between invoice and delivery note line items (needs fix)
- ✅ Discrepancy analysis can access delivery note line items
- ✅ Quantity comparisons work correctly
- ✅ No crashes when line items are missing
- ⚠️ Both manual and scanned delivery notes work correctly (scanned needs fix)