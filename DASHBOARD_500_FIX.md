# 🚨 Dashboard 500 Error - Surgical Fix Guide

## Problem
The Dashboard route (`http://127.0.0.1:3000/dashboard`) is returning a 500 error due to SSR (Server-Side Rendering) issues with our centralized config and missing Next.js environment variables.

## Root Causes
1. **Environment Variable Mismatch**: Next.js doesn't read `VITE_*` variables, only `NEXT_PUBLIC_*`
2. **SSR Browser API Access**: Components accessing `window`, `localStorage`, or `document` during server-side rendering
3. **Import.meta Access**: Our config tries to access `import.meta.env` which doesn't exist in Next.js SSR

## ✅ Fixes Applied

### 1. Updated Centralized Config (`lib/config.ts`)
- ✅ Added safe `import.meta` access with try/catch
- ✅ Added Next.js environment variable support (`NEXT_PUBLIC_API_BASE_URL`)
- ✅ Added runtime injector support
- ✅ Added port 3003 support (your current Next.js port)
- ✅ Added SSR-safe fallbacks

### 2. Added Browser Guards to Dashboard (`tmp_lovable/src/pages/Dashboard.tsx`)
- ✅ Added `useEffect` and `useState` for client-side mounting
- ✅ Added loading state to prevent SSR crashes
- ✅ Added browser safety checks

### 3. Created Error Boundary (`pages/dashboard/error.tsx`)
- ✅ Added graceful error handling for Dashboard route
- ✅ Added error logging and retry functionality

## 🔧 Manual Steps Required

### Step 1: Create Next.js Environment File
Create a file called `.env.local` in your project root with:

```bash
# Next.js Environment Configuration
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NODE_ENV=development
```

### Step 2: Restart Next.js Dev Server
```bash
# Stop the current dev server (Ctrl+C)
# Then restart:
npm run dev
```

### Step 3: Verify Backend is Running
```bash
# In another terminal, start the backend:
python test_backend_simple.py
```

### Step 4: Test the Fix
1. Visit `http://127.0.0.1:3003/dashboard` (note: port 3003, not 3000)
2. Should see Dashboard loading, then render properly
3. If error boundary appears, check the error message

## 🧪 Verification Steps

### 1. Check Environment Variables
```bash
# In your browser console (F12), run:
console.log(process.env.NEXT_PUBLIC_API_BASE_URL)
# Should show: http://127.0.0.1:8000
```

### 2. Check Backend Health
```bash
curl http://127.0.0.1:8000/api/health
# Should return: {"status":"ok"}
```

### 3. Check Dashboard Route
- Visit `http://127.0.0.1:3003/dashboard`
- Should see Dashboard with metrics and charts
- No 500 errors in browser console

## 🚨 If Still Getting 500 Errors

### Check Next.js Terminal Output
Look for specific error messages in the terminal where `npm run dev` is running.

### Common Error Messages & Fixes:

#### "import.meta is not defined"
- ✅ **Fixed**: Our config now has safe import.meta access

#### "window is not defined"
- ✅ **Fixed**: Dashboard now has browser guards and client-side mounting

#### "process.env.NEXT_PUBLIC_API_BASE_URL is undefined"
- **Fix**: Create `.env.local` file with `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`

#### "Cannot read property 'env' of undefined"
- **Fix**: Restart Next.js dev server after creating `.env.local`

### Debug Steps:
1. **Check terminal output** where Next.js is running
2. **Check browser console** (F12) for client-side errors
3. **Check Network tab** for failed requests
4. **Verify backend** is running on port 8000

## 🎯 Expected Results

### ✅ Success Indicators:
- Dashboard loads without 500 errors
- Backend health banner shows green/online
- No console errors in browser
- Dashboard displays metrics and charts

### ❌ Failure Indicators:
- 500 error page
- Error boundary with error message
- Console errors about `import.meta` or `window`
- Backend health banner shows offline

## 🔄 Rollback Plan

If the fix doesn't work:
1. **Revert config**: Restore original `lib/config.ts`
2. **Remove error boundary**: Delete `pages/dashboard/error.tsx`
3. **Restart services**: Stop and restart both backend and frontend
4. **Check logs**: Look for specific error messages

## 📞 Support

If you're still getting 500 errors after following these steps:
1. **Copy the exact error message** from the Next.js terminal
2. **Check browser console** for any client-side errors
3. **Verify backend is running** on port 8000
4. **Check environment variables** are set correctly

The fixes we've implemented should resolve the SSR issues, but the manual environment file creation is required for Next.js to read the API base URL correctly.
