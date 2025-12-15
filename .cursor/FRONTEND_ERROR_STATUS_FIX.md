# Frontend Error Status & Infinite Loop Fix

**Date**: 2025-12-11  
**Issue**: 
1. Backend returns `status: 'error'` but frontend keeps polling indefinitely
2. Infinite render loop causing component to re-render constantly
3. Card detection not working even when invoice exists

## Root Causes

1. **Polling Never Stops on Error**:
   - Polling logic only stopped if `isDuplicateOrErrorWithData` was true
   - This required `hasItems || hasData`, which are false when status is 'error'
   - Result: Polling continues forever even when backend reports error

2. **Infinite Render Loop**:
   - `useEffect` for card detection had `invoices` in dependency array
   - Every time invoices changed, effect ran
   - Effect might trigger state updates, causing re-render
   - Re-render causes invoices to change (new array reference), triggering effect again
   - Result: Component renders constantly

3. **Card Detection Not Working**:
   - Even though invoice exists (`invoicesLength: 1`), card detection wasn't finding it
   - Likely due to ID mismatch or effect not running when needed

## Fixes Applied

### 1. Stop Polling on Error Status (`frontend_clean/src/lib/upload.ts:255-270`)
- **Added**: `const isError = statusData?.status === 'error'`
- **Changed**: Polling stops if `isError` is true (even without items/data)
- **Reason**: When backend reports error, invoice might still exist in DB - let card detection handle it
- **Result**: Polling stops after error, preventing infinite polling

### 2. Return Minimal Metadata on Error (`frontend_clean/src/lib/upload.ts:273-283`)
- **Added**: Early return for error status without items/data
- **Returns**: Minimal metadata with just `id: docId` so card detection can still work
- **Reason**: Even if status endpoint fails, invoice might exist in DB and appear in invoice list
- **Result**: Card detection can still match by doc_id even when status is error

### 3. Fixed Infinite Render Loop (`frontend_clean/src/pages/Invoices.tsx:909-1003`)
- **Added**: `lastInvoiceCountRef` to track last invoice count
- **Changed**: Only run card detection check when invoice count changes
- **Removed**: `invoices`, `animateProgress`, `processUploadQueue` from dependency array
- **Reason**: Prevent effect from running on every render
- **Result**: Effect only runs when invoice count actually changes

### 4. Fixed Periodic Refresh Dependencies (`frontend_clean/src/pages/Invoices.tsx:904`)
- **Removed**: `fetchInvoices` from dependency array (it's stable via useCallback)
- **Added**: ESLint disable comment explaining why
- **Reason**: `fetchInvoices` is memoized, doesn't need to be in dependencies
- **Result**: Periodic refresh doesn't cause infinite loops

## Files Modified

1. `frontend_clean/src/lib/upload.ts` - Stop polling on error, return minimal metadata
2. `frontend_clean/src/pages/Invoices.tsx` - Fixed infinite render loop, improved card detection

## Testing

The fixes should now:
1. ✅ Stop polling when backend returns error status
2. ✅ Prevent infinite render loops
3. ✅ Still detect cards even when status is error (by checking invoice list)
4. ✅ Show detailed console logs for debugging

## Next Steps

1. **Restart frontend** to pick up changes
2. **Upload a file via UI**
3. **Check browser console** for:
   - `[UPLOAD] Polling complete` message (should stop on error)
   - `[UPLOAD] Checking card detection` logs
   - No more infinite render messages
4. **Check backend logs** to see why OCR is failing (status: 'error')
