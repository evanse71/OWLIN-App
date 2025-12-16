# Testing Guide for Stuck at 100% Fixes

## Automated Backend Tests

Run the automated test script to verify the fixes work:

```powershell
# Activate virtual environment
cd C:\Users\tedev\FixPack_2025-11-02_133105
.\.venv311\Scripts\Activate.ps1

# Run tests
python test_stuck_100pct_fixes.py
```

**Expected Output**:
- ✅ Watchdog Detection: PASSED
- ✅ Watchdog Fixing: PASSED
- ✅ Exception Handling Structure: PASSED
- ✅ Status Update on Error: PASSED

---

## UI Testing (Recommended)

The UI is the best way to test the complete flow. Here's how:

### Test 1: Normal Upload Flow

1. **Start backend** (if not already running):
   ```powershell
   cd C:\Users\tedev\FixPack_2025-11-02_133105
   .\.venv311\Scripts\Activate.ps1
   python -m uvicorn backend.main:app --reload --port 8000
   ```

2. **Start frontend** (if not already running):
   ```powershell
   cd frontend_clean
   npm run dev
   ```

3. **Upload a normal invoice**:
   - Go to http://localhost:5176/invoices
   - Upload a PDF invoice
   - **Expected**: Card appears immediately, shows "Processing...", then updates to "Ready" or "Needs Review" when OCR completes

---

### Test 2: Watchdog Detection (Manual)

1. **Create a stuck document** (using API):
   ```powershell
   # Create a document stuck in processing
   $body = @{
       id = "test-stuck-manual"
       filename = "test.pdf"
       stored_path = "/tmp/test.pdf"
       size_bytes = 1000
       uploaded_at = (Get-Date).AddMinutes(-15).ToString("yyyy-MM-ddTHH:mm:ss")
       status = "processing"
       ocr_stage = "ocr_start"
   } | ConvertTo-Json
   
   # Insert via SQL (or use a test script)
   ```

2. **Check watchdog status**:
   ```powershell
   Invoke-RestMethod -Uri "http://localhost:8000/api/watchdog/status" -Method Get | ConvertTo-Json -Depth 5
   ```
   **Expected**: Shows stuck document(s) with minutes_stuck > 10

3. **Fix stuck documents**:
   ```powershell
   Invoke-RestMethod -Uri "http://localhost:8000/api/watchdog/fix-stuck?max_minutes=10" -Method Post | ConvertTo-Json
   ```
   **Expected**: Returns `{"status": "ok", "fixed_count": 1, ...}`

4. **Verify in UI**:
   - Check the document in the UI
   - **Expected**: Status changed to "Error" with error message

---

### Test 3: Exception Handling

1. **Upload a corrupted/invalid file**:
   - Create a file that will cause OCR to fail
   - Upload via UI
   - **Expected**: Card appears, shows "Error" status with error message

2. **Check backend logs**:
   - Look for `[OCR_V2]` error messages
   - **Expected**: All errors set document status to "error"

---

### Test 4: Timeout Protection (Advanced)

**Note**: This is hard to test without a very slow OCR process. The timeout is set to 5 minutes, so you'd need to:

1. **Simulate slow OCR** (requires code modification):
   - Temporarily add a sleep in OCR processing
   - Upload a document
   - Wait 5+ minutes
   - **Expected**: Document times out and status set to "error" with timeout message

2. **Or verify timeout structure**:
   - Run the automated test script (already includes this)
   - **Expected**: Timeout mechanism exists and works

---

## Monitoring

### Watch for These Log Messages

**Watchdog**:
```
[WATCHDOG] Found X documents stuck in processing for >10 minutes
[WATCHDOG] Fixed X stuck document(s)
[WATCHDOG] Periodic check fixed X stuck document(s)
```

**Timeout**:
```
[OCR_TIMEOUT] OCR processing timed out after 300 seconds for doc_id=...
```

**Exception Handling**:
```
[OCR_V2] OCR pipeline execution failed: ...
[OCR_V2] Failed to update document status after error: ...
```

---

## Quick Verification Checklist

- [ ] Automated tests pass (`python test_stuck_100pct_fixes.py`)
- [ ] Watchdog endpoint works (`/api/watchdog/status`)
- [ ] Watchdog can fix stuck documents (`/api/watchdog/fix-stuck`)
- [ ] UI shows cards immediately after upload
- [ ] UI updates card status when OCR completes
- [ ] Error documents show error status in UI
- [ ] No documents remain stuck in "processing" indefinitely

---

## Troubleshooting

### Watchdog Not Running

Check startup logs for:
```
[STARTUP] Watchdog background task started
```

If missing, check `backend/main.py` startup event.

### Documents Still Stuck

1. Check watchdog is running: `GET /api/watchdog/status`
2. Manually fix: `POST /api/watchdog/fix-stuck`
3. Check logs for errors in watchdog task

### Timeout Not Working

1. Verify `OCR_PROCESSING_TIMEOUT_SECONDS = 300` in `ocr_service.py`
2. Check that `_run_with_timeout()` is called around `_process_with_v2_pipeline()`
3. Look for `[OCR_TIMEOUT]` in logs

---

**End of Testing Guide**

