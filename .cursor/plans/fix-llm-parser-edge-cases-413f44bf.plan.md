---
name: "Fix LLM Parser Edge Cases: Stori Zero Quantity & Red Dragon Hallucination"
overview: ""
todos:
  - id: 036bd4cc-aa83-4890-adff-0061bf9910aa
    content: "Enhance _repair_line_items() to prioritize zero-quantity fix: when Qty==0 AND Unit Price > 0, force Qty=1 and recalculate Total immediately"
    status: pending
  - id: e99d6627-0d32-45c1-8e0c-186cbba455a4
    content: Strengthen prompt header filtering rules to explicitly ignore VAT Registration, Address, Phone, Email patterns with examples
    status: pending
  - id: 1428e7f5-a49b-4efc-b62c-162b35e252ba
    content: Enhance merged columns rule in prompt with explicit examples and clearer instructions for splitting quantity from description
    status: pending
  - id: 34f4ea49-03a2-4152-b669-1bf7ca7e1dbc
    content: "Add new multi-page delivery note rule: if 'Delivery Note' appears in OCR text, return empty line_items and set document_type to 'delivery_note'"
    status: pending
  - id: 23c87379-0042-4ce7-8029-f2b4ad6dc4e5
    content: Verify and enhance _clean_supplier_name() to ensure all payment term variations are covered, add regex fallback for complex patterns
    status: pending
---

# Fix LLM Parser Edge Cases: Stori Zero Quantity & Red Dragon Hallucination

## Current State Analysis

The `backend/llm/invoice_parser.py` file already has:

- `_repair_line_items()` method (lines 668-745) with some repair logic
- `_get_extraction_prompt()` method (lines 312-372) with basic extraction rules
- `_clean_supplier_name()` method (lines 814-868) with payment terms removal

However, these need enhancement to fix the specific bugs:

1. **Stori Invoice**: Qty=0 when it should be 12 (needs more aggressive repair)
2. **Red Dragon Invoice**: LLM extracting header info as line items, merging columns incorrectly, reading delivery note page

## Implementation Plan

### Task 1: Aggressive Self-Healing Logic Enhancement

**File**: `backend/llm/invoice_parser.py`
**Method**: `_repair_line_items()` (lines 668-745)

**Changes**:

1. **Prioritize the zero-quantity fix**: Move the check for `Qty == 0 AND Unit Price > 0` to the top of the repair logic, before other calculations
2. **Force Qty = 1 when appropriate**: When `item.qty == 0` (or `<= 0`) AND `item.unit_price > 0`, immediately set `qty = 1.0` and recalculate `total = qty * unit_price`
3. **Improve logging**: Add more detailed logging to track when this specific fix is applied

**Specific Code Changes**:

- Reorder the repair logic to check for `qty == 0 AND unit_price > 0` FIRST
- Ensure this check happens before any division operations that could fail
- Add explicit comment: "Fix for Stori invoice: Force Qty=1 when Qty=0 but Unit Price exists"

### Task 2: Advanced Prompt Engineering

**File**: `backend/llm/invoice_parser.py`
**Method**: `_get_extraction_prompt()` (lines 312-372)

**Changes**:

1. **Strengthen Header Filtering Rules**:

- Add explicit examples: "DO NOT extract 'VAT Registration No: GB123456789' as a line item"
- Add rule: "If a line contains 'VAT Registration', 'Address:', 'Phone:', 'Tel:', or 'Email:', IGNORE it completely"
- Clarify: "Only extract actual product/service descriptions, quantities, and prices"

2. **Enhance Merged Columns Rule**:

- Make the existing rule (line 326) more explicit with examples
- Add: "When you see patterns like '6 12 LITRE PEPSI', split immediately: Qty=6, Description='12 LITRE PEPSI'"
- Add: "If a line starts with a number followed by another number, the first is ALWAYS the quantity"

3. **Add Multi-Page Delivery Note Rule** (NEW):

- Add a new section: "**MULTI-PAGE DOCUMENT HANDLING:**"
- Rule: "If the OCR text contains the words 'Delivery Note' or 'DELIVERY NOTE' anywhere on the page, DO NOT extract any line items from that page"
- Rule: "If you see 'Delivery Note' in the text, return an empty `line_items` array and set `document_type` to 'delivery_note'"
- Rule: "Only process pages that are clearly invoices or receipts, not delivery notes"

4. **Improve Noise Filtering Section**:

- Expand the existing noise filtering (lines 334-338) with more specific patterns
- Add: "IGNORE any line that matches these patterns: 'VAT Reg', 'Reg No', 'Company No', 'Address:', 'Tel:', 'Email:', 'Bank:', 'Account:', 'Sort Code:'"

### Task 3: Supplier Name Cleaning Enhancement

**File**: `backend/llm/invoice_parser.py`
**Method**: `_clean_supplier_name()` (lines 814-868)

**Changes**:

1. **Verify existing keywords**: The method already has "TERMS", "PAYMENT", "DUE DATE" in the `split_keywords` list (lines 832-845)
2. **Add additional patterns**: Add more variations like "& TERMS", "TERMS &", "PAYMENT TERMS &", etc.
3. **Improve regex matching**: Consider using regex for more flexible matching of these patterns
4. **Add edge case handling**: Handle cases where supplier name might have multiple keywords (e.g., "Snowdonia Hospitality & TERMS & PAYMENT")

**Specific Code Changes**:

- Review the `split_keywords` list to ensure all variations are covered
- Add regex-based matching as a fallback for complex patterns
- Add logging for when supplier names are cleaned

## Implementation Order

1. **Task 1** (Self-Healing): Fix the repair logic first - this is a Python-side fix that will immediately help
2. **Task 2** (Prompt Engineering): Update the prompt to prevent the issues at the source
3. **Task 3** (Supplier Cleaning): Verify and enhance the existing cleaning logic

## Testing Considerations

After implementation, test with:

- Stori invoice (should fix Qty=0 → Qty=1 when Unit Price exists)
- Red Dragon invoice (should not extract header info, should split merged columns correctly, should ignore delivery note page)
- Supplier names with various payment term patterns

## Files to Modify

- `backend/llm/invoice_parser.py` (3 methods to enhance)