# 🔄 Force Fresh OCR - Cache Cleanup Guide

**Problem**: Re-uploading invoices shows old results (UUIDs, "Unknown Item", £0.00)  
**Root Cause**: File system caching - old `ocr_output.json` files being reused  
**Solution**: Clear cache and restart server  

---

## The Caching Issue Explained

### What Happens on Upload

```
1. User uploads "stori_invoice.pdf"
2. System calculates file hash
3. Creates folder: data/uploads/stori_invoice/
4. Runs OCR pipeline
5. Saves results: data/uploads/stori_invoice/ocr_output.json
```

### What Happens on Re-Upload

```
1. User deletes invoice from UI (database record deleted)
2. User re-uploads "stori_invoice.pdf"
3. System calculates file hash (same as before)
4. Finds existing folder: data/uploads/stori_invoice/
5. ⚠️  MAY reuse old ocr_output.json (if caching logic exists)
6. Shows old results (UUIDs, "Unknown Item", £0.00)
```

**The Problem**: Physical files in `data/uploads/` are NOT deleted when you delete from UI.

---

## Solution: Clear the Cache

### Method 1: Automated Script (Recommended)

Use the cleanup script to clear cache folders:

```bash
# Preview what would be deleted
python clear_ocr_cache.py --dry-run --all

# Delete all cache folders
python clear_ocr_cache.py --all

# Delete specific folders (e.g., Stori invoices)
python clear_ocr_cache.py --pattern stori

# Delete specific folders (e.g., Dragon invoices)
python clear_ocr_cache.py --pattern dragon
```

**Output**:
```
================================================================================
OCR CACHE CLEANUP SCRIPT
================================================================================

📁 Scanning for OCR cache folders...

✓ Found 3 cache folder(s)

🗑️  DELETE: stori_invoice
         Path: data/uploads/stori_invoice
         Size: 2.45 MB (15 files)
         Modified: 2025-12-03 10:30:00
         Contents: ocr_output.json, pages/, original.pdf

🗑️  DELETE: dragon_invoice
         Path: data/uploads/dragon_invoice
         Size: 1.89 MB (12 files)
         Modified: 2025-12-03 09:15:00
         Contents: ocr_output.json, pages/, original.pdf

================================================================================
Total cache size: 4.34 MB
Folders to delete: 2
================================================================================

🗑️  Deleting cache folders...
  ✓ Deleted: data/uploads/stori_invoice
  ✓ Deleted: data/uploads/dragon_invoice

================================================================================
CLEANUP COMPLETE
Deleted: 2 folder(s)
================================================================================

✅ OCR cache cleared successfully!
```

---

### Method 2: Manual Deletion

If the script doesn't work, delete manually:

**Windows PowerShell**:
```powershell
# Delete all cache folders
Remove-Item -Recurse -Force "data\uploads\*"
Remove-Item -Recurse -Force "backend\data\uploads\*"

# Or delete specific folders
Remove-Item -Recurse -Force "data\uploads\stori*"
Remove-Item -Recurse -Force "data\uploads\dragon*"
```

**Windows Command Prompt**:
```cmd
# Delete all cache folders
rmdir /s /q data\uploads
rmdir /s /q backend\data\uploads

# Recreate empty directories
mkdir data\uploads
mkdir backend\data\uploads
```

**Linux/Mac**:
```bash
# Delete all cache folders
rm -rf data/uploads/*
rm -rf backend/data/uploads/*

# Or delete specific folders
rm -rf data/uploads/stori*
rm -rf data/uploads/dragon*
```

---

### Method 3: Selective Deletion

Delete only the JSON files (keep images for debugging):

```bash
# Windows PowerShell
Get-ChildItem -Path "data\uploads" -Recurse -Filter "ocr_output.json" | Remove-Item -Force

# Linux/Mac
find data/uploads -name "ocr_output.json" -delete
```

---

## Critical: Restart the Backend

**Even after clearing cache, you MUST restart the backend!**

### Why?
- Python bytecode may be cached in memory
- Old `TableExtractor` class instance may still be loaded
- Module imports may be stale

