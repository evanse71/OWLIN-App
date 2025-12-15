# Quick Start Guide - Launch Localhost for Testing

## The Problem
You're getting `ERR_CONNECTION_REFUSED` on http://localhost:5176 because the servers aren't running.

## Solution: Start Both Servers

### Option 1: Use the Batch File (Easiest)
1. **Double-click `START_BOTH_SERVERS.bat`** in the project root
2. Two command windows will open:
   - One for the Backend (port 8000)
   - One for the Frontend (port 5176)
3. Wait 15-30 seconds for both servers to start
4. Open your browser to: **http://localhost:5176**

### Option 2: Manual Start (If batch file doesn't work)

#### Start Backend (Terminal 1):
```batch
cd c:\Users\tedev\FixPack_2025-11-02_133105
.venv311\Scripts\activate.bat
set OWLIN_ENV=dev
set FEATURE_OCR_PIPELINE_V2=true
set PYTHONPATH=%CD%
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Wait for: `INFO:     Uvicorn running on http://127.0.0.1:8000`

#### Start Frontend (Terminal 2):
```batch
cd c:\Users\tedev\FixPack_2025-11-02_133105\frontend_clean
npm run dev
```

Wait for: `Local: http://localhost:5176/`

### Option 3: Use PowerShell Script
```powershell
powershell -ExecutionPolicy Bypass -File .\START_SERVERS.ps1
```

## Verify Servers Are Running

### Check Backend:
Open browser to: http://localhost:8000/health
- Should return JSON response

### Check Frontend:
Open browser to: http://localhost:5176
- Should show the Owlin application

## Troubleshooting

### Port Already in Use
If you get "port already in use" errors:
```batch
REM Find process using port 8000
netstat -ano | findstr :8000

REM Find process using port 5176
netstat -ano | findstr :5176

REM Kill the process (replace <PID> with the number from above)
taskkill /PID <PID> /F
```

### Backend Won't Start
1. Check virtual environment exists: `.venv311\Scripts\python.exe`
2. Verify dependencies: `pip list | findstr uvicorn`
3. Check for errors in the backend window

### Frontend Won't Start
1. Install dependencies: `cd frontend_clean && npm install`
2. Check Node.js is installed: `node --version`
3. Check for errors in the frontend window

### Still Getting Connection Refused
1. Make sure BOTH servers are running (check both windows)
2. Wait longer - backend can take 30+ seconds to start (OCR engines loading)
3. Check Windows Firewall isn't blocking the ports
4. Try accessing http://127.0.0.1:5176 instead of localhost:5176

## Expected Behavior

Once both servers are running:
- **Backend**: http://localhost:8000 (API server)
- **Frontend**: http://localhost:5176 (Web application)
- Frontend proxies API requests to backend automatically
- You should see the Owlin invoice management interface

## Quick Test Commands

```batch
REM Test backend
curl http://localhost:8000/health

REM Test frontend
curl http://localhost:5176

REM Check what's listening on ports
netstat -ano | findstr ":8000 :5176"
```
