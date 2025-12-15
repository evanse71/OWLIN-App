# Quick Start Backend - Step by Step

## The Problem
The backend is timing out when trying to start. This usually means it's hanging during startup.

## Solution: Run These Commands

Open PowerShell in the project directory and run:

### Step 1: Kill any stuck processes
```powershell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
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

### Step 4: Start backend (in the SAME terminal)
```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

**IMPORTANT:** Keep this terminal window open! The backend runs in this window.

### Step 5: Wait for startup
Look for this message in the terminal:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Step 6: Test in a NEW terminal
Open a NEW PowerShell window and run:
```powershell
python check_backend.py
```

## Alternative: Use the Script

Or simply run:
```powershell
.\start_backend_simple.ps1
```

## Troubleshooting

### If it hangs during startup:
1. Check the terminal window for error messages
2. Look for import errors or missing modules
3. Check if database is locked
4. Try starting without reload: `--reload` → remove this flag

### If port 8000 is still in use:
```powershell
netstat -ano | findstr ":8000"
# Note the PID, then:
taskkill /PID <PID> /F
```

### If you see import errors:
```powershell
pip install -r requirements.txt
```

## Once Running

- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:5176 (should now connect!)
