# Release Checklist — Copy-Paste Commands

## ✅ Pre-Flight (Complete)

- [x] Database schema fixed (WAL mode enabled)
- [x] Frontend built fresh (`npm run build`)
- [x] Static files deployed to `backend/static/`
- [x] All 8 gates passed
- [x] Snapshot created: `FixPack_2025-11-02_14-28-12`
- [x] Backend running from correct directory (`:8000`)

---

## 🚀 Go-Live Commands

### 1. Start Production Monitor
```powershell
.\Monitor-Production.ps1
```
**Expected Output:**
```
TIME       WAL        QUEUE      INFLIGHT   ERRORS     STATUS
14:35:00   ✓          0          0/4        0          OK
```

### 2. Verify All Gates
```powershell
.\Prove-Hardening.ps1
```
**Expected:** Exit code 0, all checks passing

### 3. Browser Smoke Test
```
URL: http://127.0.0.1:8000/invoices
```
**DevTools Console:**
```javascript
document.querySelectorAll('[data-testid="invoices-footer-bar"]').length  // Expect: 1
window.__OWLIN_DEBUG?.invoices  // Expect: {pendingInSession, readyCount, sessionInvoices}
```

### 4. Upload Test Invoice
- Drag PDF to upload area
- Wait for processing (status → `scanned`)
- Check lifecycle: 
  ```powershell
  $inv = Invoke-RestMethod http://127.0.0.1:8000/api/invoices
  $docId = $inv.invoices[0].id
  Invoke-RestMethod "http://127.0.0.1:8000/api/debug/lifecycle?doc_id=$docId"
  ```
- Verify `line_items[]` present in response

---

## 🔒 Post-Ship Monitoring

### Health Pulse (Every 10s)
```powershell
while ($true) {
    $h = Invoke-RestMethod http://127.0.0.1:8000/api/health/details
    Write-Host (Get-Date).ToString("HH:mm:ss"), "Q:$($h.ocr_queue)", "I:$($h.ocr_inflight)", "E:$($h.total_errors)"
    Start-Sleep 10
}
```

### Alert Thresholds
| Condition | Action |
|-----------|--------|
| `db_wal: false` | **CRITICAL** — Stop backend, check DB, restart |
| `ocr_queue > 20` | **WARNING** — Throttle uploads or increase `OCR_MAX_CONCURRENCY` |
| `ocr_inflight == max` for >5 min | Check CPU/memory usage |
| `total_errors` increasing | Check `backend_stdout.log` for patterns |

---

## 🔄 Rollback Procedure

### Instant Rollback (30 seconds)
```powershell
# Stop backend
taskkill /F /IM python.exe 2>$null

# Identify last good snapshot
$good = (Get-ChildItem -Directory | Where-Object Name -like "FixPack_*" | 
         Sort-Object LastWriteTime -Descending | Select-Object -Skip 1 -First 1).FullName

# Restore
Robocopy "$good\code" . /MIR /XD FixPack_*
Robocopy "$good\static" backend\static /MIR
Robocopy "$good\data" data /MIR

# Restart
python -m uvicorn backend.main:app --port 8000
```

### Verify Rollback
```powershell
$h = Invoke-RestMethod http://127.0.0.1:8000/api/health/details
"WAL: $($h.db_wal) | Version: $($h.app_version)"
```

---

## 📦 Next Snapshot (Before Changes)

```powershell
$ts = (Get-Date).ToString('yyyy-MM-dd_HH-mm-ss')
$new = "FixPack_$ts"
New-Item -ItemType Directory $new | Out-Null

# Code
Robocopy . "$new\code" /E /XD node_modules .venv .git out dist FixPack_* data /NFL /NDL /NJH

# Build & static
cd source_extracted\tmp_lovable
npm run build
cd ..\..
Robocopy source_extracted\tmp_lovable\out "$new\static" /E /NFL /NDL /NJH
Robocopy backend\static "$new\static_backend" /E /NFL /NDL /NJH

# Data & logs
Robocopy data "$new\data" /E /NFL /NDL /NJH
Copy-Item backend_stdout.log* "$new\" -ErrorAction SilentlyContinue

# Index
"Release: $ts`nRoot: $((Get-Location).Path)" | Out-File "$new\README.txt" -Encoding utf8

Write-Host "Snapshot created: $new" -ForegroundColor Green
```

---

## 📊 Key Metrics

### Current Baseline
- **WAL Mode:** Enabled
- **OCR Max Concurrency:** 4
- **Log Rotation:** 5MB, 3 backups
- **App Version:** 1.2.0
- **Snapshot:** FixPack_2025-11-02_14-28-12 (1.3 GB)

### Performance Targets
- **Upload to DOC_READY:** < 15 seconds
- **OCR Queue:** < 10 sustained
- **Error Rate:** < 5%
- **TTI (Time to Interactive):** < 2 seconds on `/invoices`

---

## 🛠 Troubleshooting

### Backend Won't Start
```powershell
# Test import
python -c "import backend.main; print('OK')"

# Check for stale processes
taskkill /F /IM python.exe

# Verify working directory
Get-Location  # Must be workspace root
```

### Static Files 404
```powershell
# Rebuild and copy
cd source_extracted\tmp_lovable
npm run build
Copy-Item out\* ..\..\backend\static\ -Recurse -Force
cd ..\..

# Restart backend
taskkill /F /IM python.exe
python -m uvicorn backend.main:app --port 8000
```

### Database Errors
```powershell
# Check WAL mode
sqlite3 data/owlin.db "PRAGMA journal_mode"  # Should return: wal

# If corrupted, restore from snapshot
Copy-Item "FixPack_2025-11-02_14-28-12\data\owlin.db" data\owlin.db -Force
```

---

## 📝 Documentation

- **Full Proof:** `BRJ_RELEASE_LOCK.md`
- **Hardening Details:** `HARDENING_PROOF_COMPLETE.md`
- **Quick Start:** `QUICK_START.md`
- **Operator Guide:** `docs/OPERATIONS.md`

---

## ✅ Release Sign-Off

**Date:** 2025-11-02  
**Version:** 1.0 Production-Grade  
**All 8 Gates:** PASSED  
**Snapshot:** FixPack_2025-11-02_14-28-12  
**Rollback Ready:** YES  

**Status:** PRODUCTION-READY ✅

**Ship it.** 🚀

