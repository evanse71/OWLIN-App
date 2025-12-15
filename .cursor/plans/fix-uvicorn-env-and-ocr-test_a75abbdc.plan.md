---
name: fix-uvicorn-env-and-ocr-test
overview: Repair pydantic-core dependency, start backend with venv Python 3.11, and verify OCR test no longer emits excessive_quantity skips
todos:
  - id: reinstall-deps
    content: Reinstall pydantic/pydantic-core/fastapi/starlette/uvicorn in venv
    status: completed
  - id: clear-caches
    content: Delete backend __pycache__ and *.pyc
    status: completed
  - id: start-backend
    content: Run uvicorn with venv Python 3.11, no reload
    status: completed
  - id: verify-ocr
    content: Run health + OCR test; ensure no excessive_quantity and items>=1
    status: completed
---

# Fix uvicorn startup and verify OCR test

1) Reinstall matching deps in venv

- In repo root, uninstall pydantic, pydantic-core, fastapi, starlette, uvicorn.
- Reinstall pinned versions: pydantic==2.7.4, pydantic-core==2.18.4, fastapi==0.115.14, starlette==0.46.2, uvicorn[standard]==0.23.2.

2) Clear caches

- Remove backend/**pycache** and backend/**/*.pyc to avoid stale code paths.

3) Start backend with venv Python 3.11

- From repo root, run .venv311\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 5176 (no --reload).
- Confirm startup logs show [QUANTITY_TRACE] path to backend/ocr/table_extractor.py.

4) Verify OCR test

- Call /api/health then /api/dev/ocr-test with the Wild Horse filename.
- Expected: line_items_count >= 1, method_chosen != "none", and no "excessive_quantity" anywhere in skipped_lines or debug_skipped.