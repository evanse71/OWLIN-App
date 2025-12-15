# Invoice ↔ Delivery Note Pairing Workflow - Implementation Complete

## Summary

Successfully implemented a fast manual pairing workflow with consistent suggestions UI and prepared auto-pairing infrastructure. All changes use real SQLite DB data and existing endpoints where possible.

---

## Files Changed

### Backend (4 files)

1. **`backend/main.py`**
   - Added `GET /api/delivery-notes/unpaired` endpoint (after line 713)
   - Returns delivery notes not currently paired (no accepted/confirmed pair)
   - Supports optional filters: venue, supplier, from_date, to_date
   - Uses LEFT JOIN with pairs table to exclude paired DNs

2. **`backend/services/auto_pairing.py`** (NEW FILE)
   - Created `auto_pair_invoice_if_confident(invoice_id)` helper function
   - Automatically pairs invoices with high-confidence suggestions (≥0.9)
   - Reuses existing manual match logic
   - Returns pairing result with status and metadata
   - Not yet wired into creation flows (prepared for future use)

3. **`backend/routes/manual_entry.py`**
   - Added TODO comment at line 220 for auto-pair hook point in `create_manual_invoice()`

4. **`backend/services/ocr_service.py`**
   - Added TODO comment at line 302 for auto-pair hook point after OCR invoice creation

### Frontend (5 files)

1. **`frontend_clean/src/lib/api.ts`**
   - Added `fetchUnpairedDeliveryNotes()` function
   - Calls `GET /api/delivery-notes/unpaired`
   - Supports optional filters (venue, supplier, date range)
   - Returns array of delivery note objects

2. **`frontend_clean/src/pages/Invoices.tsx`**
   - Added manual pairing workflow state:
     - `manualPairingWorkflowActive` (boolean)
     - `activePairingInvoiceId` (string | null)
     - `pairingSuggestions` (PairingSuggestion[])
     - `unpairedDeliveryNotes` (any[])
   - Added useEffect to auto-select first unpaired invoice when entering pairing mode
   - Added useEffect to fetch suggestions and unpaired DNs when active invoice changes
   - Added `handlePairDeliveryNote()` function with auto-advance logic
   - Added `handleToggleManualPairingWorkflow()` function
   - Updated render to show manual pairing column when workflow is active
   - Passes pairing mode props to InvoicesHeader and DocumentDetailPanel

3. **`frontend_clean/src/components/invoices/InvoicesHeader.tsx`**
   - Added props: `manualPairingWorkflowActive`, `onToggleManualPairingWorkflow`
   - Added pairing mode toggle button in header
   - Button shows "✓ Pairing Mode" when active, "Manual Pairing" when inactive
   - Uses primary-action-large style when active, secondary-action when inactive

4. **`frontend_clean/src/components/invoices/DocumentDetailPanel.tsx`**
   - Added props: `manualPairingWorkflowActive`, `topSuggestion`, `onPairWithSuggestion`
   - Enhanced existing "Recommended Delivery Note" card to work with manual pairing mode
   - Shows top suggestion from parent when in manual pairing mode
   - Pair button calls `onPairWithSuggestion` in manual pairing mode

5. **`frontend_clean/src/pages/InvoicesNew.css`**
   - Added styles for manual pairing column
   - Styled DN cards with suggested variant
   - Added confidence badges
   - Added empty state styles
   - Added loading indicator animation

### Tests (1 file)

1. **`tests/test_pairing_workflow.py`** (NEW FILE)
   - Test: `test_suggestions_endpoint_response_shape()` - Verifies suggestions endpoint response
   - Test: `test_unpaired_delivery_notes_endpoint()` - Verifies unpaired DNs are filtered correctly
   - Test: `test_auto_pair_helper_below_threshold()` - Tests auto-pair with low confidence
   - Test: `test_auto_pair_helper_high_confidence()` - Tests auto-pair with high confidence
   - Test: `test_manual_match_endpoint()` - Tests manual pairing endpoint

---

## New Endpoints

### `GET /api/delivery-notes/unpaired`

**Purpose**: Returns delivery notes that are not currently paired with any invoice.

