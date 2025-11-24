# Test Suite - OCR Pipeline End-to-End

Comprehensive API and E2E tests for the OCR → Cards → Line Items pipeline with artifact generation.

## Test Structure

```
tests/
├── api/
│   └── test_invoices_api.py    # Pytest API tests
├── e2e/
│   └── invoices.spec.ts         # Playwright E2E tests
├── fixtures/
│   └── *.pdf                    # Test PDF files (auto-generated)
├── artifacts/
│   ├── api/                     # JSON responses, logs
│   └── e2e/                     # Screenshots
├── run_all.ps1                  # CI-style runner (Windows)
└── README.md                    # This file
```

## Prerequisites

```powershell
# Install Python dependencies
pip install pytest requests reportlab

# Install Node/Playwright dependencies
npm install
npx playwright install --with-deps chromium
```

## Quick Start

### Run All Tests (Recommended)

```powershell
# Single command - builds, serves, tests, artifacts
.\tests\run_all.ps1
```

This will:
1. Build frontend → `out/` → `backend/static/`
2. Start backend on port 8000
3. Run pytest API tests
4. Run Playwright E2E tests
5. Stop backend
6. Save artifacts to `tests/artifacts/`

### Run Individual Test Suites

#### API Tests Only

```powershell
# Ensure backend is running first
python -m uvicorn backend.main:app --port 8000

# In another terminal:
python -m pytest tests/api/test_invoices_api.py -v -s
```

#### E2E Tests Only

```powershell
# Ensure backend + frontend are running
python -m uvicorn backend.main:app --port 8000

# Run E2E tests
npx playwright test tests/e2e/invoices.spec.ts --reporter=list

# With headed browser (for debugging)
npx playwright test tests/e2e/invoices.spec.ts --headed
```

## Test Coverage

### API Tests (`test_invoices_api.py`)

| Test | What It Proves |
|------|----------------|
| `test_upload_returns_processing` | Upload endpoint returns `{doc_id, filename, status: "processing"}` |
| `test_lifecycle_completes_with_items` | Document progresses to ready state with `line_items[]` populated |
| `test_duplicate_upload_no_dupe_cards` | Uploading same file twice creates 2 unique doc_ids, no duplicates |
| `test_retry_ocr_recovers` | `/api/ocr/retry/{doc_id}` endpoint works and reprocesses document |
| `test_api_response_contract` | `/api/invoices` returns required keys: `id, supplier, status, confidence, line_items` |

### E2E Tests (`invoices.spec.ts`)

| Test | What It Proves |
|------|----------------|
| `should load invoices page` | Page loads, key UI elements visible |
| `should upload file and display card` | File upload → card appears → line items table or empty state shown |
| `should not create duplicate cards` | Rapid double upload doesn't create UI duplicates |
| `should show retry button on error` | Error state shows retry button, clicking it reprocesses |

## Artifacts

After running tests, check `tests/artifacts/`:

### API Artifacts (`tests/artifacts/api/`)

```
upload_response.json              # Response from /api/upload
invoice_with_items.json           # Full invoice with line_items
invoice_full_detail.json          # Response from /api/invoices/{id}
duplicate_test_invoices.json      # Duplicate upload test results
retry_ocr_test.json               # Retry OCR test results
invoices_after_upload.json        # Full /api/invoices response
```

### E2E Artifacts (`tests/artifacts/e2e/`)

```
after_upload.png                  # Screenshot after file upload
after_expand.png                  # Screenshot after expanding card
duplicate_test.png                # Screenshot of duplicate upload test
after_retry.png                   # Screenshot after OCR retry
error_check.png                   # Screenshot of error state check
```

## Inspecting Artifacts

```powershell
# View API artifacts
Get-Content tests\artifacts\api\invoice_with_items.json | ConvertFrom-Json

# Open screenshot
Invoke-Item tests\artifacts\e2e\after_upload.png
```

## Test Configuration

### API Tests

- **Base URL**: `http://127.0.0.1:8000` (configurable in `test_invoices_api.py`)
- **Timeouts**: 15s for OCR completion, 10s for API calls
- **Test PDFs**: Auto-generated minimal PDFs if missing

### E2E Tests

- **Base URL**: `http://127.0.0.1:8000`
- **Browser**: Chromium (headless by default)
- **Timeouts**: 15s for card appearance, 10s for page load
- **Screenshots**: Full page, saved on every major step

## Debugging Failed Tests

### API Test Failures

```powershell
# Run single test with verbose output
python -m pytest tests/api/test_invoices_api.py::test_lifecycle_completes_with_items -v -s

# Check backend logs
tail -f logs/backend_stdout.log  # Linux/Mac
Get-Content -Wait logs\backend_stdout.log  # Windows

# Inspect artifact
cat tests/artifacts/api/invoice_with_items.json
```

### E2E Test Failures

```powershell
# Run with headed browser to watch
npx playwright test tests/e2e/invoices.spec.ts --headed --debug

# Check screenshot
Invoke-Item tests\artifacts\e2e\after_upload.png

# Playwright trace viewer (if enabled)
npx playwright show-trace trace.zip
```

### Common Issues

**Backend not starting**: Ensure port 8000 is free
```powershell
netstat -ano | findstr :8000
```

**Tests timing out**: Increase timeouts in test files or check backend performance

**Artifacts empty**: Check write permissions on `tests/artifacts/` directory

**PDFs not created**: Install `reportlab` or ensure fallback PDF generation works

## CI Integration

The `run_all.ps1` script is designed for CI environments:

```yaml
# Example GitHub Actions
- name: Run Test Suite
  run: |
    pip install pytest requests reportlab
    npm install
    npx playwright install --with-deps chromium
    pwsh tests/run_all.ps1

- name: Upload Artifacts
  uses: actions/upload-artifact@v3
  with:
    name: test-artifacts
    path: tests/artifacts/
```

## Acceptance Criteria (BRJ Standard)

✅ All pytest tests pass  
✅ Playwright spec passes  
✅ JSON artifacts contain `line_items[]` array  
✅ Screenshots saved successfully  
✅ Duplicate test confirms one invoice per upload (unique doc_ids)  
✅ Retry endpoint changes status → processing → ready  

**If any test fails**: Fix immediately and re-run. No exceptions.

## Next Steps

- Add multi-invoice PDF split test (one PDF → multiple invoices)
- Add long table test (>200 line items render performance)
- Add concurrent upload stress test (10 simultaneous uploads)
- Add lifecycle log extraction and validation
- Add performance budgets (Time To Interactive < 2s)

