# Code Assistant Mega Upgrade - Quick Start

## Installation (5 minutes)

### Step 1: Install qwen2.5-coder for 128k context

```powershell
ollama pull qwen2.5-coder:7b
```

Wait for download to complete (~4 GB).

### Step 2: Configure models (Optional)

Add to `env.local` or set environment variable:

```powershell
$env:OLLAMA_MODELS="qwen2.5-coder:7b,deepseek-coder:6.7b,codellama:7b"
```

If not set, system auto-detects all installed models.

### Step 3: Restart backend

```powershell
# Stop existing backend
Stop-Owlin.bat

# Start with new configuration
Start-Owlin-5176.ps1
```

### Step 4: Verify installation

```powershell
python test_mega_assistant.py
```

Should show:
```
✓ CODE ASSISTANT MEGA UPGRADE: OPERATIONAL
  - Model registry: Working
  - Configuration: Loaded
  - Quality tracking: Active
  - Chat system: Fully operational
```

## Usage

### In the UI

1. **Open Chat Assistant**
   - Click input box in top-right corner
   - Or expand from header

2. **Select Context Size**
   - NEW: 128k option for full codebase analysis
   - Dropdown in header: Small (10k) → Maximum (128k)

3. **Ask Debugging Question**
   - Example: "why did the upload succeed but not show invoice data?"
   - System will:
     - Auto-include 3-10 relevant files
     - Select best model (qwen2.5-coder for large context)
     - Analyze actual code
     - Provide file:line references
     - Never give generic advice

4. **See Model Info**
   - Header shows: "Using qwen2.5-coder:7b • 128k context"
   - Green = model active and working

### Example Questions That Now Work Perfectly

**Before:** Generic troubleshooting lists
**After:** Code-specific analysis with fixes

- "why did the upload succeed but not show supplier name?"
  → Analyzes upload.ts, shows exact issue at line 236, provides fix
  
- "how does the invoice card get populated with data?"
  → Traces flow from upload → OCR → database → Invoices.tsx
  
- "why are line items not showing?"
  → Shows normalizeUploadResponse function, identifies data mapping issue

## Monitoring

### Check Quality Metrics

Visit: `http://localhost:8000/api/chat/quality`

Shows:
- Generic response rate (should be < 5%)
- Code reference rate (should be > 95%)
- Files per request (should be > 3)
- Overall health score

### Check Available Models

Visit: `http://localhost:8000/api/chat/models`

Shows:
- All installed models
- Context window sizes
- Model specialties
- File sizes

### Check Configuration

Visit: `http://localhost:8000/api/chat/config`

Shows:
- Current model configuration
- Registry stats
- Feature flags

## Troubleshooting

### "No models available"
Run `ollama list` to check installed models.
Install at least one code model:
```powershell
ollama pull qwen2.5-coder:7b
# or
ollama pull deepseek-coder:6.7b
```

### "Generic responses still appearing"
1. Check `/api/chat/quality` for metrics
2. Verify Ollama is running: `ollama serve`
3. Check backend logs for validation details
4. System will auto-retry with stricter prompt

### "Context size too large"
- 128k requires qwen2.5-coder:7b or llama3.2
- System auto-caps to model's max
- Check `/api/chat/config` for max_context_available

## Advanced Configuration

### Prioritize Different Models

```powershell
# Prefer speed over context
$env:OLLAMA_MODELS="llama3.2:3b,deepseek-coder:6.7b,qwen2.5-coder:7b"

# Prefer context over speed  
$env:OLLAMA_MODELS="qwen2.5-coder:7b,deepseek-coder:6.7b"
```

### Adjust Quality Thresholds

Edit `backend/services/chat_metrics.py`:
```python
"generic_response_rate": {
    "threshold": 2.0,  # Even stricter (was 5.0)
    # ...
}
```

## Testing

### Run Integration Tests

```powershell
pytest tests/integration/test_chat_assistant_mega.py -v
```

### Manual Test

1. Ask: "why did the upload succeed but not show invoice data?"
2. Verify response includes:
   - File names (upload.ts, Invoices.tsx, main.py)
   - Line numbers (file.ts:236, etc.)
   - Code snippets
   - Specific root cause
   - Exact fix with BEFORE/AFTER

3. Check logs for:
   - `Selected model: qwen2.5-coder:7b`
   - `Auto-included X files for debugging`
   - `Response validation passed`

## What You Get

### Guaranteed for Debugging Questions:
- ✅ 3-10 code files auto-included
- ✅ Specific file:line references
- ✅ Data flow tracing
- ✅ Root cause identification
- ✅ Exact code fixes
- ✅ No generic troubleshooting

### Multi-Model Intelligence:
- Large context (64k-128k) → uses qwen2.5-coder
- Fast analysis (16k-32k) → uses deepseek-coder
- Fallback chain → tries all models before giving up
- Even without LLM → shows actual code

### Quality Tracking:
- Every request logged
- Quality metrics calculated
- Pass/fail thresholds
- Performance monitoring

## Success Indicators

When working correctly, you'll see:
- ✅ Green "Using qwen2.5-coder:7b" in chat header
- ✅ Responses reference 2+ files with line numbers
- ✅ Data flow traced through actual code
- ✅ Specific fixes provided
- ✅ No numbered generic troubleshooting lists

## Summary

The code assistant is now **mega-powered** and will:
1. Auto-detect which files to analyze (3-10 files)
2. Select the best model for your question
3. Analyze actual code with line numbers
4. Trace data flow through files
5. Provide specific fixes
6. Fall back gracefully if models fail
7. Track quality metrics

**No more generic advice. Only code-specific analysis.**

Ready to test! Ask it anything about your code.

