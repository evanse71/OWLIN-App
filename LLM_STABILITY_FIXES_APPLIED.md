# 🔧 LLM Stability Fixes Applied

## Problem Diagnosed

**Silent Fallback Detected:**
- LLM tried to run but **timed out** (30s was too short)
- System silently fell back to geometric extraction
- Result: "Unknown item" and impossible math persisted

## Fixes Applied

### 1. ✅ Increased Timeout (30s → 120s)

**Files Changed:**
- `backend/llm/invoice_parser.py` - Default timeout now 120s
- `backend/config.py` - Config default now 120s

**Why:** Local LLMs (Ollama) can take 30-90 seconds on first inference while loading model weights into memory. The 30s timeout was killing it prematurely.

### 2. ✅ LOUD Logging Added

**File:** `backend/llm/invoice_parser.py`

**Before:**
```python
LOGGER.warning(f"Ollama request timeout")  # Quiet
```

**After:**
```python
LOGGER.error(f"[LLM_PARSER] ✗ TIMEOUT after {self.timeout}s")
LOGGER.error(f"[LLM_PARSER] Timeout details: {str(e)}")  # With stack trace
```

**Why:** Silent failures are invisible. Now every failure screams in the logs.

### 3. ✅ Crash Instead of Silent Fallback

**File:** `backend/ocr/owlin_scan_pipeline.py`

**Before:**
```python
except Exception as e:
    LOGGER.error("Failed, using geometric...")  # Silent fallback
    use_llm_extraction = False
```

**After:**
```python
except Exception as e:
    LOGGER.error("[LLM_EXTRACTION] ✗ CRITICAL ERROR", exc_info=True)
    if FEATURE_LLM_EXTRACTION:
        raise  # CRASH to expose the error
```

**Why:** This is **temporary debug mode**. We need to see the EXACT error (timeout, connection, JSON parse, etc.) instead of silently falling back.

### 4. ✅ Enhanced Status Logging

**Added to logs:**
```
[LLM_EXTRACTION] ✓ LLM-first extraction ENABLED
[LLM_EXTRACTION] ✓ Model: qwen2.5-coder:7b
[LLM_EXTRACTION] ✓ Timeout: 120s
[LLM_EXTRACTION] ✓ Ollama URL: http://localhost:11434
[LLM_PARSER] Calling Ollama (attempt 1/3)...
[LLM_PARSER] SUCCESS - Response length: 1245 chars
[LLM_EXTRACTION] ✓ SUCCESS: 3 items, confidence=0.950
```

**Why:** Clear visibility into what's happening at each step.

## How to Test

### Step 1: Verify Ollama is Reachable

```bash
python verify_ollama_now.py
```

**Expected output:**
```
✓ Ollama is RUNNING
✓ Found 4 models
✓ Generation successful in 2.5s
✓ All tests PASSED
```

**If fails:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running, start it
ollama serve
```

### Step 2: Clear Cache

```bash
python clear_ocr_cache.py --all
```

**Why:** Remove old geometric results so system tries fresh.

### Step 3: Restart Backend

```bash
# Stop current backend (Ctrl+C)
.\start_backend_5176.bat
```

**Watch for these log lines on startup:**
```
[LLM_EXTRACTION] ✓ LLM-first extraction ENABLED
[LLM_EXTRACTION] ✓ Model: qwen2.5-coder:7b
[LLM_EXTRACTION] ✓ Timeout: 120s
```

### Step 4: Upload Invoice

Upload your test invoice and **watch the logs carefully**.

## What to Look For

### ✅ SUCCESS (You'll see):
```
[LLM_EXTRACTION] ⚡ Starting LLM reconstruction
[LLM_PARSER] Calling Ollama (attempt 1/3)...
[LLM_PARSER] Model: qwen2.5-coder:7b, Timeout: 120s
[LLM_PARSER] SUCCESS - Response length: 1245 chars
[LLM_EXTRACTION] ✓ SUCCESS: 3 items, confidence=0.950, time=2.50s
```

**Result in UI:** Real descriptions like "Crate of Beer"

### ❌ TIMEOUT (You'll see):
```
[LLM_PARSER] Calling Ollama (attempt 1/3)...
[LLM_PARSER] ✗ TIMEOUT after 120s (attempt 1/3)
[LLM_PARSER] Retrying in 1s...
[LLM_PARSER] ✗ FAILED after 3 attempts
[LLM_EXTRACTION] ✗ FAILED: LLM returned empty response
```

**Action:** Check if Ollama is under heavy load or model is too large.

### ❌ CONNECTION ERROR (You'll see):
```
[LLM_PARSER] ✗ CONNECTION ERROR (attempt 1/3)
[LLM_PARSER] Cannot reach Ollama at http://localhost:11434
```

**Action:** Ollama is not running. Run `ollama serve`.

### ❌ INVALID JSON (You'll see):
```
[LLM_EXTRACTION] ✗ FAILED: LLM returned invalid JSON
```

**Action:** Model prompt might need tuning or model is not suitable.

## Expected Processing Times

| Phase | Time |
|-------|------|
| First inference (cold start) | 30-90s |
| Subsequent inferences | 2-5s |
| With GPU | 1-3s |

**Note:** The 120s timeout handles even slow cold starts. Once the model is warm, it's much faster.

## Reverting Silent Fallback (After Debugging)

Once we confirm the LLM is working, we can **re-enable graceful fallback**:

**File:** `backend/ocr/owlin_scan_pipeline.py`

**Change from:**
```python
if FEATURE_LLM_EXTRACTION:
    raise  # Crash (debug mode)
```

**Back to:**
```python
# Mark for manual review (production mode)
table_data = {
    "method_used": "llm_failed",
    "needs_manual_review": True,
    "error": llm_result.error_message
}
```

But **first**, let's confirm it works!

## Summary of Changes

| File | Change | Reason |
|------|--------|--------|
| `backend/llm/invoice_parser.py` | Timeout 30s→120s | Prevent premature timeout |
| `backend/llm/invoice_parser.py` | Loud error logging | See exact failures |
| `backend/ocr/owlin_scan_pipeline.py` | Crash on LLM init fail | No silent fallback (temp) |
| `backend/ocr/owlin_scan_pipeline.py` | Crash on LLM extraction fail | See exact error (temp) |
| `backend/ocr/owlin_scan_pipeline.py` | Enhanced status logging | Visibility into each step |
| `backend/config.py` | Default timeout 120s | Config matches code |
| `verify_ollama_now.py` | NEW | Quick connectivity test |

## Next Steps

```bash
# 1. Test Ollama connectivity (30 seconds)
python verify_ollama_now.py

# 2. Clear cache (10 seconds)
python clear_ocr_cache.py --all

# 3. Restart backend (30 seconds)
# Stop with Ctrl+C, then:
.\start_backend_5176.bat

# 4. Upload invoice and watch logs (60 seconds)
# Look for [LLM_EXTRACTION] SUCCESS message
```

## Expected Outcome

**If Ollama was timing out:**
- ✅ Now works with 120s timeout
- ✅ Logs show clear success/failure
- ✅ "Unknown item" disappears

**If Ollama was disconnected:**
- ✅ Logs show CONNECTION ERROR clearly
- ✅ You fix by running `ollama serve`
- ✅ Retry and it works

**If model is wrong:**
- ✅ Logs show which model is being used
- ✅ You can change `LLM_MODEL_NAME` in config
- ✅ Retry with better model

---

**Status:** 🔧 Fixes Applied - Ready for Testing

**Action:** Run `python verify_ollama_now.py` RIGHT NOW to verify connectivity!

