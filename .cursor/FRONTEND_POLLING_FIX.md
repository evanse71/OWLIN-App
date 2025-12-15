# Frontend Upload Polling Fix

**Date**: 2025-12-11  
**Issue**: Progress bar stuck at 100%, no invoice cards appearing after upload

## Root Cause

The frontend polling logic had two issues:

1. **Polling timeout too short**: 
   - Frontend polled for 40 attempts × 1.5s = **60 seconds**
   - OCR processing takes **~60-70 seconds** to complete
   - Frontend gave up just before OCR finished

2. **No fallback refresh mechanism**:
   - When polling timed out, frontend entered 'waiting-for-card' state
   - Only called `fetchInvoices()` once
   - If invoice wasn't ready yet, it would never appear

## Fixes Applied

### 1. Increased Polling Timeout (`frontend_clean/src/lib/upload.ts`)
- **Changed**: `maxAttempts` from 40 to 80
- **Result**: Polling now lasts 80 × 1.5s = **120 seconds** (matches OCR processing time)
- **Line**: 225

### 2. Added Periodic Invoice Refresh (`frontend_clean/src/pages/Invoices.tsx`)
- **Added**: `useEffect` hook that periodically refreshes invoice list every 5 seconds
- **Trigger**: While files are in 'waiting-for-card' or 'processing' state
- **Result**: Even if polling times out, frontend keeps checking for invoice cards
- **Lines**: 858-874

## How It Works Now

1. **Upload**: File uploaded, `doc_id` received
2. **Polling**: Frontend polls `/api/upload/status` for up to 120 seconds
3. **If polling succeeds**: Card appears immediately via `onComplete` callback
4. **If polling times out**: 
   - Frontend enters 'waiting-for-card' state
   - Periodic refresh (every 5s) keeps checking invoice list
   - When invoice appears, card detection `useEffect` triggers
   - Progress bar animates to 100% and card appears

## Testing

To verify the fix works:

1. Upload a file via the UI
2. Watch the progress bar - it should:
   - Reach 100% after upload completes
   - Show "Processing..." while OCR runs
   - Automatically show invoice card when OCR completes (even if it takes 70+ seconds)

## Files Modified

1. `frontend_clean/src/lib/upload.ts` - Increased polling timeout
2. `frontend_clean/src/pages/Invoices.tsx` - Added periodic refresh mechanism

## Status

✅ **Fixed** - Frontend should now properly handle long-running OCR processing and show cards even if polling times out.
