# Fix: Backend Routes Not Loading

## Issue
The new endpoints (`/api/chat/config`, `/api/chat/models`, `/api/chat/metrics`, `/api/chat/quality`) are returning 404 even though they're defined in the code.

## Root Cause
The backend process is running old code that was loaded before the new routes were added. The routes ARE in the code file, but the running Python process hasn't reloaded them.

## Solution

### Option 1: Full Restart (Recommended)

1. **Stop all backend processes:**
   ```powershell
   # Kill all Python processes
   Get-Process python* | Stop-Process -Force
   
   # Or kill specific port
   Get-NetTCPConnection -LocalPort 8000 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
   ```

2. **Clear Python cache:**
   ```powershell
   Get-ChildItem -Path backend -Recurse -Filter "*.pyc" | Remove-Item -Force
   Get-ChildItem -Path backend -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
   ```

3. **Start backend fresh:**
   ```powershell
   cd backend
   python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Wait 5 seconds, then test:**
   ```powershell
   python test_mega_assistant.py
   ```

### Option 2: Use Your Existing Start Script

If you have a start script that manages both frontend and backend:

```powershell
# Stop everything
.\stop_owlin.bat  # or whatever your stop script is

# Start fresh
.\Start-Owlin-5176.ps1
```

### Verification

After restarting, these endpoints should work:
- `GET http://localhost:8000/api/chat/config` ✅
- `GET http://localhost:8000/api/chat/models` ✅  
- `GET http://localhost:8000/api/chat/metrics` ✅
- `GET http://localhost:8000/api/chat/quality` ✅

### Quick Test

```powershell
# Test one endpoint
curl http://localhost:8000/api/chat/config

# Should return JSON with models, features, etc.
# NOT: {"detail":"Not Found"}
```

## Why This Happens

Python caches imported modules. When you:
1. Start backend → loads `chat_router.py` (old version with 3 routes)
2. Add new routes to `chat_router.py`
3. Backend is still running → still has old code in memory

Even with `--reload`, uvicorn sometimes doesn't detect route additions properly.

## Confirmation

The routes ARE in the code:
```python
# backend/routes/chat_router.py has:
@router.get("/config")      # Line 231
@router.get("/models")      # Line 264  
@router.get("/metrics")     # Line 297
@router.get("/quality")     # Line 311
```

Once the backend restarts with fresh code, all 7 routes will be available:
- `/api/chat` (POST)
- `/api/chat/status` (GET)
- `/api/chat/diagnose` (GET)
- `/api/chat/config` (GET) ← NEW
- `/api/chat/models` (GET) ← NEW
- `/api/chat/metrics` (GET) ← NEW
- `/api/chat/quality` (GET) ← NEW

