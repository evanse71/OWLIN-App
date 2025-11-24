# Fix: Backend 500 Error on Health Check

## Problem
Frontend shows: "Backend: Unreachable (Health check failed: 500 Internal Server Error)"

## Solution

### Step 1: Make sure backend is running
```powershell
.\Test-Backend.ps1
```

If backend is not running, start it:
```powershell
.\start_backend_8000.bat
```

You should see in the backend window:
```
INFO: Uvicorn running on http://0.0.0.0:8000
```

### Step 2: Test the health endpoint
Open a new PowerShell window and run:
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/health"
```

You should see:
```json
{"status":"ok","ocr_v2_enabled":true,"request_id":"..."}
```

### Step 3: Start everything together
```powershell
.\Start-Owlin-5176.ps1
```

This will:
1. Start backend on port 8000
2. Wait for backend to be ready (up to 45 seconds)
3. Start frontend on port 5176
4. Open browser to http://localhost:5176/invoices?dev=1

### Step 4: Verify
- Backend window should show: "INFO: Uvicorn running on http://0.0.0.0:8000"
- Frontend window should show: "VITE v..." and "Local: http://localhost:5176"
- Browser should show: "Backend: Healthy ✅" (green)

## Troubleshooting

### If backend still shows 500 error:
1. Check backend window for error messages
2. Check `backend_stdout.log` for errors
3. Try restarting backend: Close backend window, then run `.\start_backend_8000.bat`

### If backend won't start:
1. Make sure virtual environment is activated
2. Check if port 8000 is in use: `netstat -an | findstr :8000`
3. Kill any processes on port 8000: `Get-NetTCPConnection -LocalPort 8000 | Stop-Process -Id {OwningProcess}`

### If frontend can't reach backend:
1. Make sure backend is running (check backend window)
2. Check firewall isn't blocking port 8000
3. Try accessing http://localhost:8000/api/health directly in browser

## What was fixed:
- Health endpoint now handles errors gracefully
- Audit logging failures won't crash the health check
- Better error messages in logs

