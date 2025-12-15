# Running Invoice Validation Tests

## Prerequisites

1. **Ollama must be running** with a model available (qwen2.5-coder:7b or qwen2.5-coder:32b)
   - Check: `curl http://localhost:11434/api/tags`
   - Start if needed: `ollama serve`

2. **Python environment activated** (if using venv)
   - Windows: `.\.venv\Scripts\activate`
   - Linux/Mac: `source .venv/bin/activate`

## Test A: Stori Invoice (Clean Case)

```powershell
python backend/scripts/test_invoice_validation.py "data\uploads\36d55f24-1a00-41f3-8467-015e11216c91__Storiinvoiceonly1.pdf" "test_stori_results.txt"
```

**Expected Results:**
- Supplier Name: Stori / Stori Beer & Wine / Snowdonia Spirit Co
- Reasonable line items (names & totals)
- Subtotal / VAT Amount / Grand Total match the PDF
- Grand Total Error and Subtotal Error ≈ 0–1%
- Confidence high (≥ 0.8 ideally)
- Needs Review: False
- Ending message: ✅ Invoice passed validation

## Test B: Wild Horse Invoice (Problem Case)

**Note:** You'll need to provide the path to your Wild Horse invoice file.

```powershell
python backend/scripts/test_invoice_validation.py "path\to\Wild_Horse_invoice.pdf" "test_wildhorse_results.txt"
```

**Expected Results:**
- Grand Total around £891.54 (not 89,154.00)
- OR, if LLM still misreads but math doesn't line up:
  - Grand Total Error significantly > 10%
  - Needs Review: True
  - ⚠ Validation Errors block showing subtotal / grand total mismatch
  - Ending message: 🔴 INVOICE MARKED FOR REVIEW with clear reason

**Also check line items:**
- Should NOT include:
  - "Delivered in containers…"
  - "Containers outstanding…"
  - All-caps return policy text

## Quick Setup Check

Before running tests, verify your setup:

```powershell
python backend/scripts/test_setup_check.py
```

This will check:
- ✓ Imports working
- ✓ Configuration correct
- ✓ Ollama connection
- ✓ Test files exist

## Viewing Results

Results are written to the specified output file (e.g., `test_stori_results.txt`). You can view them with:

```powershell
Get-Content test_stori_results.txt
```

Or open in any text editor.

## Troubleshooting

**If tests hang:**
- Check Ollama is running: `curl http://localhost:11434/api/tags`
- Check model is available: `ollama list`
- LLM processing can take 30-120 seconds per invoice

**If you see import errors:**
- Make sure you're in the project root directory
- Activate virtual environment if using one
- Check Python path includes project root

**If validation doesn't trigger:**
- Check `FEATURE_LLM_EXTRACTION = True` in `backend/config.py`
- Check `LLM_VALIDATION_ERROR_THRESHOLD = 0.10` is set
- Verify Ollama model is responding
