---
name: Clear All Non-Paired Delivery Notes Feature
overview: ""
todos:
  - id: 20fc4d9b-d788-4951-8903-50dedb5ea289
    content: Enhance invoice card selection animation in InvoicesNew.css with smooth scale and color transitions
    status: pending
  - id: 43bdf67b-d19c-417b-b358-08830d0bdeb3
    content: Enhance delivery note card selection animation in DeliveryNoteCard.css to match invoice card style
    status: pending
  - id: 67351485-6b56-4e43-a2da-1c6493220220
    content: Create slideDownFadeIn keyframe animation in DocumentDetailPanel.css
    status: pending
  - id: 12ae48fb-3149-421f-ac61-d76650ba3019
    content: Apply sequential animation delays to detail panel widgets (header, line items, pairing widget, etc.)
    status: pending
  - id: bd2fce36-a50f-498a-a9a3-eb374b3550ed
    content: Test animations when switching between invoice and delivery note selections
    status: pending
  - id: 54d6786f-5f75-4c15-a06f-788149351f4c
    content: Create backend endpoint POST /api/delivery-notes/batch/delete to delete non-paired delivery notes
    status: pending
  - id: 0ca8044d-7596-497b-bd27-08d41f84fe91
    content: Add deleteDeliveryNotes API function in frontend_clean/src/lib/api.ts
    status: pending
  - id: 200840ca-1d15-4873-9f82-b6d67724d768
    content: Create ClearDeliveryNotesModal component with two-step confirmation (warning + type DELETE)
    status: pending
  - id: c1e55293-9863-4c8e-85a1-4140b19f18d2
    content: Add batch clear button to DeliveryNotesCardsSection header with modal integration
    status: pending
  - id: ab7301ed-52f3-42c6-9363-d6d0f2f5ec69
    content: Add individual delete button to DeliveryNoteCard component with inline confirmation
    status: pending
  - id: db2c3afc-19f7-4893-bdc0-9a5aa4da0cae
    content: Style delete buttons and confirmation overlays in CSS files
    status: pending
  - id: bfe894e4-e602-41cd-8d77-d2a6f459fe14
    content: "Integrate delete handlers: call API, refresh list, show toasts, clear selection"
    status: pending
---

# Clear All Non-Paired Delivery Notes Feature

## Overview

Add functionality to delete non-paired delivery notes with two approaches:

1. **Batch clear button** in widget header - clears all non-paired DNs with two-step confirmation
2. **Individual delete buttons** on each card - deletes single DN with inline confirmation (similar to invoice cards)

Both features only affect non-paired delivery notes to protect data integrity.

## Changes Required

### 1. Backend: Delete Non-Paired Delivery Notes Endpoint

**File: `backend/routes/invoices_submit.py`**

- Add new endpoint: `POST /api/delivery-notes/batch/delete`
- Create request model: `DeleteDeliveryNotesRequest` with `delivery_note_ids: List[str]`
- Implementation logic:
- Verify each delivery note ID exists in documents table with `doc_type = 'delivery_note'`
- Check if delivery note is paired (exists in pairs table)
- Only delete non-paired delivery notes (skip paired ones)
- Delete associated line items from `line_items` table where `invoice_id IS NULL` and matches DN doc_id
- Delete from documents table
- Return response with `deleted_count`, `skipped_count`, and `message`
- Add audit logging for deletion operations

### 2. Frontend: API Function

**File: `frontend_clean/src/lib/api.ts`**

- Add interface: `DeleteDeliveryNotesResponse` with `deleted_count`, `skipped_count`, `message`, `success`
- Add function: `deleteDeliveryNotes(deliveryNoteIds: string[]): Promise<DeleteDeliveryNotesResponse>`
- Call endpoint: `POST ${API_BASE_URL}/api/delivery-notes/batch/delete`
- Handle errors and return normalized response

### 3. Frontend: Two-Step Confirmation Modal (Batch Delete)

**File: `frontend_clean/src/components/invoices/ClearDeliveryNotesModal.tsx` (new file)**

- Create modal component with two-step confirmation process
- **Step 1 - Warning**:
- Display count: "You are about to delete X non-paired delivery notes"
- Warning message about permanent deletion
- Buttons: "Cancel" and "Continue to Confirm"
- **Step 2 - Type Confirmation**:
- Require user to type "DELETE" in input field
- Confirm button disabled until text matches exactly
- Show validation feedback
- Buttons: "Back", "Cancel", and "Confirm Delete" (disabled until typed correctly)
- Props: `isOpen`, `onClose`, `onConfirm`, `count`, `loading`
- Use existing modal styling from Modal.css

