# Dev Debug Assistant - Integration Checklist

Use this checklist to verify the Dev Debug Assistant is properly integrated into your Owlin installation.

## 📋 File Verification

### Backend Files

- [ ] `backend/devtools/__init__.py` exists
- [ ] `backend/devtools/models.py` exists
- [ ] `backend/devtools/runner.py` exists
- [ ] `backend/devtools/llm_explainer.py` exists
- [ ] `backend/routes/dev_tools.py` exists
- [ ] `backend/main.py` includes dev_tools router (line ~113)

### Frontend Files

- [ ] `frontend_clean/src/pages/DevDebug.tsx` exists
- [ ] `frontend_clean/src/App.tsx` imports DevDebug
- [ ] `frontend_clean/src/App.tsx` has `/dev/debug` route

### Documentation Files

- [ ] `DEV_DEBUG_ASSISTANT_README.md` exists
- [ ] `DEV_DEBUG_QUICK_START.md` exists
- [ ] `DEV_DEBUG_IMPLEMENTATION_SUMMARY.md` exists
- [ ] `scripts/test_dev_assistant.ps1` exists

## 🔧 Dependency Check

### Python Tools (Backend)

Run these commands to verify:

```powershell
# Check MyPy
mypy --version
# Expected: mypy 1.x.x

# Check Ruff
ruff --version
# Expected: ruff 0.x.x

# Check Pytest
pytest --version
# Expected: pytest 7.x.x or 8.x.x
```

Installation command if missing:
```powershell
pip install mypy ruff pytest
```

### Node Tools (Frontend)

Run these commands to verify:

```powershell
cd frontend_clean

# Check TypeScript
npx tsc --version
# Expected: Version 5.x.x

# Check ESLint
npx eslint --version
# Expected: v8.x.x or v9.x.x
```

Installation command if missing:
```powershell
npm install
```

### Optional: Ollama

Check if running:
```powershell
curl http://localhost:11434/api/tags
```

If not installed, download from: https://ollama.com/download

Pull model:
```powershell
ollama pull codellama:7b
```

## 🚀 Runtime Verification

### 1. Start Backend

```powershell
# From repo root
uvicorn backend.main:app --reload --port 8000
```

Expected output should include:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 2. Test Backend Endpoints

```powershell
# Test health endpoint
curl http://localhost:8000/api/health

# Test dev tools status
curl http://localhost:8000/api/dev/status
```

Expected responses:
- `/api/health` → `{"status":"ok", ...}`
- `/api/dev/status` → `{"status":"ok", "ollama_available": ..., ...}`

### 3. Start Frontend

```powershell
cd frontend_clean
npm run dev
```

Expected output should include:
```
VITE ready in X ms
Local: http://localhost:5173/
```

### 4. Access UI

Open browser to: `http://localhost:5173/dev/debug`

Expected:
- Page loads without errors
- Header shows "Dev Debug Assistant"
- "Run Checks" button is visible
- Layout shows two columns (issues list and explanation panel)

## 🧪 Functional Tests

### Test 1: Run Checks

1. Click "Run Checks" button
2. Wait for completion (10-30 seconds)
3. Verify issues appear in left panel (or "No issues found")
4. Check stats bar shows counts by severity and tool

**Expected:**
- Button shows "🔄 Running Checks..." during execution
- Issues populate left panel when complete
- Stats bar updates with counts

### Test 2: Select Issue

1. Click on any issue in the list
2. Verify right panel updates
3. Check issue details are displayed

**Expected:**
- Selected issue has blue highlight
- Right panel shows issue details
- Code context textarea is visible

### Test 3: Generate Explanation

1. (Optional) Paste code context in textarea
2. Click "Generate Explanation & Patch Suggestion"
3. Wait for response (2-5 seconds)
4. Verify explanation appears

**Expected:**
- Button shows "⏳ Generating..." during processing
- Four colored cards appear:
  - Blue: Plain English explanation
  - Purple: Technical cause
  - Green: Suggested fix
  - Orange: Cursor prompt
- Confidence and method shown at bottom

### Test 4: Copy Cursor Prompt

1. Click "📋 Copy" button on Cursor prompt
2. Verify button changes to "✓ Copied!"
3. Paste in a text editor to verify clipboard

**Expected:**
- Button text changes temporarily
- Prompt is in clipboard
- Format is ready for Cursor AI

## 🔍 Linting Verification

Run these commands to ensure no errors were introduced:

### Backend Linting

```powershell
# From repo root
mypy backend/devtools
ruff check backend/devtools backend/routes/dev_tools.py
```

Expected: No errors

### Frontend Linting

```powershell
cd frontend_clean
npx tsc --noEmit
npx eslint src/pages/DevDebug.tsx src/App.tsx
```

Expected: No errors

## 📊 Performance Tests

### Backend Performance

Run checks endpoint and measure time:

```powershell
Measure-Command {
    Invoke-RestMethod -Uri "http://localhost:8000/api/dev/run_checks"
}
```

Expected: 10-30 seconds for first run, 5-15 seconds for subsequent runs

### Frontend Performance

1. Open browser DevTools (F12)
2. Go to Network tab
3. Click "Run Checks"
4. Check request timing

Expected:
- API request completes in 10-30 seconds
- UI remains responsive during request
- No console errors

## ✅ Final Checklist

Mark each as complete:

- [ ] All files exist in correct locations
- [ ] Backend starts without errors
- [ ] Frontend starts without errors
- [ ] Can access `/dev/debug` page
- [ ] "Run Checks" button works
- [ ] Issues display in left panel
- [ ] Can select an issue
- [ ] "Generate Explanation" button works
- [ ] Explanations display correctly
- [ ] "Copy Cursor Prompt" works
- [ ] No linting errors in new files
- [ ] No console errors in browser
- [ ] No backend errors in logs
- [ ] Documentation files are accessible
- [ ] Test script runs successfully

## 🆘 Troubleshooting

### Issue: Backend won't start

**Check:**
```powershell
# Verify import works
python -c "from backend.routes.dev_tools import router; print('OK')"
```

**Solution:** If import fails, check for syntax errors in new files

### Issue: Frontend build fails

**Check:**
```powershell
cd frontend_clean
npx tsc --noEmit
```

**Solution:** Fix any TypeScript errors shown

### Issue: API returns 404

**Check:**
```powershell
curl http://localhost:8000/docs
```

**Solution:** Verify dev_tools router is included in main.py

### Issue: "No issues found" but I know there are errors

**Check:**
```powershell
# Manually run a tool
mypy backend --ignore-missing-imports
```

**Solution:** Ensure tools are installed and working independently

## 🎓 Quick Reference

**Access UI:** `http://localhost:5173/dev/debug`

**API Endpoints:**
- `GET /api/dev/run_checks` - Run code quality checks
- `POST /api/dev/llm/explain` - Generate explanation
- `GET /api/dev/status` - System status

**Key Files:**
- Backend: `backend/devtools/` and `backend/routes/dev_tools.py`
- Frontend: `frontend_clean/src/pages/DevDebug.tsx`
- Docs: `DEV_DEBUG_*.md` files

**Test Script:** `.\scripts\test_dev_assistant.ps1`

---

**When all items are checked, integration is complete! ✅**

