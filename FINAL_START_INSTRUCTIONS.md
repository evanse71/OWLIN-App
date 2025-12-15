# Final Backend Start Instructions

## The Problem
The backend keeps timing out. This usually means it's hanging during startup.

## Solution: Start in Current Terminal

**IMPORTANT:** Run the backend in the SAME terminal window so you can see error messages!

### Step 1: Make sure you're in the project directory
```powershell
cd c:\Users\tedev\FixPack_2025-11-02_133105
```

### Step 2: Activate virtual environment
```powershell
.\.venv\Scripts\Activate.ps1
```

### Step 3: Set environment variables
```powershell
$env:OWLIN_ENV="dev"
$env:FEATURE_OCR_PIPELINE_V2="true"
$env:PYTHONPATH="c:\Users\tedev\FixPack_2025-11-02_133105"
$env:PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION="python"
```

### Step 4: Start backend (in THIS terminal - don't open a new window!)
```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --log-level info
```

**Keep this terminal window open!** The backend runs here.

### Step 5: Watch for these messages
You should see:
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Step 6: Test in a NEW terminal
Open a NEW PowerShell window and run:
```powershell
python check_backend.py
```

## Alternative: Use the Batch File

Or simply double-click:
- `START_BACKEND_DIRECT.bat`

This will show you all the output in the same window.

## If It Still Hangs

Look at the LAST message before it hangs. Common issues:
- Database lock - check if another process has the DB open
- Import error - look for Python import errors
- OCR engine loading - PaddleOCR can take 30+ seconds to load

## Once Running

- Backend: http://localhost:8000
- Frontend: http://localhost:5176 (should now connect!)
- Upload documents via the web interface
