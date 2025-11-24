# Fix: /invoices endpoint returning 404

## Problem
Getting `{"detail":"Not Found"}` when accessing `http://localhost:5176/invoices`

## Solution
The backend code has been updated to add a `/invoices` route that aliases to `/api/invoices`. You need to **restart the backend** for the changes to take effect.

## Steps to Fix

### Option 1: Quick Restart (Recommended)
1. Find the backend window running on port 5176
2. Press `Ctrl+C` to stop it
3. Run `start_backend_5176.bat` again

### Option 2: Kill and Restart
```powershell
# Kill the backend process
$proc = Get-NetTCPConnection -LocalPort 5176 -State Listen | Select-Object -ExpandProperty OwningProcess -Unique
Stop-Process -Id $proc -Force

# Wait a moment
Start-Sleep -Seconds 2

# Restart the backend
.\start_backend_5176.bat
```

## Verify the Fix
After restarting, test the endpoint:
```powershell
curl http://localhost:5176/invoices
```

You should see JSON data with invoices, not `{"detail":"Not Found"}`.

## What Was Changed
- Added `/invoices` route that directly calls the same function as `/api/invoices`
- The route is defined at line 367 in `backend/main.py`
- Both `/invoices` and `/api/invoices` now work identically

## Alternative
If you don't want to restart, you can use the existing endpoint:
- Use `http://localhost:5176/api/invoices` instead of `http://localhost:5176/invoices`

