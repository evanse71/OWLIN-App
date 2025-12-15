# Gemini 3 Pro Integration Guide

## Overview
Integration template for LLM-based verification of complex invoices that fail numeric consistency checks.

**When to Use**: Only for ~15-20% of invoices flagged as "Needs Review"  
**Cost Savings**: 80% reduction vs LLM-first approach  
**Processing Time**: +2-5s for LLM verification  

---

## Architecture

### Decision Flow
```
Invoice Upload
    ↓
OCR Extraction (40-80s)
    ↓
Numeric Validation (<1ms)
    ↓
┌─────────────────────────────────────┐
│ Integrity Score Check               │
├─────────────────────────────────────┤
│ ≥ 0.9: Math-verified (Green)       │ → Auto-accept (80%)
│ 0.7-0.9: Verified (Blue)           │ → Auto-accept
│ 0.4-0.7: Needs Review (Yellow)     │ → LLM verification (15%)
│ < 0.4: Unverified (Gray)           │ → LLM or manual (5%)
└─────────────────────────────────────┘
    ↓
LLM Verification (if needed, +2-5s)
    ↓
Final Result
```

---

## Implementation

### File Created
**`backend/services/llm_verifier.py`**

### Key Functions

#### 1. `build_verification_prompt()`
Constructs a detailed prompt for Gemini 3 Pro including:
- Raw OCR text
- Current parsed data
- Validation issues
- Expected values (computed from line items)

#### 2. `verify_with_gemini_pro()`
Sends verification request to Gemini API:
- Low temperature (0.1) for factual accuracy
- Structured JSON response
- Error handling and logging

#### 3. `should_use_llm_verification()`
Decision logic for when to call LLM:
- Integrity score < 0.75
- Critical issues detected
- >30% of items missing data

---

## Prompt Template

### Input to Gemini
```
You are an expert invoice verification assistant.

RAW OCR TEXT:
[Full text from PaddleOCR]

CURRENT EXTRACTED DATA:
- Supplier: Red Dragon Brewery
- Total: £1.50 (SUSPECT)
- Subtotal: £548.03
- VAT: £109.61 (20%)
- Line Items: 2 items

VALIDATION ISSUES:
- CRITICAL OCR ERROR: total £1.50 seems too low (expected ~£657.60)
- Total mismatch: header £1.50 vs expected £657.60 (diff: £656.10)

EXPECTED VALUES:
- Items Subtotal: £548.00
- VAT Expected: £109.60
- Total Expected: £657.60

YOUR TASK:
1. Re-read the raw OCR text
2. Reconstruct line items with correct qty/unit_price/total
3. Verify subtotal, VAT, and total match printed values
4. Return corrected JSON
```

### Output from Gemini
```json
{
  "verification_status": "corrected",
  "confidence": 0.95,
  "corrections_made": [
    "Corrected total from £1.50 to £657.60 (OCR misread decimal point)",
    "Verified line items match printed invoice"
  ],
  "invoice": {
    "supplier": "Red Dragon Brewery",
    "invoice_number": "RDB-2025-1234",
    "date": "2025-11-15",
    "subtotal": 548.03,
    "vat_rate": 0.20,
    "vat_amount": 109.61,
    "total": 657.64,
    "line_items": [
      {
        "description": "Premium Beer Case A",
        "qty": 12,
        "unit_price": 37.67,
        "line_total": 452.04
      },
      {
        "description": "Craft Beer Case B",
        "qty": 4,
        "unit_price": 23.99,
        "line_total": 95.96
      }
    ]
  },
  "validation": {
    "subtotal_check": "pass",
    "vat_check": "pass",
    "total_check": "pass",
    "explanation": "Corrected total from £1.50 to £657.64. OCR misread the decimal point. All other values are consistent with the printed invoice."
  }
}
```

---

## Integration Example

### In `backend/services/ocr_service.py`

```python
from backend.services.llm_verifier import verify_with_gemini_pro, should_use_llm_verification

# After numeric validation
if should_use_llm_verification(validation):
    logger.info(f"[LLM] Requesting verification for doc_id={doc_id}")
    
    llm_result = verify_with_gemini_pro(
        raw_ocr_text=raw_text,
        parsed_data=parsed_data,
        validation=validation
    )
    
    if llm_result and llm_result['verification_status'] in ['verified', 'corrected']:
        # Use LLM's corrected data
        logger.info(f"[LLM] Using LLM-corrected data (confidence: {llm_result['confidence']})")
        
        # Update parsed data with LLM corrections
        llm_invoice = llm_result['invoice']
        parsed_data.update({
            'supplier': llm_invoice.get('supplier'),
            'invoice_no': llm_invoice.get('invoice_number'),
            'date': llm_invoice.get('date'),
            'subtotal': llm_invoice.get('subtotal'),
            'vat': llm_invoice.get('vat_amount'),
            'vat_rate': llm_invoice.get('vat_rate'),
            'total': llm_invoice.get('total'),
        })
        
        # Update line items
        line_items = llm_invoice.get('line_items', [])
        
        # Update validation badge
        validation_result['badge'] = {
            'label': 'LLM-verified',
            'color': 'green',
            'tooltip': f"Verified by AI (confidence: {llm_result['confidence']:.2f})"
        }
        validation_result['llm_corrections'] = llm_result.get('corrections_made', [])
        validation_result['llm_confidence'] = llm_result['confidence']
```

