---
name: Pairing System Enhancements Plan
overview: ""
todos:
  - id: 5a9c23bf-578e-4fa4-a1be-e68e4fe4409a
    content: Review existing invoice/dn models and routes
    status: pending
  - id: 96dd0697-a825-4419-87f2-5a531612d7f6
    content: Plan pairing engine, db updates, endpoints
    status: pending
---

# Pairing System Enhancements Plan

## Overview

This plan implements four key improvements to the pairing system:

1. Supplier stats computation script (improves pairing accuracy)
2. Pairing analytics/metrics endpoint (visibility into system performance)
3. Enhanced error messages (better UX)
4. Auto-refresh after pairing (improved workflow)

## Implementation Steps

### 1. Supplier Stats Computation Script

**File**: `backend/scripts/compute_supplier_stats.py` (new)

Create a script that analyzes historical delivery notes to compute supplier statistics:

- Query all delivery notes grouped by supplier (and optionally venue)
- Compute typical delivery weekdays (most common days of week deliveries occur)
- Calculate average days between deliveries
- Calculate standard deviation of days between deliveries
- Use `upsert_supplier_stats()` from `backend/app/db.py` to save results
- Support command-line arguments for:
  - `--supplier-id`: Compute stats for specific supplier only
  - `--venue-id`: Filter by venue
  - `--min-deliveries`: Minimum number of deliveries required (default: 3)
  - `--dry-run`: Show what would be computed without saving

**Key logic**:

- Group delivery notes by normalized supplier name and venue
- Extract delivery dates and compute weekday distribution
- Calculate inter-delivery intervals (days between consecutive deliveries)
- Use statistical functions (mean, stddev) for intervals
- Handle edge cases (single delivery, missing dates)

### 2. Pairing Analytics Endpoint

**File**: `backend/routes/pairing_router.py` (update)

Add new endpoint: `GET /api/pairing/stats`

**Response model**:

```python
class PairingStatsResponse(BaseModel):
    total_invoices: int
    paired_count: int
    unpaired_count: int
    suggested_count: int
    auto_paired_count: int
    manual_paired_count: int
    avg_confidence: Optional[float]
    pairing_rate_7d: float  # Percentage paired in last 7 days
    pairing_rate_30d: float  # Percentage paired in last 30 days
    recent_activity: List[Dict]  # Last 10 pairing events
```

**Implementation**:

- Query `invoices` table for status counts
- Query `pairing_events` for recent activity and rates
- Calculate average confidence from paired invoices
- Return aggregated statistics

### 3. Enhanced Error Messages

**File**: `backend/routes/pairing_router.py` (update)

Improve error handling in existing endpoints:

**`confirm_pairing()`**:

- Check if delivery note is already paired to another invoice
- Check if invoice is already paired to a different delivery note
- Return specific error messages:
  - "Delivery note is already paired to invoice {invoice_id}"
  - "Invoice is already paired to delivery note {dn_id}. Unpair first or use reassign."
  - Validate delivery note exists and is a delivery note type

**`reassign_pairing()`**:

- Check if new delivery note is already paired
- Check if new delivery note exists
- Return specific errors for each case

**`unpair_invoice()`**:

- Already has good error handling, but ensure message is clear

**General improvements**:

- Add validation helper functions
- Return HTTP 409 (Conflict) for pairing conflicts
- Return HTTP 400 (Bad Request) for validation errors
- Include helpful context in error messages

### 4. Auto-refresh After Pairing

**File**: `frontend_clean/src/components/invoices/DocumentDetailPanel.tsx` (update)

After successful pairing:

- Refresh pairing suggestions for the current invoice
- Update invoice detail to show new pairing status
- Clear any cached suggestion data
- Optionally show a success message

**Implementation**:

- In `handlePairWithDN()` or similar pairing handlers:
  - After successful API call, call `fetchPairingSuggestions()` again
  - Update local state to reflect new pairing
  - Trigger parent component refresh if needed

**File**: `frontend_clean/src/pages/Invoices.tsx` (update)

- After successful pairing in manual workflow:
  - Refresh pairing suggestions for the next invoice
  - Update invoice list to show new pairing status
  - Ensure UI reflects current state

## Files to Modify

1. **New**: `backend/scripts/compute_supplier_stats.py`
2. **Update**: `backend/routes/pairing_router.py` (add stats endpoint, improve errors)
3. **Update**: `frontend_clean/src/components/invoices/DocumentDetailPanel.tsx` (auto-refresh)
4. **Update**: `frontend_clean/src/pages/Invoices.tsx` (auto-refresh)
5. **Update**: `frontend_clean/src/lib/api.ts` (add fetchPairingStats function)

## Testing Considerations

1. **Supplier Stats Script**:

   - Test with various supplier/venue combinations
   - Test with minimal data (1-2 deliveries)
   - Test dry-run mode
   - Verify stats are computed correctly

2. **Analytics Endpoint**:

   - Test with empty database
   - Test with various pairing statuses
   - Verify calculations are correct

3. **Error Messages**:

   - Test all error scenarios
   - Verify HTTP status codes are appropriate
   - Check error messages are user-friendly

4. **Auto-refresh**:

   - Test pairing flow end-to-end
   - Verify suggestions update after pairing
   - Check no duplicate API calls

## Dependencies

- Uses existing `upsert_supplier_stats()` from `backend/app/db.py`
- Uses existing `insert_pairing_event()` for audit trail
- No new database migrations required
- No new external dependencies

## Success Criteria

- Supplier stats script can be run and produces accurate statistics
- Analytics endpoint returns useful pairing metrics
- Error messages are clear and actionable
- UI automatically refreshes after pairing without manual intervention