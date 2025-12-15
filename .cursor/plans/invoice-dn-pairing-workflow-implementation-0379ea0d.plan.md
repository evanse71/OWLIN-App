---
name: Manual Delivery Note Form Improvements
overview: ""
todos:
  - id: 3d38174e-1526-4fb6-9ad9-1f34d7f1e428
    content: "Reorder DN form fields to match invoice mode: Supplier first, then Note Number + Date row, then Venue, Line Items, Supervisor, Driver/Vehicle/Time Window"
    status: pending
  - id: e277713a-c58c-4471-b477-22e5ffa562fc
    content: Add supervisor state variable and input field in the form (after Line Items section)
    status: pending
  - id: 9b248345-c54b-4a9d-9edc-f48368ed90c8
    content: Update createManualDeliveryNote API function to include supervisor field in request
    status: pending
  - id: d2efb3f2-59bf-4c30-89a0-a7933c9d8af0
    content: Add supervisor field to ManualDeliveryNoteCreate Pydantic model in backend
    status: pending
  - id: 3af915a9-d0a8-41b0-be72-d5a687af848e
    content: "Update backend to store supervisor in notes field (format: Supervisor: {name}) or separate column"
    status: pending
  - id: 1bf7d0a9-0293-469f-884e-c6a4cb30d556
    content: Test and fix DatePicker calendar month/year navigation if needed
    status: pending
  - id: 0c7dda9f-8a58-4000-bb57-30b924649530
    content: Test complete form submission with all fields including supervisor
    status: pending
---

# Manual Delivery Note Form Improvements

## Overview

Restructure the manual delivery note creation form to match the invoice mode layout, add a supervisor field for tracking who took/supervised the delivery, fix calendar date picker functionality, and improve overall form organization.

## Changes Required

### 1. Restructure Form Field Order (Match Invoice Mode)

**File**: `frontend_clean/src/components/invoices/ManualInvoiceOrDNModal.tsx`

**Current DN Form Order**:

- Note Number + Date (row)
- Supplier
- Venue
- Line Items
- Driver + Vehicle (row)
- Time Window

**New DN Form Order** (matching Invoice mode):

- Supplier (top, full width)
- Note Number + Date (row)
- Venue
- Line Items
- Supervisor (new field)
- Driver + Vehicle (row)
- Time Window

**Implementation**:

- Move Supplier field to the top (before Note Number/Date row)
- Keep Note Number and Date in the same row
- Add Supervisor field after Line Items section
- Maintain Driver, Vehicle, and Time Window as optional fields

### 2. Add Supervisor Field

**Files**:

- `frontend_clean/src/components/invoices/ManualInvoiceOrDNModal.tsx`
- `frontend_clean/src/lib/api.ts`
- `backend/routes/manual_entry.py`

**Frontend Changes**:

- Add `supervisor` state variable: `const [supervisor, setSupervisor] = useState('')`
- Add supervisor input field in the form (after Line Items, before Driver/Vehicle)
- Include supervisor in form submission data
- Add supervisor to copyInvoiceToDN function if applicable

**Backend Changes**:

- Add `supervisor: Optional[str] `field to `ManualDeliveryNoteCreate` model
- Store supervisor in the `notes` field or create a separate `supervisor` column in documents table
- If using `notes` field, format as: `"Supervisor: {name}\n{existing notes}"`
- Update response to include supervisor information

**Database**:

- Option 1: Store in existing `notes` field (simpler, no schema change)
- Option 2: Add `supervisor` column to documents table (requires migration)
- Recommendation: Use Option 1 initially, can migrate later if needed

### 3. Fix Calendar Date Picker

**File**: `frontend_clean/src/components/common/DatePicker.tsx`

**Issues to Fix**:

- Ensure month/year navigation buttons work correctly
- Verify calendar popup opens and closes properly
- Test date selection functionality
- Ensure proper date formatting (YYYY-MM-DD for backend, DD/MM/YYYY for display)

**Current Implementation**:

- DatePicker component already has month/year navigation (ChevronLeft/ChevronRight buttons)
- Has `navigateMonth` and `navigateYear` functions
- May need to verify event handlers are working correctly

**Fixes**:

- Verify `navigateMonth` and `navigateYear` functions are properly implemented
- Ensure click handlers on navigation buttons prevent event propagation
- Test that calendar popup positioning works correctly
- Verify date selection updates the input field correctly

### 4. Additional Beneficial Fields (Optional)

**Consider Adding**:

- **Delivery Reference/PO Number**: Optional field for tracking purchase orders
- **Special Instructions**: Optional notes field for delivery-specific information
- **Delivery Status**: Optional dropdown (Pending, In Transit, Delivered, etc.)

**Decision**: Start with Supervisor field only. Additional fields can be added later if needed.

### 5. Form Validation & UX

**Ensure**:

- Required fields are marked with asterisk (*)
- Optional fields (Supervisor, Driver, Vehicle, Time Window) are clearly optional
- Form maintains consistent styling with invoice mode
- Error messages display correctly
- Loading states work properly

## Implementation Steps

1. **Restructure Form Layout**

- Reorder fields in DN form section (around line 3610-3750)
- Move Supplier to top
- Keep Note Number + Date in row
- Add Supervisor field after Line Items

2. **Add Supervisor State & Field**

- Add state variable
- Add input field in form
- Include in form submission
- Update copyInvoiceToDN function

3. **Update Backend API**

- Add supervisor to ManualDeliveryNoteCreate model
- Store supervisor in notes field (format: "Supervisor: {name}")
- Update response to include supervisor

4. **Fix Calendar**

- Test DatePicker component functionality
- Fix any navigation issues
- Verify date formatting

5. **Test & Verify**

- Test form submission with supervisor
- Verify field order matches invoice mode
- Test calendar navigation
- Verify data is saved correctly

## Files to Modify

1. `frontend_clean/src/components/invoices/ManualInvoiceOrDNModal.tsx`

- Reorder form fields
- Add supervisor state and input field
- Update form submission logic

2. `frontend_clean/src/lib/api.ts`

- Update `createManualDeliveryNote` to include supervisor

3. `backend/routes/manual_entry.py`

- Add supervisor to `ManualDeliveryNoteCreate` model
- Store supervisor in notes field
- Update response

4. `frontend_clean/src/components/common/DatePicker.tsx` (if needed)

- Fix calendar navigation if issues found

## Testing Checklist

- [ ] Form field order matches invoice mode (Supplier first, then Note Number + Date)
- [ ] Supervisor field appears and is optional
- [ ] Supervisor value is saved correctly
- [ ] Calendar date picker allows month/year navigation
- [ ] Date selection works correctly
- [ ] Form submission includes all fields
- [ ] Data displays correctly after creation
- [ ] Copy from invoice function works (if applicable)