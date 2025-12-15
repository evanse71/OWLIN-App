---
name: Implement All Invoice Page Buttons
overview: ""
todos: []
---

# Implement All Invoice Page Buttons

## Overview

Currently, many buttons on the invoices page only log to console or have TODO comments. This plan implements full functionality for all buttons.

## Current Status Analysis

### Working Buttons:

- ✅ Upload button (header) - triggers file input
- ✅ Prominent upload zone - drag & drop works
- ✅ View mode toggle - switches between scanned/manual
- ✅ Search - filters invoices
- ✅ Venue/date selectors - work correctly

### Buttons Needing Implementation:

1. **Create manual invoice** - Currently just console.log
2. **Create manual delivery note** - Currently just console.log  
3. **Link delivery note** - Currently just console.log
4. **Change delivery note** - Currently just console.log
5. **View delivery note** - Currently just console.log
6. **Mark as reviewed** - Currently just console.log
7. **Escalate to supplier** - Currently just console.log
8. **Open original PDF** - Not implemented
9. **OCR details** - Not implemented
10. **Save note** (discussion log) - Not implemented

## Implementation Plan

### Phase 1: Create Modal Components

**File: `frontend_clean/src/components/invoices/ManualInvoiceModal.tsx`**

- Modal component for creating manual invoices
- Form fields: supplier, invoice number, date, venue, line items (with add/remove), subtotal, VAT, total
- Submit button calls API endpoint `/api/manual-entry/invoices` (POST)
- On success: refresh invoice list, close modal, show success message

**File: `frontend_clean/src/components/invoices/ManualDeliveryNoteModal.tsx`**

- Modal component for creating manual delivery notes
- Form fields: note number, date, supplier, line items, driver, vehicle, time window
- Submit button calls API endpoint `/api/manual-entry/delivery-notes` (POST)
- On success: refresh data, close modal, show success message

**File: `frontend_clean/src/components/invoices/LinkDeliveryNoteModal.tsx`**

- Modal to select and link existing delivery note to invoice
- Shows list of available delivery notes (fetch from `/api/delivery-notes`)
- Search/filter functionality
- Link button calls API endpoint `/api/invoices/{id}/link-delivery-note` (POST with DN ID)
- On success: refresh invoice detail, close modal

**File: `frontend_clean/src/components/invoices/DeliveryNoteDetailModal.tsx`**

- Modal to view full delivery note details
- Shows all delivery note information including line items
- Fetch from `/api/delivery-notes/{id}` endpoint
- Display-only (no editing)

**File: `frontend_clean/src/components/invoices/OCRDetailsModal.tsx`**

- Modal to show OCR processing details for scanned invoices
- Display OCR confidence scores, extracted text, processing metadata
- Fetch from `/api/invoices/{id}/ocr-details` endpoint

**File: `frontend_clean/src/components/invoices/Modal.css`**

- Shared CSS for all modals (overlay, container, header, body, footer, close button)
- Consistent styling matching the design system

### Phase 2: Implement API Functions

**File: `frontend_clean/src/lib/api.ts`** (add functions)

- `createManualInvoice(data)` - POST to `/api/manual-entry/invoices`
- `createManualDeliveryNote(data)` - POST to `/api/manual-entry/delivery-notes`
- `linkDeliveryNoteToInvoice(invoiceId, deliveryNoteId)` - POST to `/api/invoices/{id}/link-delivery-note`
- `fetchDeliveryNoteDetails(id)` - GET from `/api/delivery-notes/{id}`
- `fetchDeliveryNotes()` - GET from `/api/delivery-notes` (for linking)
- `markInvoiceReviewed(invoiceId)` - POST to `/api/invoices/{id}/mark-reviewed`
- `escalateToSupplier(invoiceId, message?)` - POST to `/api/invoices/{id}/escalate`
- `saveInvoiceNote(invoiceId, note)` - POST to `/api/invoices/{id}/notes`
- `fetchInvoicePDF(invoiceId)` - GET from `/api/invoices/{id}/pdf` (returns blob URL)
- `fetchOCRDetails(invoiceId)` - GET from `/api/invoices/{id}/ocr-details`

