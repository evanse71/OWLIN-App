# Fix Invoice Data - Step by Step Guide

## 🔍 **Problem**
The invoice is showing:
- ❌ "Unknown item" for descriptions
- ❌ Wrong quantities (12, 98 instead of 8, 2)
- ❌ Wrong invoice number (UUID instead of 852021_162574)
- ❌ Wrong VAT/totals

## 🎯 **Root Cause**
The invoice was processed **BEFORE** we implemented the fixes. The database and OCR cache contain old data.

## ✅ **Solution: Force Fresh Processing**

### **Step 1: Delete Invoice from UI**
1. Open the invoice in the UI
2. Click the **delete/trash** button (or use the delete action)
3. Confirm deletion

### **Step 2: Clear OCR Cache** ✅ DONE
```bash
python clear_ocr_cache.py --all
```
**Status**: ✅ Cache cleared

### **Step 3: Verify Backend is Running** ✅ DONE
```bash
# Backend should be running on port 8000
```
**Status**: ✅ Backend running with new code

### **Step 4: Re-upload Invoice**
1. Go to the upload page
2. Upload the **Stori invoice PDF** again
3. Wait for processing to complete

### **Step 5: Verify Results**
After re-upload, you should see:
- ✅ Invoice number: `852021_162574` (not UUID)
- ✅ Descriptions: "Gwynt Black Dragon case of 12", "Barti Spiced 70cl"
- ✅ Quantities: 8, 2 (not 12, 98)
- ✅ Total: £289.17
- ✅ VAT: £48.19

---

## 🔧 **What Changed in the Code**

### **Backend Fixes Applied:**
1. ✅ **Invoice Number Regex**: Now handles "INVOICE NO. 852021_162574"
2. ✅ **Total Extraction**: Prioritizes large amounts, handles commas
3. ✅ **Description Extraction**: Checks multiple field names, skips empty

### **Files Modified:**
- `backend/services/ocr_service.py`:
  - Invoice number patterns (lines 609-629)
  - Total extraction logic (lines 659-715)
  - Description extraction (lines 861-906)

---

## 📝 **If Still Not Working**

### **Check Backend Logs**
Look for these log messages:
```
[EXTRACT] Found invoice number via pattern: 852021_162574
[EXTRACT] Found total: £289.17
[SPATIAL_FALLBACK] Extracted item 1: Gwynt Black Dragon...
```

### **Verify Cache is Cleared**
```bash
# Check if cache folders exist
ls backend/data/uploads/
# Should be empty or only new uploads
```

### **Restart Backend**
```bash
# Stop backend (Ctrl+C)
# Start backend
python -m uvicorn backend.main:app --port 8000 --reload
```

---

## 🎯 **Expected Behavior After Re-upload**

1. **Backend processes PDF** with new extraction code
2. **Extracts invoice number** using improved regex
3. **Extracts descriptions** using spatial clustering + semantic patterns
4. **Calculates totals** using improved logic
5. **Saves to database** with correct data
6. **Frontend displays** correct information

---

**Status**: ✅ **Ready for Re-upload**

**Next Step**: Delete invoice from UI → Re-upload PDF → Verify results

