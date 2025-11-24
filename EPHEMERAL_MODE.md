# 🚀 Ephemeral Demo Mode

**True ephemeral demo mode** - no demo data, fresh state on every page load, real uploads create cards, refreshing wipes everything for instant retesting.

## ✅ Features

- **No demo/preloaded data** - All mock data eliminated in ephemeral mode
- **Fresh state on every page load** - Backend resets on startup and page refresh  
- **Uploads create real cards** - Real API integration maintained
- **Refreshing wipes what you just uploaded** - Perfect for demos
- **Production-safe** - Reset endpoint returns 403 unless `OWLIN_EPHEMERAL=1`
- **Supplier aliases preserved** - Matching functionality stays useful
- **Browser cache clearing** - Eliminates stale demo data from storage
- **HMR protection** - Only resets once per session, not on hot reloads

## 🚀 Quick Start

### Linux/macOS (POSIX)
```bash
# Start in ephemeral mode
VITE_API_BASE_URL=http://127.0.0.1:8000 \
VITE_OWLIN_EPHEMERAL=1 \
OWLIN_SINGLE_PORT=1 \
OWLIN_EPHEMERAL=1 \
bash scripts/run_single_port.sh
```

### Windows PowerShell
```powershell
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
$env:VITE_OWLIN_EPHEMERAL="1"
$env:OWLIN_SINGLE_PORT="1"
$env:OWLIN_EPHEMERAL="1"
powershell -ExecutionPolicy Bypass -File scripts\run_single_port.ps1
```

## 🧪 30-Second Proof

### Linux/macOS
```bash
# 1) Start server (in one terminal)
VITE_API_BASE_URL=http://127.0.0.1:8000 \
VITE_OWLIN_EPHEMERAL=1 OWLIN_SINGLE_PORT=1 OWLIN_EPHEMERAL=1 \
bash scripts/run_single_port.sh

# 2) Test (in another terminal)
./test_ephemeral_clean.sh
```

### Windows PowerShell
```powershell
# 1) Start server (in one terminal)
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
$env:VITE_OWLIN_EPHEMERAL="1"
$env:OWLIN_SINGLE_PORT="1"
$env:OWLIN_EPHEMERAL="1"
powershell -ExecutionPolicy Bypass -File scripts\run_single_port.ps1

# 2) Test (in another terminal)
.\test_ephemeral_clean.ps1
```

## 🔧 Manual Testing

### 1. Health Check
```bash
curl -s http://127.0.0.1:8000/api/health
```

### 2. Reset Endpoint (Ephemeral Mode)
```bash
curl -s -X POST http://127.0.0.1:8000/api/reset | jq
```

### 3. Create Test PDFs
```bash
# Linux/macOS
printf "%%PDF-1.4\nINV-1234_ACME\n" > INV-1234_ACME.pdf
printf "%%PDF-1.4\nDN-1234_ACME\n" > DN-1234_ACME.pdf

# Windows PowerShell
$inv="%PDF-1.4`nINV-1234_ACME`n"; $dn="%PDF-1.4`nDN-1234_ACME`n"
[IO.File]::WriteAllText("INV-1234_ACME.pdf",$inv,[Text.Encoding]::UTF8)
[IO.File]::WriteAllText("DN-1234_ACME.pdf",$dn,[Text.Encoding]::UTF8)
```

### 4. Upload Files
```bash
# Via UI: Open http://127.0.0.1:8000 → Invoices → upload both files

# Via API:
curl -s -F "file=@INV-1234_ACME.pdf" http://127.0.0.1:8000/api/upload | jq
curl -s -F "file=@DN-1234_ACME.pdf" http://127.0.0.1:8000/api/upload | jq
```

### 5. Check Pairing Suggestions
```bash
curl -s http://127.0.0.1:8000/api/pairs/suggestions | jq
```

### 6. Refresh Page → Everything Disappears
Open http://127.0.0.1:8000 in browser, refresh the page, and watch everything reset!

## 🛡️ Safety Features

### Production Protection
```bash
# With OWLIN_EPHEMERAL=0 (or unset)
curl -i -X POST http://127.0.0.1:8000/api/reset  # → 403 Forbidden
```

### HMR Protection
The frontend only resets once per session to avoid excessive resets during development:
```tsx
// Only resets once per full page load (avoids HMR resets)
if (EPHEMERAL && !sessionStorage.getItem("ephemeralResetDone")) {
  fetch("/api/reset?t=" + Date.now(), { method: "POST" })
    .finally(() => sessionStorage.setItem("ephemeralResetDone", "1"))
}
```

## 🔍 Troubleshooting

### Reset Endpoint Returns 500
- Ensure `OWLIN_EPHEMERAL=1` is set
- Check that the route is registered: `@app.post("/api/reset")`
- Verify table names in `_reset_db()` match your schema: `documents`, `pairs`, `audit_log`

### No Cards After Upload
- Confirm you're using **real API** (`api.real.ts`)
- Check your PDF isn't deduplicated (use different contents)
- Check logs: `tail -n 200 data/logs/app.log | grep -E "upload|PAIR_SUGGEST|ERROR"`

### Frontend Not Resetting
- Verify `VITE_OWLIN_EPHEMERAL=1` is set
- Check browser console for errors
- Clear sessionStorage: `sessionStorage.clear()` in browser console

## 📁 Files Modified

### Backend (`test_backend_simple.py`)
- Added ephemeral mode configuration
- Added reset functions (`_safe_rmdir_contents`, `_reset_db`, `clear_state`)
- Added `/api/reset` endpoint with production protection
- Modified lifespan manager to reset on startup
- Fixed Unicode encoding issues in logging

### Frontend (`tmp_lovable/src/App.tsx`)
- Added comprehensive ephemeral boot sequence
- Added reset trigger on page load (once per session)
- Added HMR protection with sessionStorage

### Frontend (`tmp_lovable/src/app-ephemeral-boot.ts`) - NEW
- Comprehensive boot sequence for ephemeral mode
- Browser cache clearing (localStorage, sessionStorage, IndexedDB, caches)
- Global demo-off flag for components
- HMR protection with sessionStorage

### Frontend (`tmp_lovable/src/lib/api.ts`)
- Force real API only - no demo fallbacks
- Empty state returns instead of demo data
- Ephemeral mode detection

### Frontend (`tmp_lovable/src/pages/Dashboard.tsx`, `tmp_lovable/src/pages/FlaggedIssues.tsx`)
- Added empty state guards for ephemeral mode
- Prevents mock data from showing

### Frontend (`tmp_lovable/src/pages/Invoices.tsx`, `tmp_lovable/src/components/layout/Sidebar.tsx`)
- Added ephemeral mode guards for mock venues
- Empty arrays when in ephemeral mode

## 🎯 Perfect For

- **Demos** - Clean slate every time
- **Testing** - Consistent starting state
- **Development** - No leftover data
- **Presentations** - Reliable, repeatable demos

## 🔄 How It Works

1. **Server Startup**: When `OWLIN_EPHEMERAL=1`, server clears all data on startup
2. **Page Load**: Frontend calls `/api/reset` once per session on page load
3. **Uploads**: Real API creates actual cards and pairing suggestions
4. **Refresh**: Page refresh triggers another reset, wiping everything
5. **Production**: Reset endpoint returns 403 unless ephemeral mode is enabled

That's it! Fresh state every load, real uploads create cards, and you can retest instantly with a refresh. 🚀
