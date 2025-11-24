# Fix Connection Issue - Port 5176

## The Problem
You're getting `ERR_CONNECTION_REFUSED` when trying to access `http://localhost:5176/invoices?dev=1`

## Quick Fix Steps

### Step 1: Stop Everything
In PowerShell, run:
```powershell
Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force
```

### Step 2: Test Current Status
```powershell
.\Test-Connection.ps1
```

### Step 3: Start Backend First
```powershell
# Option A: Use the batch file (in cmd, not PowerShell)
cmd /c start_backend_8000.bat

# Option B: Start manually
.venv\Scripts\activate
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Wait until you see: `Uvicorn running on http://0.0.0.0:8000`

### Step 4: Start Frontend (in a NEW terminal)
```powershell
cd source_extracted\tmp_lovable
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000"
npm run dev
```

Wait until you see: `Local: http://localhost:5176/`

### Step 5: Open Browser
Go to: **http://127.0.0.1:5176/invoices?dev=1**

(Use `127.0.0.1` instead of `localhost` if `localhost` doesn't work)

## Alternative: Use PowerShell Script

Run this single command:
```powershell
.\Start-Owlin-5176.ps1
```

Or use the interactive menu:
```powershell
.\START_HERE.ps1
```

## If Still Not Working

1. **Check Windows Firewall:**
   - Windows might be blocking the ports
   - Try temporarily disabling firewall to test

2. **Check if ports are actually listening:**
   ```powershell
   Get-NetTCPConnection -LocalPort 5176
   Get-NetTCPConnection -LocalPort 8000
   ```

3. **Check the frontend terminal window:**
   - Look for error messages
   - Make sure it says "Local: http://localhost:5176/" or similar

4. **Try different URLs:**
   - http://127.0.0.1:5176/invoices?dev=1
   - http://localhost:5176/invoices?dev=1
   - http://[::1]:5176/invoices?dev=1

5. **Check browser console:**
   - Press F12 in browser
   - Look for errors in Console tab
   - Check Network tab to see if requests are being made

## Common Issues

### "Port already in use"
```powershell
# Kill the process
Get-Process -Name node | Stop-Process -Force
```

### "Cannot find module"
```powershell
cd source_extracted\tmp_lovable
npm install
```

### "Backend is offline" banner
- Wait 10-15 seconds after starting backend
- Check backend window for errors
- Verify backend is on port 8000: http://localhost:8000/api/health