---

## Setup

### 1. Install Gemini SDK
```bash
pip install google-generativeai
```

### 2. Set API Key
```bash
# Windows
$env:GEMINI_API_KEY="your-api-key-here"

# Or add to .env file
GEMINI_API_KEY=your-api-key-here
```

### 3. Enable in Config
```python
# backend/config.py
FEATURE_LLM_VERIFICATION = env_bool("FEATURE_LLM_VERIFICATION", False)
```

---

## Cost Analysis

### Gemini 3 Pro Pricing (Estimated)
- Input: $0.00125 per 1K tokens
- Output: $0.005 per 1K tokens

### Per Invoice (with LLM)
- Input: ~1,500 tokens (OCR text + prompt) = $0.00188
- Output: ~500 tokens (JSON response) = $0.0025
- **Total**: ~$0.0044 per invoice

### Monthly Cost (1000 invoices)
| Scenario | LLM Usage | Cost |
|----------|-----------|------|
| **With Validation** | 150-200 invoices (15-20%) | **$0.66-$0.88** |
| Without Validation | 1000 invoices (100%) | $4.40 |

**Savings**: ~80% ($3.50+ per 1000 invoices)

---

## Testing

### Test 1: Red Dragon Invoice
```python
# Simulate Red Dragon case
validation = ValidationResult(
    is_consistent=False,
    integrity_score=0.65,
    issues=["CRITICAL OCR ERROR: total £1.50 seems too low"],
    corrections={"total": 657.60},
    details={"total_expected": 657.60}
)

if should_use_llm_verification(validation):
    llm_result = verify_with_gemini_pro(
        raw_ocr_text=ocr_text,
        parsed_data=parsed_data,
        validation=validation
    )
    
    # Expected: LLM corrects £1.50 → £657.60
    assert llm_result['invoice']['total'] == 657.60
    assert llm_result['verification_status'] == 'corrected'
```

### Test 2: Clean Invoice (No LLM)
```python
validation = ValidationResult(
    is_consistent=True,
    integrity_score=0.95,
    issues=[],
    corrections={},
    details={}
)

# Should NOT request LLM
assert not should_use_llm_verification(validation)
# Badge should be green "Math-verified"
```

---

## Production Workflow

### Scenario 1: Clean Invoice (80%)
```
OCR → Validation → Math-verified (Green) → Auto-accept
Cost: $0 | Time: 45s
```

### Scenario 2: Auto-Corrected (15%)
```
OCR → Validation → Auto-correct → Verified (Blue) → Auto-accept
Cost: $0 | Time: 45s
```

### Scenario 3: Critical Error (5%)
```
OCR → Validation → Critical issue → LLM verify → Corrected → Accept
Cost: $0.0044 | Time: 50s
```

---

## UI Integration

### Badge Display
```tsx
{invoice.validation?.badge && (
  <span 
    className={`badge badge-validation-${invoice.validation.badge.color}`}
    title={invoice.validation.badge.tooltip}
  >
    {invoice.validation.badge.label}
  </span>
)}
```

### Possible Badges
- 🟢 **Math-verified** - No LLM needed
- 🟢 **LLM-verified** - Verified by AI
- 🔵 **Verified** - Auto-corrected, no LLM
- 🟡 **Needs Review** - LLM recommended or human review
- ⚪ **Unverified** - Manual entry needed

---

## Next Steps

### To Enable LLM Verification:

1. **Install SDK**
   ```bash
   pip install google-generativeai
   ```

2. **Add API Key**
   ```bash
   $env:GEMINI_API_KEY="your-key"
   ```

3. **Enable Feature**
   ```python
   # backend/config.py
   FEATURE_LLM_VERIFICATION = True
   ```

4. **Integrate in OCR Service**
   - Add LLM verification call after numeric validation
   - Update validation badge based on LLM result
   - Store both OCR and LLM results for audit

---

## Files

- `backend/services/llm_verifier.py` (NEW) - LLM integration
- `GEMINI_INTEGRATION_GUIDE.md` (this file) - Documentation

---

**Status**: ✅ Template ready - Add API key to enable LLM verification for complex invoices!