**Query Parameters**:
- `venue` (optional): Filter by venue
- `supplier` (optional): Filter by supplier
- `from_date` (optional): Filter from date (YYYY-MM-DD)
- `to_date` (optional): Filter to date (YYYY-MM-DD)
- `limit` (optional, default 50): Number of results
- `offset` (optional, default 0): Pagination offset

**Response**: Array of delivery note objects
```json
[
  {
    "id": "dn-123",
    "filename": "Delivery Note DN-001.pdf",
    "supplier": "Test Supplier",
    "date": "2025-01-15",
    "doc_date": "2025-01-15",
    "total": 100.0,
    "delivery_note_number": "DN-001",
    "noteNumber": "DN-001",
    "deliveryNo": "DN-001",
    "venue": "Waterloo",
    "venueId": "Waterloo"
  }
]
```

**Logic**: 
- Selects from `documents` where `doc_type='delivery_note'`
- LEFT JOIN with `pairs` table on `pairs.delivery_id = documents.id` AND `pairs.status IN ('accepted', 'confirmed')`
- Excludes rows where a pair exists (`pairs.id IS NULL`)

---

## New Functions

### `auto_pair_invoice_if_confident(invoice_id: str)`

**Location**: `backend/services/auto_pairing.py`

**Purpose**: Automatically pairs an invoice with a high-confidence delivery note suggestion.

**Logic**:
1. Fetches suggestions for the invoice from pairs table (status='suggested')
2. Checks if top suggestion has confidence ≥ 0.9 (AUTO_PAIR_THRESHOLD)
3. If yes, creates/updates pair with status='accepted'
4. Updates `invoices.paired = 1`
5. Runs issue detection (price mismatch, short delivery)
6. Updates invoice status and issues_count

**Returns**:
```python
{
  "paired": True,
  "invoice_id": "inv-123",
  "delivery_id": "dn-456",
  "score": 0.95,
  "status": "matched",  # or "flagged" if issues detected
  "issues_count": 0
}
```

Or:
```python
{
  "paired": False,
  "reason": "below_threshold" | "no_suggestions" | "invoice_not_found" | "already_paired"
}
```

**Not Yet Wired**: Hook points are marked with TODO comments but not actively called. Ready for future activation.

---

## UI Changes

### Manual Pairing Mode

**How to Activate**:
1. Click "Manual Pairing" toggle button in the Invoices page header
2. Button changes to "✓ Pairing Mode" when active

**Layout When Active**:
- **Left Column**: Invoice list (existing DocumentList)
- **Center Column**: Invoice detail card (existing DocumentDetailPanel)
- **Right Column**: Delivery notes column (NEW)

### Right Column: Delivery Notes

**Section A: Suggested for this invoice**
- Shows delivery notes from suggestions endpoint
- Each card displays:
  - Delivery note number
  - Confidence badge (e.g., "95%")
  - Supplier name
  - Date
  - Total amount
  - "Pair" button (primary style)
- Cards have teal border and highlighted background

**Section B: Other unpaired delivery notes**
- Shows other unpaired DNs not in suggestions
- Same card layout as Section A but without confidence badge
- Standard border and background

**Empty States**:
- "No unpaired delivery notes found" - when no DNs available
- "All invoices have been paired!" - when no unpaired invoices remain

### Pairing Interaction

**Click "Pair" button on any DN card**:
1. Calls `POST /api/manual/match` with invoice_id and delivery_note_id
2. Shows success toast: "Delivery note paired successfully"
3. Updates local state:
   - Marks invoice as paired
   - Removes DN from unpaired lists
   - Removes DN from suggestions
4. Auto-advances to next unpaired invoice
5. If no more unpaired invoices, shows "All invoices have been paired!" message

**Error Handling**:
- API errors shown in toast notification
- Errors don't break the UI
- Empty suggestions/DNs handled gracefully

### Invoice Detail Card Enhancement

**When invoice is not paired and suggestions exist**:
- Shows "Suggested Delivery Note" card (or "Recommended Delivery Note" in normal mode)
- Displays: supplier, date, total, confidence score
- "Pair with this delivery note" button
- In manual pairing mode, uses `topSuggestion` prop from parent
- Button calls `onPairWithSuggestion` in manual pairing mode

---

## How to Use Manual Pairing Mode

### Step-by-Step Workflow

