# Step 5: Expected Outcomes

This document describes how each fix addresses the original problems and the expected behavior of the system.

## Original Problems

1. **Wrong supplier name** - System extracted distributor/payment processor names instead of actual supplier
2. **100× total error** - Invoice total £891.54 was extracted as £89,154.00 (multiplied by 100)
3. **Container text in line items** - Container IDs and return policy text appeared as line items
4. **No validation gating** - Invoices with large errors were auto-saved without review flags

## Fixes and Expected Outcomes

### 1. Wrong Supplier Name - FIXED

**Problem:** System extracted wrong supplier name (e.g., distributor name or payment processor instead of actual supplier).

**Root Cause:**
- LLM only saw block-level OCR text, missing full-page context
- Prompt didn't explicitly clarify where supplier name should come from
- Footer text was sometimes used instead of header

**Fixes Applied:**

1. **Full-Page Text Assembly** (`backend/ocr/owlin_scan_pipeline.py:717-723`)
   - Assembles text from all OCR blocks into full-page context
   - LLM now sees complete document structure

2. **Page-Level Parsing** (`backend/ocr/owlin_scan_pipeline.py:726-743`)
   - Parses full-page text once for header/footer fields
   - Extracts supplier name from full document context

3. **Prompt Clarification** (`backend/llm/invoice_parser.py:400`)
   - Explicitly states: "Extract the main supplier name from the header/top of the document"
   - Warns: "Do NOT use distributor names, payment processor names, or footer text"

**Expected Outcome:**
- Supplier name extracted from header/top of document
- Distributor names and payment processors ignored
- Footer text not used for supplier identification
- More accurate supplier name extraction

---

### 2. 100× Total Error - FIXED

**Problem:** Invoice total £891.54 was extracted as £89,154.00 (multiplied by 100).

**Root Cause:**
- LLM sometimes multiplied totals by 100 (treating decimal as whole number)
- No hard validation gate to catch large errors
- Soft validation only logged warnings but didn't flag for review

**Fixes Applied:**

1. **Prompt Warning** (`backend/llm/invoice_parser.py:375-383`)
   - Explicitly warns: "DO NOT multiply totals by 100"
   - Instructions to preserve decimal points exactly as shown
   - Example: "891.54" should NOT become "89154.00" or "89,154.00"
   - Marked as "CRITICAL - AVOID 100× ERRORS"

2. **Hard Validation Gate** (`backend/llm/invoice_parser.py:1099, 1125`)
   - Checks if relative error between calculated and extracted totals > 10%
   - If error exceeds threshold, sets `needs_review = True`
   - Caps confidence at 0.5 for review items
   - Stores validation errors in metadata

**Expected Outcome:**
- LLM preserves decimal points correctly (no multiplication by 100)
- If 100× error still occurs, hard gate catches it (>10% error)
- Invoice marked as `needs_review` instead of auto-saving
- Confidence capped at 0.5 to indicate low reliability
- Validation errors stored for user review

---

### 3. Container Text in Line Items - FIXED

**Problem:** Container IDs and return policy text appeared as line items (e.g., "CONTAINER ABC123", "WE DO NOT ACCEPT RETURNS").

**Root Cause:**
- LLM prompt didn't explicitly forbid container/policy text
- No post-processing filter to remove footer noise
- All-caps policy text looked like product descriptions

**Fixes Applied:**

1. **Prompt Rules** (`backend/llm/invoice_parser.py:359-369`)
   - Container Lists: Explicitly instructs to ignore container IDs, container numbers, container lists
   - Return Policy: Explicitly instructs to ignore return policy text, terms and conditions
   - Examples provided for both cases

2. **Post-Processing Filter** (`backend/llm/invoice_parser.py:735-804`)
   - `_filter_footer_lines()` method removes container/policy text
   - Called after LLM extraction (line 471)
   - Filters container keywords, all-caps policy text, and ID-only lines

**Expected Outcome:**
- Container IDs not extracted as line items
- Return policy text not extracted as line items
- Footer/legal text filtered out before saving
- Only actual products/services appear in line items

---

### 4. Hard Gate Behavior - IMPLEMENTED

**Problem:** Invoices with large errors were auto-saved without review flags.

**Root Cause:**
- Only soft validation (warnings, confidence penalties)
- No hard stop for large errors
- No status flagging for manual review

**Fixes Applied:**

1. **Hard Validation Gate** (`backend/llm/invoice_parser.py:1048-1184`)
   - Calculates relative error: `abs(calculated - extracted) / extracted`
   - Compares against `LLM_VALIDATION_ERROR_THRESHOLD` (0.10 = 10%)
   - If error > 10%: Sets `needs_review = True`, caps confidence at 0.5, stores errors

2. **Database Status Handling** (`backend/services/ocr_service.py:308-322`)
   - Detects `needs_review` flag from LLM result
   - Sets `invoice_status = 'needs_review'` if flag is true

3. **Database Storage** (`backend/app/db.py:394, 406-408`)
   - `needs_review` added to valid statuses list
   - `upsert_invoice()` accepts and stores status parameter

**Expected Outcome:**
- Invoices with >10% error automatically flagged for review
- Status set to `'needs_review'` instead of `'scanned'`
- Confidence capped at 0.5 to indicate low reliability
- Validation errors stored in metadata for user review
- Frontend can display "Needs Review" badge

---

## Summary of Expected Behavior

### Clean Invoice (No Errors)
- Supplier name extracted correctly from header
- Totals extracted with correct decimal points
- No container/policy text in line items
- Validation errors < 10%
- Status: `'scanned'`
- Confidence: High (0.8-1.0)
- `needs_review`: False

### Invoice with Errors (>10%)
- Validation errors > 10%
- Status: `'needs_review'`
- Confidence: Capped at 0.5
- `needs_review`: True
- Validation errors stored in metadata

### Hard Gate Triggers When:
- Subtotal error > 10%: `abs(calculated_subtotal - extracted_subtotal) / extracted_subtotal > 0.10`
- Grand total error > 10%: `abs(calculated_grand - extracted_grand) / extracted_grand > 0.10`

### Hard Gate Actions:
1. Sets `needs_review = True`
2. Caps confidence at 0.5
3. Stores validation errors in metadata
4. Sets invoice status to `'needs_review'` in database
5. Logs error with details for debugging

---

## Implementation Status

All fixes are implemented and verified:
- Config settings (FEATURE_OCR_V2_PREPROC, LLM_VALIDATION_ERROR_THRESHOLD)
- Prompt strengthening (container/policy filtering, total warnings)
- Footer filtering method (_filter_footer_lines)
- Hard validation gate (_verify_and_score)
- Full-page text assembly (owlin_scan_pipeline)
- Database status handling (ocr_service, db)
- Test script (test_invoice_validation.py)

**Status:** Production-ready pending end-to-end testing with real invoices.