### How to Restart

**Windows**:
```cmd
# Stop backend (Ctrl+C in the terminal)
# Or kill the process:
taskkill /F /IM python.exe

# Start backend
start_backend_5176.bat
# Or:
cd backend
python -m uvicorn main:app --reload --port 8000
```

**Linux/Mac**:
```bash
# Stop backend
pkill -f "uvicorn main:app"

# Start backend
cd backend
python -m uvicorn main:app --reload --port 8000
```

---

## Verification Steps

### 1. Verify Cache is Cleared

```bash
# Check if folders are gone
ls data/uploads/
# Should be empty or show only new uploads

# Or use the script
python clear_ocr_cache.py --dry-run --all
# Should show "No cache folders found"
```

### 2. Verify Backend Restarted

```bash
# Check backend is running
curl http://localhost:8000/health

# Check logs show fresh startup
tail -20 backend/logs/*.log
# Should show recent startup messages
```

### 3. Re-Upload Test Invoice

```bash
# Upload via UI or API
curl -X POST http://localhost:8000/api/ocr/process \
  -F "file=@stori_invoice.pdf"
```

### 4. Watch Logs for NEW Processing

```bash
# Watch logs in real-time
tail -f backend/logs/*.log | grep -E "SPATIAL|EXTRACT|TABLE"

# Expected NEW markers:
# [SPATIAL_CLUSTER] Image width: 2480px, gap_threshold: 49px
# [SPATIAL_CLUSTER] Detected 4 columns at X-boundaries: [0, 210, 320, 410, 530]
# [SPATIAL_FALLBACK] Extracted item 1: Crate of Beer... (qty=12, unit=3.56, total=42.66)
# [SPATIAL_FALLBACK] Calculated unit price: 42.66 / 12 = £3.56
# [EXTRACT] Invoice Number: INV-12345
```

### 5. Verify Results in UI

Check that the invoice now shows:
- ✅ Real descriptions (not "Unknown Item")
- ✅ Calculated unit prices (not £0.00)
- ✅ Real invoice number (not UUID)

---

## Troubleshooting

### Issue: Cache folders still exist after deletion

**Cause**: Script doesn't have permissions or wrong path

**Solution**:
```bash
# Run as administrator (Windows)
# Or check paths:
python clear_ocr_cache.py --dry-run --all
# Verify it found the folders

# Manual deletion:
explorer data\uploads  # Windows
# Delete folders manually
```

### Issue: Still seeing old results after cache clear

**Cause**: Backend not restarted

**Solution**:
```bash
# Force kill Python processes
taskkill /F /IM python.exe  # Windows
pkill -9 python              # Linux/Mac

# Restart backend
./start_backend_5176.bat
```

### Issue: New logs not appearing

**Cause**: Backend not running or wrong port

**Solution**:
```bash
# Check if backend is running
curl http://localhost:8000/health

# Check which port is active
netstat -ano | findstr :8000
netstat -ano | findstr :5176

# Start on correct port
cd backend
python -m uvicorn main:app --reload --port 8000
```

### Issue: Spatial clustering not triggering

**Cause**: PaddleOCR not returning word blocks

**Solution**:
```bash
# Check PaddleOCR is installed
python -c "from paddleocr import PaddleOCR; print('PaddleOCR OK')"

# Check logs for PaddleOCR initialization
grep "PaddleOCR" backend/logs/*.log

# Expected:
# PaddleOCR initialized.
# PaddleOCR loaded successfully for table extraction
```

---

## Complete Cleanup Procedure

### Full Reset (Nuclear Option)

If you want to start completely fresh:

```bash
# 1. Stop backend
# Ctrl+C or taskkill /F /IM python.exe

# 2. Clear ALL cache
python clear_ocr_cache.py --all

# 3. Clear database (optional - only if testing)
# CAUTION: This deletes all invoices!
# rm data/owlin.db
# python backend/app/db.py  # Recreate schema

# 4. Apply migration
python apply_invoice_number_migration.py

# 5. Restart backend
./start_backend_5176.bat

# 6. Re-upload test invoices

# 7. Verify fresh processing
tail -f backend/logs/*.log | grep SPATIAL
```

