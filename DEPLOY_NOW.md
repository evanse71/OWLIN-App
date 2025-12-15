# 🚀 DEPLOY NOW - Quick Start Guide

**Status**: 🟢 Ready for Deployment  
**Time Required**: 5 minutes  
**Risk**: Low (backward compatible)

---

## Quick Deploy (Copy-Paste These Commands)

### Windows PowerShell

```powershell
# Step 1: Apply database migration (30 seconds)
python apply_invoice_number_migration.py

# Step 2: Clear OCR cache (30 seconds)
python clear_ocr_cache.py --all

# Step 3: Stop backend (if running)
# Press Ctrl+C in backend terminal
# Or force kill:
taskkill /F /IM python.exe

# Step 4: Start backend (30 seconds)
.\start_backend_5176.bat
# Or:
cd backend
python -m uvicorn main:app --reload --port 8000

# Step 5: Watch logs (keep this running)
Get-Content backend\logs\*.log -Wait -Tail 50 | Select-String -Pattern "SPATIAL|EXTRACT"
```

---

### Windows Command Prompt

```cmd
REM Step 1: Apply migration
python apply_invoice_number_migration.py

REM Step 2: Clear cache
python clear_ocr_cache.py --all

REM Step 3: Stop backend
taskkill /F /IM python.exe

REM Step 4: Start backend
start_backend_5176.bat

REM Step 5: Watch logs
tail -f backend\logs\*.log | findstr "SPATIAL EXTRACT"
```

---

### Linux/Mac

```bash
# Step 1: Apply migration
python3 apply_invoice_number_migration.py

# Step 2: Clear cache
python3 clear_ocr_cache.py --all

# Step 3: Stop backend
pkill -f "uvicorn main:app"

# Step 4: Start backend
cd backend
python3 -m uvicorn main:app --reload --port 8000 &

# Step 5: Watch logs
tail -f backend/logs/*.log | grep -E "SPATIAL|EXTRACT"
```

---

## Verification Checklist

### ✅ Step 1: Migration Applied

**Expected Output**:
```
================================================================================
INVOICE NUMBER MIGRATION
================================================================================

📁 Database: data\owlin.db

📝 Applying migration...
  1. Adding invoice_number column...
     ✓ Column added
  2. Creating index on invoice_number...
     ✓ Index created

✅ Migration successful!
   Columns: id, doc_id, supplier, date, value, invoice_number
   Existing invoices: 42
```

**Verify**:
```bash
sqlite3 data/owlin.db "PRAGMA table_info(invoices)" | findstr invoice_number
# Expected: invoice_number|TEXT|0||0
```

---

### ✅ Step 2: Cache Cleared

**Expected Output**:
```
================================================================================
CLEANUP COMPLETE
Deleted: 5 folder(s)
================================================================================

✅ OCR cache cleared successfully!
```

**Verify**:
```bash
# Should be empty or show only .gitkeep
ls data/uploads/
```

---

### ✅ Step 3: Backend Restarted

**Expected in Logs**:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Verify**:
```bash
curl http://localhost:8000/health
# Expected: {"status": "healthy"}
```

---

### ✅ Step 4: Upload Test Invoice

**Via UI**: 
- Open http://localhost:5176
- Click "Upload Invoice"
- Select Stori invoice
- Watch processing

**Via API**:
```bash
curl -X POST http://localhost:8000/api/ocr/process \
  -F "file=@stori_invoice.pdf"
```

---

### ✅ Step 5: Verify New Processing

**Watch Logs**:
```bash
tail -f backend/logs/*.log | grep -E "SPATIAL|EXTRACT"
```

**Expected NEW Markers** (these prove new code is running):
```
[SPATIAL_CLUSTER] Image width: 2480px, gap_threshold: 49px
[SPATIAL_CLUSTER] Detected 4 columns at X-boundaries: [0, 210, 320, 410, 530]
[SPATIAL_CLUSTER] Column assignments: ['description', 'qty', 'unit_price', 'total']
[SPATIAL_FALLBACK] Image height: 2980px, y_tolerance: 29px
[SPATIAL_FALLBACK] Extracted item 1: Crate of Beer... (qty=12, unit=3.56, total=42.66)
[SPATIAL_FALLBACK] Calculated unit price: 42.66 / 12 = £3.56
[EXTRACT] Found invoice number via pattern 'INV[-/]?(\d+)': INV-12345
[EXTRACT] Invoice Number: INV-12345
[STORE] Storing document: invoice_no='INV-12345', supplier='Stori Beer & Wine', ...
```