### 4. Frontend: Batch Clear Button in Widget Header

**File: `frontend_clean/src/components/invoices/DeliveryNotesCardsSection.tsx`**

- Add "Clear All" button in widget header (next to title/badge area)
- Button properties:
- Icon: Trash2 from lucide-react
- Small size, subtle styling
- Danger color (red/orange tint)
- Only visible when `filteredDeliveryNotes.length > 0`
- Disabled when `loading` or `pairingLoading`
- State management:
- Add state for batch clear modal: `showClearAllModal`
- Add state for deletion loading: `deletingDNs`
- Handler: `handleClearAllDNs`
- Opens two-step confirmation modal
- On confirmation: calls `deleteDeliveryNotes` with all DN IDs
- Refreshes delivery notes list
- Shows success/error toast
- Clears selected DN if it was deleted

**File: `frontend_clean/src/components/invoices/DeliveryNotesCardsSection.css`**

- Style the clear all button:
- Position in header (flex layout)
- Small padding, subtle appearance
- Danger color scheme (rgba(239, 68, 68, ...))
- Hover effects
- Disabled state styling

### 5. Frontend: Individual Delete Buttons on Cards

**File: `frontend_clean/src/components/invoices/DeliveryNoteCard.tsx`**

- Add delete button to each card (similar to invoice card pattern)
- Add props: `onDelete?: (dnId: string) => void`
- Add state: `isDeleteConfirming` (boolean)
- Delete button:
- Position: absolute, top-right corner
- Icon: Trash2 from lucide-react
- Only visible when `onDelete` prop provided
- Opacity: 0.4 normally, 1.0 on hover
- Click handler stops propagation to prevent card selection
- Delete confirmation overlay:
- Similar to invoice card delete confirmation
- Shows when `isDeleteConfirming` is true
- Overlay with "Are you sure?" message
- Buttons: "Cancel" and "Confirm Delete"
- Click outside to cancel

**File: `frontend_clean/src/components/invoices/DeliveryNoteCard.css`**

- Add styles for delete button:
- `.delivery-note-card-delete-btn` - positioned absolute, top-right
- Opacity transitions
- Red color (#ef4444)
- Size: 24x24px, padding: 4px
- z-index: 20
- Add styles for delete confirmation overlay:
- `.delivery-note-card-delete-confirm` - full card overlay
- Similar to `.invoice-card-delete-confirm` pattern
- Dark background with blur
- Centered confirmation content

**File: `frontend_clean/src/components/invoices/DeliveryNotesCardsSection.tsx`**

- Add handler: `handleDeleteSingleDN(dnId: string)`
- Calls `deleteDeliveryNotes([dnId])` for single deletion
- Refreshes delivery notes list
- Shows toast notification
- Clears `selectedDNId` if deleted DN was selected
- Pass `onDelete={handleDeleteSingleDN}` to each `DeliveryNoteCard`

## Implementation Details

### Safety Features:

- **Batch delete**: Two-step confirmation (warning + type "DELETE")
- **Individual delete**: Single inline confirmation overlay
- **Protection**: Only non-paired DNs can be deleted (backend enforces this)
- **Feedback**: Clear success/error messages via toast
- **State management**: Proper loading states and disabled buttons during operations

### User Experience:

- Batch clear button is subtle but visible in header
- Individual delete buttons appear on hover (low opacity until hover)
- Confirmation prevents accidental deletion
- Immediate visual feedback after deletion
- List refreshes automatically after deletion

## Files to Modify/Create

1. `backend/routes/invoices_submit.py` - Add batch delete endpoint
2. `frontend_clean/src/lib/api.ts` - Add deleteDeliveryNotes function
3. `frontend_clean/src/components/invoices/ClearDeliveryNotesModal.tsx` - New two-step confirmation modal
4. `frontend_clean/src/components/invoices/DeliveryNotesCardsSection.tsx` - Add batch clear button and handlers
5. `frontend_clean/src/components/invoices/DeliveryNotesCardsSection.css` - Style batch clear button
6. `frontend_clean/src/components/invoices/DeliveryNoteCard.tsx` - Add individual delete button
7. `frontend_clean/src/components/invoices/DeliveryNoteCard.css` - Style delete button and confirmation overlay