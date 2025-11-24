# Dev Debug Assistant - Quick Start

## What Is It?

An **offline debugging assistant** built into Owlin that:
- 🔍 Scans your code for issues (no internet needed)
- 🤖 Explains errors in plain English
- 🎯 Generates ready-to-copy Cursor prompts
- 💰 **Saves Cursor credits** by moving "find the bug" work offline

## 2-Minute Setup

### Install Tools

```powershell
# Python linting tools
pip install mypy ruff pytest

# Frontend tools (if not already installed)
cd frontend_clean
npm install
```

### Optional: Install Ollama for AI Explanations

```powershell
# Download from: https://ollama.com/download/windows
# Then pull the model:
ollama pull codellama:7b
```

> **Note**: Works without Ollama using template fallbacks!

## How to Use

### Step 1: Start Owlin

```powershell
# Terminal 1: Backend
uvicorn backend.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend_clean
npm run dev
```

### Step 2: Open Debug Assistant

Navigate to: `http://localhost:5173/dev/debug`

### Step 3: Find & Fix Issues

1. Click **"🔍 Run Checks"** (scans your code)
2. Select an issue from the left panel
3. (Optional) Paste code context for better AI explanations
4. Click **"🤖 Generate Explanation"**
5. Copy the **Cursor Prompt** and paste in Cursor
6. Let Cursor fix it!

## What Gets Checked?

### Backend (Python)
- ✅ **MyPy**: Type errors
- ✅ **Ruff**: Code style/quality
- ✅ **Pytest**: Syntax validation

### Frontend (TypeScript)
- ✅ **tsc**: Type errors
- ✅ **ESLint**: Code style/quality

## Example Workflow

```
1. Run checks → Found: "Type 'str' cannot be assigned to 'int'"
2. Select issue → See error in services/ocr_service.py:42
3. Paste code → Add 30 lines around the error
4. Get explanation:
   📖 Plain English: "You're assigning text to a number variable"
   🔧 Technical: "Type mismatch at line 42"
   ✅ Fix: "Use correct type annotation"
   🎯 Cursor Prompt: "Fix type error at line 42 in backend/services/ocr_service.py"
5. Copy & paste → Cursor fixes it!
```

## Verify Installation

```powershell
# Run this test script:
.\scripts\test_dev_assistant.ps1
```

Should show ✓ for all required tools.

## Troubleshooting

### "No issues found" but I know there are errors
- Check tools are installed: `mypy --version`, `ruff --version`
- Ensure you're in the repo root directory

### "Explanation failed"
- Check if Ollama is running (optional)
- System auto-falls back to templates if Ollama unavailable
- Check backend logs: `backend_stdout.log`

### "Backend not accessible"
- Start backend: `uvicorn backend.main:app --reload --port 8000`
- Verify: `curl http://localhost:8000/api/dev/status`

## Tips for Best Results

✅ **DO**:
- Provide code context (30-60 lines) for better explanations
- Fix errors before warnings
- Use the generated Cursor prompts directly

❌ **DON'T**:
- Expect it to auto-fix code (it only suggests fixes)
- Run on every save (manual trigger only)

## Architecture at a Glance

```
Backend:
  backend/devtools/
    ├── models.py          → Data structures
    ├── runner.py          → Runs linting tools
    ├── llm_explainer.py   → Generates explanations
  backend/routes/
    └── dev_tools.py       → API endpoints

Frontend:
  frontend_clean/src/pages/
    └── DevDebug.tsx       → UI

Endpoints:
  GET  /api/dev/run_checks     → Scan code
  POST /api/dev/llm/explain    → Explain issue
  GET  /api/dev/status         → System status
```

## Next Steps

- Read full docs: `DEV_DEBUG_ASSISTANT_README.md`
- Run test script: `.\scripts\test_dev_assistant.ps1`
- Open UI: `http://localhost:5173/dev/debug`

---

**Built to save credits and speed up debugging! 🚀**