**Old Markers** (if you see these, cache wasn't cleared or backend not restarted):
```
[OCR_V2] Calling process_document...
# But NO [SPATIAL_CLUSTER] or [SPATIAL_FALLBACK] markers
```

---

### ✅ Step 6: Verify Results

**Check Database**:
```bash
sqlite3 data/owlin.db "SELECT id, supplier, invoice_number FROM invoices ORDER BY id DESC LIMIT 1"

# Expected:
# d46396bd|Stori Beer & Wine|INV-12345
```

**Check API**:
```bash
curl http://localhost:8000/api/invoices | jq '.invoices[0]'

# Expected:
# {
#   "id": "d46396bd",
#   "supplier": "Stori Beer & Wine",
#   "invoice_number": "INV-12345",  ← Real number!
#   "line_items": [
#     {
#       "description": "Crate of Beer",  ← Real description!
#       "quantity": 12,
#       "unit_price": 3.56,  ← Calculated!
#       "total": 42.66
#     }
#   ]
# }
```

**Check UI**:
- Open http://localhost:5176
- View uploaded invoice
- Verify all fields populated correctly

---

## Common Issues

### Issue: "No cache folders found" but still seeing old results

**Cause**: Cache in different location or backend not restarted

**Solution**:
```bash
# Check both locations
ls data/uploads/
ls backend/data/uploads/

# Force restart backend
taskkill /F /IM python.exe
./start_backend_5176.bat
```

---

### Issue: Migration fails "column already exists"

**Cause**: Migration already applied

**Solution**:
```bash
# This is OK! Migration is idempotent
# Just continue to next step
```

---

### Issue: Backend won't start

**Cause**: Port already in use or syntax error

**Solution**:
```bash
# Check port
netstat -ano | findstr :8000

# Kill process on port
taskkill /F /PID <pid>

# Check for syntax errors
python -m py_compile backend/main.py
python -m py_compile backend/ocr/table_extractor.py
```

---

### Issue: Still seeing "Unknown Item" after all steps

**Cause**: Frontend caching or old API response

**Solution**:
```bash
# Clear browser cache
# Ctrl+Shift+R (hard refresh)

# Or check API directly
curl http://localhost:8000/api/invoices | jq '.invoices[0].line_items[0].description'

# Should show real description, not "Unknown Item"
```

---

## Success Indicators

### ✅ You Know It Worked When:

1. **Logs show NEW markers**:
   - `[SPATIAL_CLUSTER]` appears
   - `[SPATIAL_FALLBACK]` appears
   - `Calculated unit price:` appears
   - `Invoice Number:` appears

2. **Database has invoice_number**:
   - Query shows real invoice number (not NULL)

3. **API returns complete data**:
   - `invoice_number` field present
   - `line_items` have descriptions
   - `unit_price` not 0.00

4. **UI displays correctly**:
   - Real invoice number visible
   - All line item fields populated
   - No "Unknown Item" or £0.00

---

## Rollback (If Needed)

### If Something Goes Wrong

```bash
# 1. Stop backend
taskkill /F /IM python.exe

# 2. Restore from backup (if you made one)
# Or just restart with old code

# 3. Database rollback (if needed)
# Note: SQLite doesn't support DROP COLUMN
# Column with NULL values is harmless

# 4. Restart backend
./start_backend_5176.bat
```

---

## Timeline

### Deployment
- **Step 1**: Migration (30 seconds)
- **Step 2**: Clear cache (30 seconds)
- **Step 3**: Restart backend (30 seconds)
- **Step 4**: Upload test (1 minute)
- **Step 5**: Verify (2 minutes)

**Total**: ~5 minutes

### Verification
- **Logs**: Immediate (watch in real-time)
- **Database**: 30 seconds (query after upload)
- **API**: 30 seconds (curl test)
- **UI**: 1 minute (visual inspection)

**Total**: ~2 minutes

---

## Final Checklist

### Pre-Deployment
- [x] All code changes committed
- [x] Migration script created
- [x] Cache cleanup script created
- [x] Documentation complete
- [x] Architect approval received

### Deployment
- [ ] Migration applied
- [ ] Cache cleared
- [ ] Backend restarted
- [ ] Test invoice uploaded
- [ ] Logs verified

### Post-Deployment
- [ ] Database checked
- [ ] API tested
- [ ] UI verified
- [ ] No errors in logs

---

## 🎯 The Moment of Truth

**Run these commands now**:

```bash
python apply_invoice_number_migration.py
python clear_ocr_cache.py --all
# Stop backend (Ctrl+C)
./start_backend_5176.bat
# Upload Stori invoice
# Watch the magic! ✨
```

---

**Status**: 🟢 **READY TO DEPLOY**

**Everything is in place. Time to see the spatial clustering in action!** 🚀

---

_Pro tip: Keep the log tail running in a separate terminal so you can watch the `[SPATIAL_CLUSTER]` markers appear in real-time. It's incredibly satisfying!_ 😊

