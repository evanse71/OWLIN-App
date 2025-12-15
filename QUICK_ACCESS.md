# Quick Access Guide

## ✅ Current Status

- **Backend**: Running on port 8000 ✅
- **Frontend Dev Server**: Not running (port 5176) ❌

## 🚀 Access the App

### Option 1: Via Backend (Recommended - No Vite needed)

The backend is already serving the built frontend from `backend/static/`.

**Open in browser:**
```
http://localhost:8000/
```

**Or go directly to invoices:**
```
http://localhost:8000/invoices?dev=1
```

This should work immediately if the static files are built.

### Option 2: Via Vite Dev Server (For Development)

If you want hot-reload during development:

1. **Open a new PowerShell window:**
   ```powershell
   cd "C:\Users\tedev\FixPack_2025-11-02_133105\frontend_clean"
   npm run dev -- --port 5176
   ```

2. **Wait for:**
   ```
   VITE v7.2.1  ready in XXX ms
   ➜  Local:   http://localhost:5176/
   ```

3. **Open in browser:**
   ```
   http://localhost:5176/
   ```

## 🔍 Troubleshooting

### If `http://localhost:8000/` shows a blank page or error:

1. **Check if static files exist:**
   ```powershell
   Test-Path "backend\static\index.html"
   ```

2. **If files don't exist, build the frontend:**
   ```powershell
   cd frontend_clean
   npm run build
   ```

3. **Check browser console (F12) for errors**

### If you get connection refused on 5176:

- The Vite dev server is not running
- Start it with: `npm run dev -- --port 5176` in the `frontend_clean` directory
- **Keep the terminal window open** - closing it stops the server

## 📋 Quick Verification

Run this to check everything:
```batch
.\VERIFY_SETUP.bat
```

