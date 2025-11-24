# Fixed: Port Configuration Issue

## The Problem
You were getting `{"detail":"Not Found"}` when accessing `http://localhost:5176/invoices` because:
- ❌ Backend was running on port 5176 (wrong port)
- ❌ Frontend wasn't running
- ❌ The `/invoices` route is a **frontend route** (React Router), not a backend API route

## The Solution
**Correct Architecture:**
- ✅ Backend: Port 8000 (FastAPI)
- ✅ Frontend: Port 5176 (Vite dev server)
- ✅ Frontend proxies `/api/*` requests to backend on port 8000

## What Was Fixed
1. ✅ Stopped backend on port 5176
2. ✅ Started backend on port 8000
3. ✅ Started frontend on port 5176

## How It Works Now

### Backend (Port 8000)
- Handles all `/api/*` endpoints
- Example: `http://localhost:8000/api/invoices` ✅

### Frontend (Port 5176)
- Serves the React application
- Handles frontend routes like `/invoices`, `/dashboard`, etc.
- Proxies `/api/*` requests to backend on port 8000
- Example: `http://localhost:5176/invoices` → Shows React app ✅
- Example: `http://localhost:5176/api/invoices` → Proxied to backend ✅

## Access Your Application

**Open in browser:**
```
http://localhost:5176/invoices
```

This will:
1. Load the React frontend (handled by Vite on port 5176)
2. React Router will show the Invoices page
3. Frontend will make API calls to `/api/invoices`
4. Vite proxy will forward those to `http://localhost:8000/api/invoices`
5. Backend will return the data
6. Frontend will display it

## Verification

Check that everything is running:
```powershell
# Backend health
curl http://localhost:8000/api/health

# Frontend (should return HTML)
curl http://localhost:5176

# API through frontend proxy
curl http://localhost:5176/api/invoices
```

## If Services Aren't Running

**Start backend on port 8000:**
```batch
start_backend_8000.bat
```

**Start frontend on port 5176:**
```batch
start_frontend_5176.bat
```

Or use the combined script:
```batch
start_owlin_5176.bat
```

## Summary

The `/invoices` route is a **frontend route** handled by React Router, not a backend API route. The frontend dev server (Vite) on port 5176 serves the React app and handles all frontend routes. The backend on port 8000 only handles `/api/*` endpoints.

✅ **Everything should work now!**

