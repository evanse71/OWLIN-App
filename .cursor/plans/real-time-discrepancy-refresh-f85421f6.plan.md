---
name: Discrepancy Refresh Improvements
overview: ""
todos:
  - id: 16488600-a878-4ecb-a4db-4e1a66a3bf89
    content: Add error recovery and timeout fallback to prevent stuck refresh state in SmartDiscrepancyWidget
    status: pending
  - id: ec301301-563b-4963-8c41-6f8202b76e8c
    content: Add onPairSuccess callback to DeliveryNotesCardsSection and wire it to trigger discrepancy refresh
    status: pending
  - id: 349b484c-4530-4853-8746-533582d9a448
    content: Fix upload completion to await fetchInvoices before triggering discrepancy refresh
    status: pending
  - id: 6ab0b7a2-0295-4871-b1d5-afce2861f5a7
    content: Improve refresh completion check to handle edge cases and race conditions
    status: pending
---

# Discrepancy Refresh Improvements

## Overview

Fix identified issues with the discrepancy refresh mechanism to ensure it works reliably in all scenarios, handles errors gracefully, and doesn't get stuck in loading states.

## Implementation Plan

### 1. Fix Error Handling - Prevent Stuck Refresh State

**File:** `frontend_clean/src/components/invoices/SmartDiscrepancyWidget.tsx`

**Problem:** If API calls fail during refresh, `isRefreshing` might get stuck because we only clear it on successful completion.

**Solution:**

- Ensure `loadingDetails` is cleared even when errors occur (already done in finally block)
- Add timeout fallback to force refresh completion after 10 seconds
- Add error recovery in refresh completion check

**Changes:**

- Add `useEffect` with timeout to force refresh completion after 10 seconds
- Ensure refresh completion check handles cases where some fetches fail
- Add error boundary to reset refresh state on critical errors

### 2. Add Refresh Trigger for DeliveryNotesCardsSection Pairing

**Files:**

- `frontend_clean/src/components/invoices/DeliveryNotesCardsSection.tsx`
- `frontend_clean/src/pages/Invoices.tsx`

**Problem:** When pairing happens in `DeliveryNotesCardsSection.handleConfirmPairing()`, it doesn't trigger discrepancy refresh.

**Solution:**

- Add `onPairSuccess` callback prop to `DeliveryNotesCardsSection`
- Pass callback from `Invoices.tsx` that increments refresh trigger
- Call callback after successful pairing in `DeliveryNotesCardsSection`

**Changes:**

- Add `onPairSuccess?: () => void` prop to `DeliveryNotesCardsSectionProps`
- Update `DeliveryNotesCardsSection` to call `onPairSuccess()` after successful pairing
- In `Invoices.tsx`, pass callback to `DeliveryNotesCardsSection` that increments `discrepancyRefreshTrigger`
- Also refresh invoice list after pairing in `DeliveryNotesCardsSection`

### 3. Fix Upload Timing Issue

**File:** `frontend_clean/src/pages/Invoices.tsx`

**Problem:** After upload, we wait 1 second before refreshing invoices, but trigger discrepancy refresh immediately, causing mismatch.

**Solution:**

- Make `fetchInvoices()` awaitable and wait for it to complete before triggering discrepancy refresh
- Ensure invoice list is updated before discrepancy widget tries to refresh

**Changes:**

- Update upload completion handler to await `fetchInvoices()` before triggering refresh
- Add small delay after `fetchInvoices()` completes to ensure state propagation

### 4. Add Timeout Fallback for Refresh Completion

**File:** `frontend_clean/src/components/invoices/SmartDiscrepancyWidget.tsx`

**Problem:** If refresh completion check doesn't fire (edge cases), refresh state could remain stuck.

**Solution:**

- Add timeout that forces refresh completion after reasonable time (10 seconds)
- Clear timeout when refresh completes normally
- Log warning when timeout fires for debugging

**Changes:**

- Add `useEffect` that sets timeout when `isRefreshing` becomes true
- Clear timeout when `isRefreshing` becomes false
- Force completion and call `onRefreshComplete` if timeout fires

### 5. Improve Refresh Completion Logic

**File:** `frontend_clean/src/components/invoices/SmartDiscrepancyWidget.tsx`

**Problem:** Current refresh completion check might have race conditions or miss edge cases.

**Solution:**

- Improve the completion check to be more robust
- Handle case where no invoices need fetching but we're still refreshing
- Ensure completion check runs after state updates settle

**Changes:**

- Refine the refresh completion `useEffect` logic
- Add check for when `uploadedInvoices` changes during refresh
- Ensure completion fires even if invoice list is empty

### 6. Add Invoice List Change Detection (Optional Enhancement)

**File:** `frontend_clean/src/components/invoices/SmartDiscrepancyWidget.tsx`

**Problem:** When invoice list updates with new invoices that have delivery notes, we should ensure they're fetched.

**Solution:**

- The existing logic should handle this, but add explicit check to ensure new invoices trigger fetch
- This is more of a safeguard than a fix

**Changes:**

- Add comment explaining that invoice list changes automatically trigger fetch via existing useEffect
- No code changes needed if current logic works correctly

## Testing Checklist

- [ ] Refresh completes successfully after pairing in DeliveryNotesCardsSection
- [ ] Refresh completes even if some API calls fail
- [ ] Refresh times out after 10 seconds if stuck
- [ ] Upload triggers refresh after invoice list updates
- [ ] Multiple rapid operations don't cause duplicate refreshes
- [ ] Refresh state never gets stuck in loading
- [ ] Error messages logged when refresh fails or times out

## Files to Modify

1. `frontend_clean/src/components/invoices/SmartDiscrepancyWidget.tsx` - Error handling, timeout, completion logic
2. `frontend_clean/src/components/invoices/DeliveryNotesCardsSection.tsx` - Add onPairSuccess callback
3. `frontend_clean/src/pages/Invoices.tsx` - Fix upload timing, add callback for DeliveryNotesCardsSection