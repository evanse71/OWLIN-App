# Fix: Port 5176 "Not Found" Error

## Problem
You're getting `{"detail":"Not Found"}` when accessing `http://localhost:5176/invoices`

## Root Cause
The **backend** is running on port 5176 instead of the **frontend**. The backend only has `/api/invoices`, not `/invoices`, so it returns 404.

## Solution

### Quick Fix (Recommended)
Run this single command to start everything correctly:
```batch
start_owlin_5176.bat
```

This will:
1. ✅ Stop any processes on ports 8000 and 5176
2. ✅ Start backend on port 8000
3. ✅ Start frontend on port 5176
4. ✅ Open browser to http://localhost:5176/invoices?dev=1

### Manual Fix

**Step 1: Stop the backend on port 5176**
```powershell
# Find and kill the process on port 5176
$proc = Get-NetTCPConnection -LocalPort 5176 -State Listen | Select-Object -ExpandProperty OwningProcess -Unique
Stop-Process -Id $proc -Force
```

**Step 2: Verify backend is on port 8000**
```powershell
# Check if backend is running on port 8000
curl http://localhost:8000/api/health
```

If not running, start it:
```batch
start_backend_8000.bat
```

**Step 3: Start frontend on port 5176**
```batch
start_frontend_5176.bat
```

Or manually:
```powershell
cd source_extracted\tmp_lovable
npm run dev
```

**Step 4: Access the application**
Open: http://localhost:5176/invoices?dev=1

## Verification

After fixing, verify:
- ✅ Backend: http://localhost:8000/api/health (should return JSON)
- ✅ Frontend: http://localhost:5176/invoices (should show React app, not JSON)
- ✅ API works: http://localhost:5176/api/invoices (should return invoice data)

## Why This Happened

You likely ran `start_backend_5176.bat` which starts the backend on port 5176. This is incorrect - the backend should always run on port 8000, and the frontend should run on port 5176.

**Correct setup:**
- Backend: Port 8000 (FastAPI/uvicorn)
- Frontend: Port 5176 (Vite dev server)
- Frontend proxies `/api/*` requests to backend on port 8000

