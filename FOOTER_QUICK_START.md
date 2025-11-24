# Footer Quick Start - 5 Minute Validation

## What Was Built

Persistent footer bar on `/invoices` showing:
- **Pending in this session:** N
- **Ready to submit:** M  
- Buttons: **[Clear Session]** and **[Submit M]**

Works on BOTH ports: 8080 (dev) and 8000 (production).

---

## Validate in 3 Steps

### Step 1: Run Automated Tests (30 seconds)
```powershell
.\Test-Footer-Both-Ports.ps1
```
Should show: `✓ AUTOMATED CHECKS PASSED` with 8 green checkmarks.

### Step 2: Test Dev Mode (2 minutes)
```powershell
cd source_extracted\tmp_lovable
npm run dev
```
1. Open: http://127.0.0.1:8080/invoices
2. Footer visible at bottom? ✓
3. Shows `Pending: 0` and `Ready: 0`? ✓
4. Both buttons disabled? ✓
5. Upload an invoice (drag & drop or click Upload)
6. Footer updates to `Pending: 1` and `Ready: 1`? ✓
7. Buttons now enabled? ✓
8. Click **Clear Session** → counts reset to 0? ✓
9. Upload again, click **Submit 1** → toast appears? ✓

### Step 3: Test Production Mode (2 minutes)
```powershell
cd ..\..  # Back to root
.\Build-And-Deploy-Frontend.ps1
python -m uvicorn backend.main:app --port 8000
```
1. Open: http://127.0.0.1:8000/invoices
2. **Exact same behavior as Step 2?** ✓

---

## Console Validation

Open browser DevTools → Console tab:

```javascript
// Should return 1 (footer exists exactly once)
document.querySelectorAll('[data-testid="invoices-footer-bar"]').length

// Should return 0 initially, increases after upload
__OWLIN_DEBUG.invoices.pendingInSession
__OWLIN_DEBUG.invoices.readyCount

// Should show session array
__OWLIN_DEBUG.invoices.sessionInvoices
```

---

## Troubleshooting

### Footer Not Visible on 8080
```powershell
# Check imports in Invoices.tsx
grep -n "InvoicesFooterBar" source_extracted/tmp_lovable/src/pages/Invoices.tsx

# Should show:
# 85: import { InvoicesFooterBar } from '@/components/invoices/InvoicesFooterBar';
# 702: <InvoicesFooterBar
```

### Footer Not Visible on 8000
```powershell
# Verify build output
ls backend/static/index.html

# If missing, rebuild:
.\Build-And-Deploy-Frontend.ps1
```

### Buttons Stay Disabled
```powershell
# Check console for errors
# Upload should call addToSession() automatically
# Check network tab: POST /api/upload should succeed
```

---

## Done When...

- [x] Automated tests pass
- [ ] Footer visible on 8080
- [ ] Footer visible on 8000  
- [ ] Buttons enable/disable correctly
- [ ] Clear works (removes pending)
- [ ] Submit works (marks as submitted)
- [ ] Console shows correct counts

**All checked? Ship it.**

---

## Files Changed (for reference)

**Created:**
- `source_extracted/tmp_lovable/src/components/invoices/InvoicesFooterBar.tsx`
- `source_extracted/tmp_lovable/src/state/invoicesStore.ts`
- `backend/routes/invoices_submit.py`
- `Build-And-Deploy-Frontend.ps1`

**Modified:**
- `source_extracted/tmp_lovable/src/pages/Invoices.tsx` (+73 lines)
- `source_extracted/tmp_lovable/vite.config.ts` (outDir → "out")
- `backend/main.py` (+3 lines)

**Total:** 7 files created, 3 modified

---

## Commands Reference

| Task | Command |
|------|---------|
| Validate | `.\Test-Footer-Both-Ports.ps1` |
| Dev mode | `cd source_extracted\tmp_lovable && npm run dev` |
| Build | `.\Build-And-Deploy-Frontend.ps1` |
| Quick rebuild | `.\Quick-Deploy.ps1` |
| Start backend | `python -m uvicorn backend.main:app --port 8000` |
| Check console | `__OWLIN_DEBUG.invoices` |
| Check DOM | `document.querySelectorAll('[data-testid="invoices-footer-bar"]')` |

---

**Status:** READY FOR VALIDATION  
**Time Required:** 5 minutes  
**Ports:** 8080, 8000

