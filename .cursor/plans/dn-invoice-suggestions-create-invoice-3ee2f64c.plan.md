---
name: Delivery Note Invoice Suggestions & Create Invoice from DN
overview: ""
todos:
  - id: 78558e3d-fb94-48e8-8b3b-37babb9d8fe1
    content: Enhance backend endpoint `/api/delivery-notes/{delivery_note_id}/suggestions` to find matching invoices by supplier and date, calculate confidence scores, and include quantity comparisons
    status: pending
  - id: 84d1dbed-71e3-4627-819b-b7749ac5b056
    content: Add state variables in ManualInvoiceOrDNModal for invoice suggestions (createdDNId, invoiceSuggestions, showInvoiceSuggestions, loadingInvoiceSuggestions)
    status: pending
  - id: a639a920-c3e4-4c71-852a-b3ea8026052d
    content: After DN creation, fetch and display invoice suggestions using fetchInvoiceSuggestionsForDN()
    status: pending
  - id: 7534f8f0-2079-4219-884d-1c5545cb055f
    content: Add UI to display invoice suggestions after DN creation, similar to existing pairing suggestions UI, with quantity difference indicators
    status: pending
  - id: a07ecb48-a951-4a40-9f74-0b648a8fa41a
    content: Add 'Create Invoice from DN' button and function to pre-fill invoice form with DN data and switch to invoice tab
    status: pending
  - id: 7cfa5389-212d-4408-bbd7-32d32448ad0d
    content: After creating invoice from DN, automatically pair the invoice with the delivery note
    status: pending
---

# Delivery Note Invoice Suggestions & Create Invoice from DN

## Overview

After creating a delivery note, users should see invoice suggestions to enable immediate pairing. Additionally, users should be able to create an invoice directly from a delivery note with pre-filled data.

## Implementation Plan

### 1. Backend: Enhance Invoice Suggestions Endpoint for Delivery Notes

**File:** `backend/main.py` (lines 831-990)

**Current State:** The endpoint `/api/delivery-notes/{delivery_note_id}/suggestions` only returns suggestions from the `pairs` table with status='suggested'. This means newly created delivery notes won't have suggestions until pairing suggestions are generated.

**Changes Needed:**

- Enhance `get_delivery_note_suggestions()` to also find invoices that match the delivery note by:
  - Supplier name (case-insensitive match)
  - Date proximity (±3 days)
  - Optionally: amount similarity
- Calculate match confidence score (0.0-1.0) based on:
  - Supplier match: +0.5 base
  - Date proximity: +0.3 for same day, decreasing by 0.1 per day up to 3 days
  - Amount similarity: +0.2 if within 5%
- For each matching invoice, calculate quantity comparison using `validate_quantity_match()`
- Include quantity differences and warnings in response
- Sort suggestions by confidence score (highest first)
- Return both existing pair suggestions AND newly found matching invoices

**Key Logic:**

```python
# After getting DN details, query invoices table for matches
# Match by supplier and date window
# Calculate confidence score
# Run quantity validation for each match
# Combine with existing pair suggestions
# Sort by confidence
```

### 2. Frontend: Show Invoice Suggestions After DN Creation

**File:** `frontend_clean/src/components/invoices/ManualInvoiceOrDNModal.tsx` (lines 364-421)

**Current State:** After DN creation (line 394), the handler just refreshes the list and shows a success message. No suggestions are fetched or displayed.

**Changes Needed:**

- After successful DN creation, extract the delivery note ID from the response
- Add state for invoice suggestions (similar to existing `pairingSuggestions` state for invoices)
- Call `fetchInvoiceSuggestionsForDN()` with the newly created DN ID
- Display suggestions in a similar UI to the invoice pairing suggestions (lines 562-638)
- Allow immediate pairing from suggestions
- Show quantity differences in the suggestion cards

**Key Changes:**

- Add state: `createdDNId`, `invoiceSuggestions`, `showInvoiceSuggestions`, `loadingInvoiceSuggestions`
- In `handleDNSubmit()` after line 394, fetch suggestions:
  ```typescript
  const dnId = response.id || response.deliveryNoteId
  if (dnId) {
    await fetchAndShowInvoiceSuggestions(String(dnId))
  }
  ```

- Create `fetchAndShowInvoiceSuggestions()` function similar to `fetchAndShowPairingSuggestions()`
- Add UI section to display invoice suggestions (similar to lines 562-638 but for invoices)

### 3. Frontend: Add "Create Invoice from DN" Feature

**File:** `frontend_clean/src/components/invoices/ManualInvoiceOrDNModal.tsx`

**Changes Needed:**

- Add a button in the delivery note form (after line 1010, before the footer) to "Create Invoice from DN"
- When clicked, pre-fill the invoice form with:
  - Supplier from DN
  - Date from DN
  - Line items from DN (copy description, qty, unit; leave price/total empty)
  - Venue from DN
- Switch to invoice tab
- After invoice creation, automatically pair the invoice with the delivery note
- Show success message indicating both invoice created and paired

**Key Implementation:**

- Add function `createInvoiceFromDN()` that:

  1. Copies DN data to invoice form fields
  2. Switches to invoice tab
  3. Pre-fills invoice form
  4. Optionally auto-submits or waits for user to add prices and submit

- Add button in DN form: "Create Invoice from This Delivery Note"
- After invoice creation, automatically call `linkDeliveryNoteToInvoice()` with the created invoice ID and DN ID

### 4. Frontend: Update API Function

**File:** `frontend_clean/src/lib/api.ts` (lines 710-737)

**Current State:** `fetchInvoiceSuggestionsForDN()` exists but may need updates to handle the enhanced response format.

**Changes Needed:**

- Ensure the function properly handles the enhanced response with quantity differences
- Update TypeScript interfaces if needed to match backend response
- The function should already work, but verify it handles:
  - `quantityDifferences` array
  - `hasQuantityMismatch` flag
  - `quantityMatchScore`
  - `quantityWarnings` array

### 5. Frontend: Update Invoices Page Success Handler

**File:** `frontend_clean/src/pages/Invoices.tsx` (lines 651-663)

**Current State:** `handleManualInvoiceOrDNSuccess()` only refreshes the invoice list. If a DN was created, it doesn't trigger suggestion fetching.

**Changes Needed:**

- The modal component should handle suggestion fetching internally, so this handler may not need changes
- However, if the modal closes after DN creation, we may need to handle suggestions at the page level
- For now, the modal will handle suggestions internally, so minimal changes needed here

## Success Criteria

- [ ] After creating a delivery note, invoice suggestions are automatically fetched and displayed
- [ ] Suggestions show quantity comparison information
- [ ] Users can pair invoices immediately from suggestions
- [ ] Users can create an invoice from a delivery note with pre-filled data
- [ ] After creating invoice from DN, it is automatically paired
- [ ] Backend endpoint finds matching invoices even if not in pairs table
- [ ] Suggestions are sorted by match confidence

## Files to Modify

1. `backend/main.py` - Enhance `get_delivery_note_suggestions()` endpoint
2. `frontend_clean/src/components/invoices/ManualInvoiceOrDNModal.tsx` - Add suggestion fetching and display after DN creation, add "Create Invoice from DN" feature
3. `frontend_clean/src/lib/api.ts` - Verify/update `fetchInvoiceSuggestionsForDN()` if needed

## Testing Considerations

- Test with newly created delivery notes (no existing pairs)
- Test with delivery notes that have existing pair suggestions
- Test quantity mismatch scenarios
- Test "Create Invoice from DN" with various DN data
- Test auto-pairing after creating invoice from DN
- Verify suggestions are sorted correctly by confidence