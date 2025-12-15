---
name: Steps 3-5 Verification and Completion Plan
overview: ""
todos:
  - id: ba910be8-9a52-42b2-a3eb-d2bc3e87bfa2
    content: "Fix syntax error in test_invoice_validation.py at line 118 (incorrect else: indentation)"
    status: pending
  - id: d33cadf2-952e-4e1e-aeac-02bd743ab3aa
    content: Verify test_invoice_validation.py meets all Step 4 requirements (runs pipeline, prints all required info, verifies hard gate)
    status: pending
  - id: 2fd195c8-3494-4b52-8181-268ada464706
    content: Create STEP_5_EXPECTED_OUTCOMES.md documenting how each fix addresses the original problems and expected behavior
    status: pending
---

# Steps 3-5 Verification and Completion Plan

## Current Status

Based on Step 2 verification, all Step 3 implementation appears to be complete:

- Config settings verified
- Prompt strengthening verified
- Footer filtering verified
- Hard validation gate verified
- Full-page text assembly verified
- Database integration verified

However, Step 4 test script has a syntax error that needs fixing.

## Step 3: Implementation Verification

### Files to Verify (Already Implemented)

1. **backend/config.py**

- Line 16: `FEATURE_OCR_V2_PREPROC = True` - VERIFIED
- Line 106: `LLM_VALIDATION_ERROR_THRESHOLD = 0.10` - VERIFIED

2. **backend/llm/invoice_parser.py**

- Prompt strengthening (lines 314-428): Container/policy filtering, total multiplication warning - VERIFIED
- `_filter_footer_lines()` method (lines 735-804) - VERIFIED
- `_verify_and_score()` hard gate (lines 1048-1184) - VERIFIED

3. **backend/ocr/owlin_scan_pipeline.py**

- Full-page text assembly (lines 717-723) - VERIFIED
- Page-level and table result merging (lines 777-792) - VERIFIED

4. **backend/services/ocr_service.py**

- needs_review status handling (lines 308-322) - VERIFIED

5. **backend/app/db.py**

- Status handling in upsert_invoice (lines 394, 406-408) - VERIFIED

**Action:** Confirm all Step 3 implementations are production-ready (already verified in Step 2).

## Step 4: Testing - Fix and Enhance Test Script

### Current Issues

**File:** `backend/scripts/test_invoice_validation.py`

**Problem:** Syntax error at line 118 - `else:` statement has incorrect indentation/context.

**Fix Required:**

- Line 118: Fix indentation of `else:` block
- Ensure proper if/else structure for needs_review check
- Verify script runs without syntax errors

### Test Script Requirements (Step 4)

The script should:

1. Run full OCR → LLM → validation pipeline
2. Print supplier name, totals, confidence, needs_review status
3. Calculate and display validation errors
4. Verify hard gate triggers for invoices with >10% error
5. Support output to file for automated testing

**Current Implementation:**

- ✅ Runs full pipeline (OCR → LLM → validation)
- ✅ Prints supplier name, totals, confidence, needs_review
- ✅ Calculates validation errors
- ✅ Shows hard gate status
- ❌ Has syntax error preventing execution

**Action:** Fix syntax error in test_invoice_validation.py

## Step 5: Expected Outcomes Documentation

### Expected Fixes

1. **Wrong supplier name:**

- Fixed by: Full-page context (owlin_scan_pipeline.py:717-723) + prompt clarification (invoice_parser.py:400)
- Status: ✅ Implemented

2. **100× total error:**

- Fixed by: Prompt warning (invoice_parser.py:375-383) + hard validation gate (invoice_parser.py:1099, 1125)
- Status: ✅ Implemented

3. **Container text in line items:**

- Fixed by: Prompt rules (invoice_parser.py:359-363) + post-filtering (invoice_parser.py:735-804)
- Status: ✅ Implemented

4. **Hard gate behavior:**

- Invoices with >10% error saved with status='needs_review', confidence capped at 0.5
- Status: ✅ Implemented (invoice_parser.py:1166, ocr_service.py:322, db.py:394)

**Action:** Document these expected outcomes in a summary file.

## Implementation Tasks

### Task 1: Fix Test Script Syntax Error

**File:** `backend/scripts/test_invoice_validation.py`

- Fix indentation issue at line 118
- Ensure proper if/else structure
- Test script runs without errors

### Task 2: Verify Test Script Meets Requirements

**File:** `backend/scripts/test_invoice_validation.py`

- Verify all Step 4 requirements are met
- Ensure output format is clear and complete
- Test with sample invoice file

### Task 3: Create Expected Outcomes Documentation

**File:** `STEP_5_EXPECTED_OUTCOMES.md` (new)

- Document how each fix addresses the original problems
- Explain hard gate behavior
- Provide examples of expected results

## Verification Checklist

### Step 3 Verification

- [x] Config settings (FEATURE_OCR_V2_PREPROC, LLM_VALIDATION_ERROR_THRESHOLD)
- [x] Prompt strengthening (container/policy filtering, total warnings)
- [x] Footer filtering method (_filter_footer_lines)
- [x] Hard validation gate (_verify_and_score)
- [x] Full-page text assembly (owlin_scan_pipeline)
- [x] Database status handling (ocr_service, db)

### Step 4 Testing

- [ ] Fix syntax error in test_invoice_validation.py
- [ ] Verify test script runs successfully
- [ ] Verify test script outputs all required information
- [ ] Test with sample invoice to verify hard gate behavior

### Step 5 Documentation

- [ ] Create expected outcomes documentation
- [ ] Document how each fix addresses original problems
- [ ] Explain hard gate behavior and status handling

## Files to Modify

1. `backend/scripts/test_invoice_validation.py` - Fix syntax error (line 118)
2. `STEP_5_EXPECTED_OUTCOMES.md` - Create new documentation file

## Notes

- Step 3 implementation is already complete (verified in Step 2)
- Main task is fixing the test script syntax error
- Documentation will help verify expected behavior