---

## Cache Cleanup Script Usage

### Basic Usage

```bash
# Interactive mode (asks for confirmation)
python clear_ocr_cache.py

# Delete all cache (no confirmation)
python clear_ocr_cache.py --all

# Preview without deleting
python clear_ocr_cache.py --dry-run --all
```

### Pattern Matching

```bash
# Delete folders matching "stori"
python clear_ocr_cache.py --pattern stori

# Delete folders matching "dragon"
python clear_ocr_cache.py --pattern dragon

# Preview pattern match
python clear_ocr_cache.py --dry-run --pattern stori
```

### Advanced

```bash
# Delete all, but preview first
python clear_ocr_cache.py --dry-run --all
# Review output, then:
python clear_ocr_cache.py --all

# Delete multiple patterns
python clear_ocr_cache.py --pattern stori
python clear_ocr_cache.py --pattern dragon
python clear_ocr_cache.py --pattern test
```

---

## Best Practices

### During Development

**Always** clear cache when testing code changes:

```bash
# Before each test cycle:
python clear_ocr_cache.py --all
./start_backend_5176.bat
# Upload test invoice
# Verify new code runs
```

### In Production

**Rarely** clear cache (only for debugging):

```bash
# Clear specific problematic invoice
python clear_ocr_cache.py --pattern <invoice_name>

# Restart backend
./start_backend_5176.bat
```

### After Code Updates

**Always** clear cache and restart:

```bash
# 1. Stop backend
# 2. Clear cache
python clear_ocr_cache.py --all
# 3. Restart backend
./start_backend_5176.bat
# 4. Test with known invoice
```

---

## Monitoring

### Check Cache Size

```bash
# Windows PowerShell
Get-ChildItem -Path "data\uploads" -Recurse | Measure-Object -Property Length -Sum

# Linux/Mac
du -sh data/uploads
```

### List Cache Folders

```bash
# Windows
dir data\uploads /b

# Linux/Mac
ls -lh data/uploads/
```

### Find Old Cache

```bash
# Windows PowerShell (folders older than 7 days)
Get-ChildItem -Path "data\uploads" -Directory | Where-Object {$_.LastWriteTime -lt (Get-Date).AddDays(-7)}

# Linux/Mac
find data/uploads -type d -mtime +7
```

---

## Quick Reference

### Commands

| Command | Purpose |
|---------|---------|
| `python clear_ocr_cache.py --dry-run --all` | Preview all cache |
| `python clear_ocr_cache.py --all` | Delete all cache |
| `python clear_ocr_cache.py --pattern stori` | Delete Stori cache |
| `taskkill /F /IM python.exe` | Stop backend (Windows) |
| `./start_backend_5176.bat` | Start backend |

### Files to Check

| File | Purpose |
|------|---------|
| `data/uploads/*/ocr_output.json` | Cached OCR results |
| `data/uploads/*/pages/*.png` | Rendered page images |
| `data/uploads/*/original.pdf` | Original uploaded file |

### Logs to Watch

| Marker | Meaning |
|--------|---------|
| `[SPATIAL_CLUSTER]` | New spatial clustering running |
| `[SPATIAL_FALLBACK]` | New extraction logic running |
| `[EXTRACT] Invoice Number:` | Invoice number extracted |
| `Calculated unit price:` | Unit price fallback working |

---

## Summary

To force fresh OCR processing:

1. **Clear cache**: `python clear_ocr_cache.py --all`
2. **Restart backend**: Stop (Ctrl+C) and start (`./start_backend_5176.bat`)
3. **Re-upload**: Upload test invoice
4. **Verify**: Watch logs for `[SPATIAL_CLUSTER]` markers

**Critical**: Both steps (clear cache + restart) are required!

---

## Status

✅ **Cache cleanup script created**  
✅ **Documentation complete**  
✅ **Ready to force fresh OCR**

**Next**: Run the script and restart! 🚀

