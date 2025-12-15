---
name: Add Python Self-Healing Logic to LLM Parser
overview: ""
todos: []
---

# Add Python Self-Healing Logic to LLM Parser

## Overview

Add post-processing repair methods to `backend/llm/invoice_parser.py` that fix common LLM extraction errors using Python logic. This ensures data correctness even when the LLM fails to follow instructions.

## Current State

- LLM extracts data but sometimes returns qty=0, missing invoice numbers, or messy supplier names
- `_verify_and_score` only fixes totals, not quantities or missing fields
- No fallback logic to extract invoice numbers from OCR text
- No supplier name cleaning

## Implementation Plan

### 1. Add `_repair_line_items` Method

**File**: `backend/llm/invoice_parser.py`

**Location**: After `_parse_llm_response` method (around line 650)

```python
def _repair_line_items(self, items: List[LLMLineItem]) -> List[LLMLineItem]:
    """
    Repair line items by fixing quantities and totals using Python math.
    
    Rules:
  - If qty is 0/None but total and unit_price > 0: calculate qty = total / unit_price
  - If total is 0 but qty and unit_price > 0: calculate total = qty * unit_price
  - If qty is still 0 after calculations: default to 1
    
    Args:
        items: List of line items to repair
        
    Returns:
        Repaired list of line items
    """
```

**Logic**:

- Iterate through each item
- If `qty <= 0` and `total > 0` and `unit_price > 0`: `qty = total / unit_price`
- If `total <= 0` and `qty > 0` and `unit_price > 0`: `total = qty * unit_price`
- If `qty <= 0` after all attempts: set `qty = 1.0`
- Round qty to 2 decimal places
- Log repairs for debugging

### 2. Add `_repair_invoice_number` Method

**File**: `backend/llm/invoice_parser.py`

**Location**: After `_repair_line_items` method

```python
def _repair_invoice_number(self, extracted_num: str, ocr_text: str) -> str:
    """
    Extract invoice number from OCR text if LLM missed it.
    
    Args:
        extracted_num: Invoice number from LLM (may be empty)
        ocr_text: Raw OCR text to search
        
    Returns:
        Invoice number (extracted or original)
    """
```

**Logic**:

- If `extracted_num` is not empty/None: return it
- Search OCR text with regex patterns:
    - `Invoice\s*(?:No|Number|#)?\s*[:.]?\s*([A-Z0-9-]{3,})`
    - `INV[-\s]?([A-Z0-9-]{3,})`
    - `Invoice\s*([A-Z]{2,}\d{4,})`
- Return first match found
- Log if repair was made

### 3. Add `_clean_supplier_name` Method

**File**: `backend/llm/invoice_parser.py`

**Location**: After `_repair_invoice_number` method

```python
def _clean_supplier_name(self, name: str) -> str:
    """
    Clean supplier name by removing payment terms and other noise.
    
    Args:
        name: Raw supplier name from LLM
        
    Returns:
        Cleaned supplier name
    """
```

**Logic**:

- Split on keywords: "TERMS", "Terms", "PAYMENT", "Payment", "Due Date", "DUE DATE"
- Keep only the part before the keyword
- Strip whitespace
- If name contains "Ltd" or "Limited", ensure it's at the end (don't split on it)
- Return cleaned name

### 4. Update `parse_document` Method

**File**: `backend/llm/invoice_parser.py`

**Location**: Modify `parse_document` method (around line 374-422)

**Changes**:

- After `_parse_llm_response` (line 405), add repair calls:

    1. `result.line_items = self._repair_line_items(result.line_items)`
    2. `result.invoice_number = self._repair_invoice_number(result.invoice_number, ocr_text)`
    3. `result.supplier_name = self._clean_supplier_name(result.supplier_name)`

- Store OCR text in result metadata for debugging: `result.metadata['ocr_text_length'] = len(ocr_text)`
- Add logging to track repairs made

### 5. Update `_verify_and_score` Method

**File**: `backend/llm/invoice_parser.py`

**Location**: Modify `_verify_and_score` method (around line 655)

**Changes**:

- Since quantities are now repaired, the math verification should be more accurate
- Keep existing logic but note that qty should rarely be 0 after repair
- Update confidence penalties if needed

## Implementation Details

### Repair Order

1. Repair line items first (fixes qty and total)
2. Repair invoice number (uses OCR text)
3. Clean supplier name (text processing)
4. Then verify and score (existing logic)

### Error Handling

- All repair methods should handle edge cases gracefully
- If repair fails, return original value
- Log warnings for failed repairs
- Don't throw exceptions - always return a value

### Logging

- Log when repairs are made: `LOGGER.info(f"[REPAIR] Fixed qty for '{item.description}': {old_qty} -> {new_qty}")`
- Log when invoice number is found: `LOGGER.info(f"[REPAIR] Extracted invoice number from OCR: {invoice_num}")`
- Log when supplier name is cleaned: `LOGGER.info(f"[REPAIR] Cleaned supplier name: '{old_name}' -> '{new_name}')`

## Testing Considerations

- Test with qty=0, total>0, unit_price>0 (should calculate qty)
- Test with missing invoice number (should extract from OCR)
- Test with supplier name containing "TERMS" (should clean)
- Test with edge cases (all zeros, negative values, etc.)

## Files to Modify

- `backend/llm/invoice_parser.py` - Add three repair methods and update `parse_document`