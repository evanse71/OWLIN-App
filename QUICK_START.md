# Quick Start — Production-Ready Baseline

## Current Status ✅

- ✅ Backend running on port 8000
- ✅ SQLite WAL mode enabled
- ✅ OCR concurrency controlled (max 4)
- ✅ Health/Debug/Audit endpoints operational
- ✅ Log rotation configured
- ✅ Footer component ready

---

## One-Command Proof

```powershell
.\Prove-Hardening.ps1
```

**Expected Output:**
```
✅ WAL Mode: Enabled
✅ OCR Metrics: inflight=0, queue=0, max=4
✅ Lifecycle: No test data (expected)
✅ Audit Export: CSV generated
✅ Log Rotation: Files found
✅ Footer: In static build
```

---

## Key Endpoints

### Health & Monitoring
```powershell
# Full health details
Invoke-RestMethod http://127.0.0.1:8000/api/health/details | ConvertTo-Json

# Key metrics
$h = Invoke-RestMethod http://127.0.0.1:8000/api/health/details
"WAL: $($h.db_wal) | Queue: $($h.ocr_queue) | Inflight: $($h.ocr_inflight)"
```

### Debugging
```powershell
# Get invoices
$inv = Invoke-RestMethod http://127.0.0.1:8000/api/invoices
$inv.invoices | Format-Table id, supplier, status

# Get lifecycle for specific doc
$docId = $inv.invoices[0].id
Invoke-RestMethod "http://127.0.0.1:8000/api/debug/lifecycle?doc_id=$docId"
```

### Audit Export
```powershell
# Export last 7 days
$from = (Get-Date).AddDays(-7).ToString('yyyy-MM-dd')
$to = (Get-Date).ToString('yyyy-MM-dd')
Invoke-WebRequest "http://127.0.0.1:8000/api/audit/export?from=$from&to=$to" -OutFile audit_export.csv
```

---

## Frontend Testing

### Dev Mode (8080)
```powershell
cd source_extracted\tmp_lovable
npm run dev
# Open http://127.0.0.1:8080/invoices
```

### Production Mode (8000)
```powershell
cd source_extracted\tmp_lovable
npm run build
Copy-Item out\* -Recurse -Force ..\..\backend\static\
# Open http://127.0.0.1:8000/invoices
```

### Console Checks
```javascript
// Footer exists (expect 1)
document.querySelectorAll('[data-testid="invoices-footer-bar"]').length

// Debug object (expect counts)
window.__OWLIN_DEBUG?.invoices
// { pendingInSession: 0, readyCount: 0, sessionInvoices: [] }
```

---

## Configuration

### Change OCR Concurrency
```powershell
# Set before starting backend
$env:OCR_MAX_CONCURRENCY = 8
python -m uvicorn backend.main:app --port 8000
```

### Enable OCR v2
```powershell
$env:FEATURE_OCR_PIPELINE_V2 = "true"
python -m uvicorn backend.main:app --port 8000
```

---

## Troubleshooting

### Backend won't start
```powershell
# Check for Python errors
python -c "import backend.main; print('OK')"

# Kill stale processes
taskkill /F /IM python.exe
```

### Database errors
```powershell
# Check WAL mode
sqlite3 data/owlin.db "PRAGMA journal_mode"
# Should return: wal

# Reinitialize (backs up old DB)
Move-Item data\owlin.db data\owlin.db.backup
# Restart backend to recreate
```

### Check logs
```powershell
# View recent lifecycle events
Select-String backend_stdout.log -Pattern "OCR_LIFECYCLE" | Select-Object -Last 20

# View errors
Select-String backend_stdout.log -Pattern "ERROR" | Select-Object -Last 10

# Tail real-time
Get-Content backend_stdout.log -Wait -Tail 20
```

---

## Production Checklist

- [ ] Backend starts without errors
- [ ] `Prove-Hardening.ps1` exits with code 0
- [ ] Frontend builds successfully (`npm run build`)
- [ ] Static files copied to `backend/static/`
- [ ] Footer visible on both 8080 and 8000
- [ ] Test upload completes without errors
- [ ] Lifecycle markers appear in logs
- [ ] Audit export generates CSV

---

## Key Files

| File | Purpose |
|------|---------|
| `Prove-Hardening.ps1` | One-command proof script |
| `docs/OPERATIONS.md` | Full operator guide |
| `HARDENING_PROOF_COMPLETE.md` | Detailed proof report |
| `backend/main.py` | Main API with hardening features |
| `backend_stdout.log` | Rotating log file |
| `tests/artifacts/api/` | Proof artifacts |

---

## What's Ready

1. ✅ **Observability**: Health, debug, audit endpoints
2. ✅ **Concurrency**: Semaphore-controlled OCR pipeline
3. ✅ **Database**: WAL mode, proper schema
4. ✅ **Logging**: Rotation, lifecycle markers
5. ✅ **Frontend**: Footer component bundled
6. ✅ **Proof**: Automated verification script

**Ship it.** 🚀