### Phase 3: Update Invoices.tsx

**File: `frontend_clean/src/pages/Invoices.tsx`**

- Add state for modals: `showManualInvoiceModal`, `showManualDNModal`, `showLinkDNModal`, `showDNDetailModal`, `showOCRModal`
- Add state for note text: `noteText` and `savingNote`
- Implement `handleNewManualInvoice()` - opens ManualInvoiceModal
- Implement `handleNewManualDN()` - opens ManualDeliveryNoteModal  
- Implement `handleLinkDeliveryNote()` - opens LinkDeliveryNoteModal
- Implement `handleChangeDeliveryNote()` - opens LinkDeliveryNoteModal (same as link)
- Implement `handleViewDeliveryNote()` - fetches DN details and opens DeliveryNoteDetailModal
- Implement `handleMarkReviewed()` - calls API, refreshes invoice list, shows success
- Implement `handleEscalateToSupplier()` - opens confirmation dialog, calls API, shows success
- Implement `handleOpenPDF()` - fetches PDF blob, opens in new tab
- Implement `handleViewOCRDetails()` - fetches OCR details, opens OCRDetailsModal
- Implement `handleSaveNote()` - saves note via API, updates UI, clears textarea
- Pass all handlers to child components
- Add modal components to render tree

### Phase 4: Update DocumentDetailPanel.tsx

**File: `frontend_clean/src/components/invoices/DocumentDetailPanel.tsx`**

- Add props: `onOpenPDF`, `onViewOCRDetails`, `onSaveNote`
- Wire up "Open original PDF" button to `onOpenPDF`
- Wire up "OCR details" button to `onViewOCRDetails`
- Add state for note textarea: `noteText` and `onChange` handler
- Wire up "Save note" button to `onSaveNote` with note text
- Add loading state for save button

### Phase 5: Update IssuesActionsPanel.tsx

**File: `frontend_clean/src/components/invoices/IssuesActionsPanel.tsx`**

- No changes needed - already receives all handlers as props

### Phase 6: Error Handling & Loading States

- Add loading states for all async operations
- Add error handling with user-friendly messages
- Show success notifications after successful operations
- Handle API errors gracefully (network errors, validation errors, etc.)

### Phase 7: Testing Checklist

- [ ] Upload button opens file picker
- [ ] Drag & drop upload works
- [ ] Create manual invoice opens modal and submits successfully
- [ ] Create manual DN opens modal and submits successfully
- [ ] Link delivery note opens modal, shows list, links successfully
- [ ] Change delivery note opens link modal
- [ ] View delivery note shows details modal
- [ ] Mark as reviewed updates invoice status
- [ ] Escalate to supplier sends escalation
- [ ] Open PDF opens PDF in new tab
- [ ] OCR details shows OCR information
- [ ] Save note persists and displays note

## Files to Create:

1. `frontend_clean/src/components/invoices/ManualInvoiceModal.tsx`
2. `frontend_clean/src/components/invoices/ManualDeliveryNoteModal.tsx`
3. `frontend_clean/src/components/invoices/LinkDeliveryNoteModal.tsx`
4. `frontend_clean/src/components/invoices/DeliveryNoteDetailModal.tsx`
5. `frontend_clean/src/components/invoices/OCRDetailsModal.tsx`
6. `frontend_clean/src/components/invoices/Modal.css`

## Files to Modify:

1. `frontend_clean/src/lib/api.ts` - Add API functions
2. `frontend_clean/src/pages/Invoices.tsx` - Implement all handlers
3. `frontend_clean/src/components/invoices/DocumentDetailPanel.tsx` - Wire up PDF/OCR/note buttons

## Notes:

- All modals should follow the existing design system (glassmorphism, light theme)
- API endpoints may need to be created on backend if they don't exist
- Some endpoints may return different data structures - normalize using existing `normalizeSnakeToCamel` utility
- PDF viewing may require backend to serve PDF files or return signed URLs
- OCR details endpoint may not exist yet - implement with graceful fallback