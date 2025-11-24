# Quick Start Guide - Port 5176

## 🚀 Fastest Way to Start

**Run this single command:**
```bash
START_OWLIN_5176.bat
```

This will:
1. ✅ Kill any processes using ports 8000 or 5176
2. ✅ Start backend on port 8000
3. ✅ Wait for backend to be ready
4. ✅ Start frontend on port 5176
5. ✅ Wait for frontend to be ready
6. ✅ Open browser to http://localhost:5176/invoices?dev=1

## 📋 Manual Steps (if automated script fails)

### Step 1: Start Backend
```bash
start_backend_8000.bat
```
Wait until you see: `Uvicorn running on http://0.0.0.0:8000`

### Step 2: Start Frontend (in a NEW terminal)
```bash
start_frontend_5176.bat
```
Wait until you see: `Local: http://localhost:5176/`

### Step 3: Open Browser
Go to: **http://localhost:5176/invoices?dev=1**

## 🔍 Troubleshooting

### "ERR_CONNECTION_REFUSED" Error

**Check if services are running:**
```bash
check_ports.bat
```

**Common fixes:**

1. **Port 5176 is blocked:**
   - Run `check_ports.bat` to see what's using the port
   - Kill the process: `taskkill /IM node.exe /F`

2. **Frontend not starting:**
   - Check if `node_modules` exists in `source_extracted/tmp_lovable`
   - If not, run: `cd source_extracted/tmp_lovable && npm install`

3. **Backend not starting:**
   - Check if `.venv` exists
   - Check backend window for Python errors
   - Verify database exists: `data/owlin.db`

4. **Both services running but can't connect:**
   - Check Windows Firewall isn't blocking ports
   - Try `http://127.0.0.1:5176/invoices?dev=1` instead of `localhost`

## ✅ Verify Everything Works

1. **Backend Health:** http://localhost:8000/api/health
   - Should return: `{"status":"ok",...}`

2. **Frontend:** http://localhost:5176/invoices?dev=1
   - Should show invoices page
   - Should show "Backend is online" banner (green)

3. **Upload Test:**
   - Click "Upload" button
   - Select a PDF invoice
   - Should see card appear with extracted data

## 📝 Configuration

- **Backend Port:** 8000 (configured in `start_backend_8000.bat`)
- **Frontend Port:** 5176 (configured in `vite.config.ts` and `package.json`)
- **API Base URL:** http://127.0.0.1:8000 (set in frontend startup scripts)

## 🆘 Still Having Issues?

1. Check both terminal windows for error messages
2. Run `check_ports.bat` to verify ports
3. Make sure you're in the project root directory
4. Verify virtual environment is activated (backend window should show `(.venv)`)
5. Verify Node.js is installed: `node --version`
6. Verify Python is installed: `python --version`

