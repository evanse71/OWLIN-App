# Fix: /invoices endpoint returning 404

## Current Status
✅ Code has been updated - the `/invoices` route is now defined at line 367 in `backend/main.py`
❌ Backend needs to be **manually restarted** to apply the changes

## The Problem
The `/invoices` endpoint returns `{"detail":"Not Found"}` because the backend is still running the old code without this route.

## The Solution

### Step 1: Stop the Backend
1. Find the backend window (the one running on port 5176)
2. Press `Ctrl+C` to stop it
3. Wait for it to fully stop

### Step 2: Restart the Backend
Run this command:
```batch
start_backend_5176.bat
```

Or use PowerShell:
```powershell
.\start_backend_5176.bat
```

### Step 3: Verify It Works
After the backend starts (wait 5-10 seconds), test the endpoint:
```powershell
curl http://localhost:5176/invoices
```

You should see JSON data with invoices, not `{"detail":"Not Found"}`.

## What Was Changed
- Added a `/invoices` route handler at line 367 in `backend/main.py`
- This route calls the same function as `/api/invoices`
- Both `/invoices` and `/api/invoices` now work identically

## Why Auto-Reload Didn't Work
The uvicorn `--reload` feature sometimes doesn't catch route additions properly. A manual restart ensures the new route is registered.

## Alternative (No Restart Needed)
If you don't want to restart, you can use the existing endpoint:
- Use `http://localhost:5176/api/invoices` instead of `http://localhost:5176/invoices`
- This endpoint already works and doesn't require any changes