1. **Enter Pairing Mode**
   - Click "Manual Pairing" button in Invoices page header
   - First unpaired invoice is automatically selected
   - Right column shows suggested DNs and other unpaired DNs

2. **Review Suggestions**
   - Top suggestions appear in "Suggested" section with confidence badges
   - Other unpaired DNs appear in "Other Unpaired" section
   - Invoice detail card shows top suggestion with "Pair with this delivery note" button

3. **Pair Delivery Note**
   - Click "Pair" button on any DN card in right column
   - OR click "Pair with this delivery note" button in invoice detail card
   - System automatically pairs and advances to next unpaired invoice

4. **Continue Until Complete**
   - System auto-advances through all unpaired invoices
   - When all invoices are paired, shows "All invoices have been paired!" message

5. **Exit Pairing Mode**
   - Click "✓ Pairing Mode" button again to exit
   - Returns to normal 3-column layout with Smart Discrepancy Widget

---

## Technical Details

### Database Schema Used

**invoices table**:
- `id` (TEXT PRIMARY KEY) - Invoice ID
- `doc_id` (TEXT) - References documents.id
- `paired` (INTEGER) - 0 = not paired, 1 = paired

**documents table**:
- `id` (TEXT PRIMARY KEY)
- `doc_type` (TEXT) - 'delivery_note' for DNs
- Fields: supplier, doc_date, total, delivery_no, venue

**pairs table**:
- `invoice_id` (TEXT) - Invoice's doc_id (NOT invoices.id)
- `delivery_id` (TEXT) - Delivery note's documents.id
- `status` (TEXT) - 'suggested', 'accepted', 'confirmed', 'rejected'
- `confidence` (REAL) - Pairing confidence score

### Existing Endpoints Used

- `GET /api/invoices/{invoice_id}/suggestions` - Fetch pairing suggestions
- `POST /api/manual/match` - Manual pairing endpoint
- `GET /api/invoices` - Fetch invoices list
- `GET /api/manual/invoices` - Fetch manual invoices list

### New Endpoints

- `GET /api/delivery-notes/unpaired` - Fetch unpaired delivery notes

---

## Testing

Run tests with:
```bash
pytest tests/test_pairing_workflow.py -v
```

Tests cover:
- Suggestions endpoint response shape
- Unpaired delivery notes endpoint filtering
- Auto-pair helper with various confidence levels
- Manual match endpoint

---

## Future Enhancements

### Auto-Pairing Integration (Prepared, Not Active)

The `auto_pair_invoice_if_confident()` function is ready to be called after:
- Manual invoice creation (`backend/routes/manual_entry.py:220`)
- OCR invoice creation (`backend/services/ocr_service.py:302`)

To activate:
1. Uncomment the TODO lines in those files
2. Add async/await support if needed
3. Consider adding a feature flag to enable/disable auto-pairing

### Additional Improvements

- Add keyboard shortcuts for pairing (e.g., number keys to pair with suggestions)
- Add bulk pairing mode (select multiple invoices, pair all at once)
- Add undo/unpair quick action in pairing mode
- Add filters to unpaired DNs list (by supplier, date range)
- Add search/filter in pairing mode right column

---

## Verification Checklist

- ✅ Backend: Unpaired DNs endpoint created and tested
- ✅ Backend: Auto-pair helper function created
- ✅ Backend: Hook points marked with TODO comments
- ✅ Frontend: Pairing mode state and toggle added
- ✅ Frontend: 3-column layout when pairing mode active
- ✅ Frontend: DN cards with Pair buttons
- ✅ Frontend: Auto-advance logic implemented
- ✅ Frontend: Suggested DN block in invoice card
- ✅ Frontend: Error handling for API failures
- ✅ Frontend: Empty state handling
- ✅ Tests: Created test file with 5 test cases
- ✅ No linting errors
- ✅ All data from real API calls (no dummy data)

---

## Notes

- The existing `pairingMode` state ('automatic' | 'manual') is separate from `manualPairingWorkflowActive` (boolean)
- The existing pairingMode is used by SmartDiscrepancyWidget for its own functionality
- The new manualPairingWorkflowActive controls the dedicated pairing workflow UI
- Both can coexist without conflicts

---

**Implementation Date**: 2025-11-27  
**Status**: ✅ COMPLETE AND READY FOR TESTING

