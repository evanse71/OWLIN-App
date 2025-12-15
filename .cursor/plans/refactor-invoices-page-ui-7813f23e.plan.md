---
name: Refactor Invoices Page UI
overview: ""
todos:
  - id: f55a27bf-41d6-4e0a-a939-6fd271804af8
    content: Remove viewMode toggle from InvoicesHeader and unify data fetching in Invoices.tsx using Promise.all to merge scanned and manual invoices with stable sort
    status: pending
  - id: 76571a24-1519-454b-bcfa-cdd77508c268
    content: Redesign invoice cards in DocumentList.tsx to be denser with supplier as primary, total prominent, badges row, OCR confidence badge, and Manual badge for consistency
    status: pending
  - id: aecca759-852e-4107-92eb-91b009d8cbde
    content: "Improve DocumentDetailPanel.tsx layout: better header card, cleaner workflow progress, improved invoice & DN section, collapsible line items, discussion header"
    status: pending
  - id: 21e0542a-9d94-4ddb-8f19-5e43d5d3cbe5
    content: Add sticky bottom submission bar to Invoices.tsx with derived readyInvoices count, Clear selection, and Submit all ready invoices buttons (test sticky positioning)
    status: pending
  - id: 4d21bcc1-3efc-4573-961a-67423f931b99
    content: Update sort options in DocumentList.tsx to include Venue and Status options
    status: pending
  - id: 07ec54f1-9343-49bb-9ec9-d002384ecaff
    content: "Polish CSS files: consistent spacing, typography hierarchy, softer Scanned/Manual badge colors, accessibility focus styles, widget-like design aesthetic"
    status: pending
---

# Refactor Invoices Page UI

## Overview

Refactor the Invoices page to create a unified, widget-like design with:

- Single unified documents list (no separate scanned/manual sections)
- Denser, clearer invoice cards with better hierarchy
- Improved right-hand content panel layout
- Sticky bottom submission bar for batch operations

## Current Structure

- `frontend_clean/src/pages/Invoices.tsx` - Main page component with viewMode toggle
- `frontend_clean/src/components/invoices/DocumentList.tsx` - Left column list
- `frontend_clean/src/components/invoices/DocumentDetailPanel.tsx` - Right column detail panel
- `frontend_clean/src/components/invoices/InvoicesHeader.tsx` - Header with viewMode toggle
- `frontend_clean/src/pages/InvoicesNew.css` - Main stylesheet

## Implementation Plan

### Phase 1: Remove ViewMode Toggle & Unify Data Fetching

**File: `frontend_clean/src/pages/Invoices.tsx`**

- Remove `viewMode` state and related logic
- Update `fetchInvoices()` to fetch from both endpoints in parallel and merge results:
  - Use `Promise.all()` to fetch from `/api/invoices` (scanned) and `/api/manual/invoices` (manual) simultaneously
  - Merge into single array, mark each with `status: 'scanned' | 'manual'`
  - Apply stable sort by created date (or invoice date) so manual + scanned don't jump around unexpectedly
  - Ensure consistent ordering regardless of fetch order
- Remove viewMode filtering from `fetchInvoiceDetail()`
- Update `InvoicesHeader` props to remove viewMode-related props

**File: `frontend_clean/src/components/invoices/InvoicesHeader.tsx`**

- Remove viewMode toggle (segmented control)
- Keep search, venue, date range selectors
- Update upload button to always show (not conditional on viewMode)
- Remove `viewMode` prop and related handlers

### Phase 2: Redesign Invoice Cards

**File: `frontend_clean/src/components/invoices/DocumentList.tsx`**

- Redesign card layout to be more compact:
  - **Top row**: Supplier name (bold, primary) + Invoice total (right-aligned, large)
  - **Second row**: Venue (subtle) + Invoice date
  - **Badges row**: Source (Manual/Scanned), Match status (Matched/Unmatched), Ready status (Ready/Draft)
  - **OCR confidence**: Always visible for scanned invoices as badge (e.g., "90% OCR")
  - **Manual badge**: For manual invoices, show "Manual" badge where OCR confidence would be to maintain visual consistency
- Update card styling:
  - Reduce padding from 16px to 12px
  - Make supplier name larger and bolder (font-size: 15px, font-weight: 600)
  - Make total amount prominent (font-size: 18px, font-weight: 700, accent-green color)
  - Improve badge layout (flex-wrap, smaller gaps)
  - Add hover state: subtle lift + brighter outline
  - Selected state: glowing outline (not too loud)

**File: `frontend_clean/src/components/invoices/DocumentList.css`**

- Update `.invoice-card-new` styles for denser layout
- Add new badge styles for OCR confidence
- Add "Manual" badge styling (consistent with OCR badge position)
- Improve spacing and typography hierarchy
- **Accessibility**: Add visible focus styles for keyboard navigation (outline, focus ring) so users can arrow-key through cards

### Phase 3: Improve Right-Hand Content Panel

**File: `frontend_clean/src/components/invoices/DocumentDetailPanel.tsx`**

- **Header card improvements**:
  - Make supplier name more dominant (larger font)
  - Add invoice filename below supplier (smaller, muted)
  - Show invoice date and venue clearly
  - Total amount: large, colored (accent-green)
  - Status chips: Scanned/Manual, Matched/Unmatched, Ready/Submitted
  - OCR confidence chip (for scanned invoices)
  - Buttons: "Open original PDF", "OCR details", "Submit invoice" (if ready)
  
- **Workflow Progress section**:
  - Convert to cleaner checklist format:
    - ✅ Scanned/Imported (with icon)
    - ✅ Issues resolved (with icon)
    - ○ Delivery note linked (with icon)
    - ○ Submitted (with icon)
  - Each step shows icon (CheckCircle2/Circle) + label + optional description
  
- **Invoice & Delivery Note section**:
  - Two side-by-side summary cards (Invoice summary, Delivery note summary)
  - Buttons above: "Link delivery note", "Create manual DN"
  - Line items table below with columns: Item name, Qty (inv vs DN), Unit price, Total, Issue marker
  - Empty state message when no line items
  - **Panel length management**: Keep each section visually tight to prevent panel from getting too long
  - **Collapsible line items**: Consider making "Line items" section collapsible if invoice has many items (>10) - add expand/collapse toggle

- **Discussion & log**:
  - Add subtle header ("Discussion & log")
  - Show timestamped events above input (if available)
  - Keep textarea and save button

**File: `frontend_clean/src/components/invoices/DocumentDetailPanel.css`**

- Improve spacing between sections
- Better typography hierarchy
- Consistent card styling
- Ensure sections stay visually tight

### Phase 4: Add Sticky Submission Bar

**File: `frontend_clean/src/pages/Invoices.tsx`**

- Derive `readyInvoices` from invoices array (don't use separate state):
  ```typescript
  const readyInvoices = invoices.filter((inv) => inv.readyToSubmit);
  ```
- Add `handleClearSelection()` function to reset ready/submission state
- Update `handleBatchSubmit()` to work with ready invoices
- Add sticky bottom bar component:
  - Left: "X invoices ready to submit" (dynamic count from `readyInvoices.length`)
  - Right: "Clear selection" (secondary) + "Submit all ready invoices" (primary)
  - Disabled if count = 0
  - Dark pill-shaped bar, slightly elevated, rounded, soft glow
- **Important**: Check that `position: sticky; bottom: 0` works with existing layout container - may need to apply to inner wrapper rather than body-level element

**File: `frontend_clean/src/pages/InvoicesNew.css`**

- Add `.submission-bar` styles:
  - Position: sticky, bottom: 0
  - Background: dark card color
  - Border-radius: 16px (top corners)
  - Padding: 16px 24px
  - Box-shadow: elevated shadow
  - Display: flex, justify-content: space-between
  - Z-index: 100
  - Margin: 24px (from page edges)
- Test sticky positioning with layout container structure

### Phase 5: Update Sort Options

**File: `frontend_clean/src/components/invoices/DocumentList.tsx`**

- Update sort dropdown to include: Date, Supplier, Venue, Status
- Update `sortBy` type to include 'venue' | 'status'
- Implement sorting logic for all options

**File: `frontend_clean/src/pages/Invoices.tsx`**

- Update `sortBy` state type
- Pass updated sort options to DocumentList

### Phase 6: Design Polish

**File: `frontend_clean/src/pages/InvoicesNew.css`**

- Ensure consistent padding (p-4 or p-5 equivalent)
- Uniform border radius for all cards (12px-16px)
- Improve color hierarchy:
  - Supplier name and totals: primary focus
  - Status chips and meta: secondary
  - **Badge colors**: Use softer colors for "Scanned / Manual" badges (neutral blues/greys), keep bright green/red for semantic meaning (Ready / Issue / Error)
  - Reuse existing palette (greens for success, red/orange for issues, blue/indigo for neutral)
- Dark theme consistency: deep slate background, cards on lighter surface, soft shadows
- **Future consideration**: Consider centralizing shared card styles (`.owlin-card` base class) to avoid touching multiple CSS files in future refactors

**File: `frontend_clean/src/components/invoices/DocumentList.css`**

- Add OCR confidence badge styling
- Add "Manual" badge styling (consistent with OCR badge position)
- Improve badge layout and spacing
- Better hover/selected states
- **Accessibility**: Add visible focus styles for keyboard navigation (outline, focus ring)

## Files to Modify

1. `frontend_clean/src/pages/Invoices.tsx` - Remove viewMode, unify fetching with Promise.all, add submission bar with derived state
2. `frontend_clean/src/components/invoices/InvoicesHeader.tsx` - Remove viewMode toggle
3. `frontend_clean/src/components/invoices/DocumentList.tsx` - Redesign cards, update sort, add Manual badge
4. `frontend_clean/src/components/invoices/DocumentDetailPanel.tsx` - Improve layout, add collapsible line items
5. `frontend_clean/src/pages/InvoicesNew.css` - Update styles, add submission bar styles, softer badge colors
6. `frontend_clean/src/components/invoices/DocumentList.css` - Card and badge improvements, accessibility focus styles
7. `frontend_clean/src/components/invoices/DocumentDetailPanel.css` - Panel improvements, tight spacing

## Acceptance Criteria

- [ ] Single documents column lists both manual and scanned invoices
- [ ] Invoice cards show supplier (primary), date, venue, total, source type, match status, OCR confidence (if available)
- [ ] Manual invoices show "Manual" badge where OCR confidence would be for visual consistency
- [ ] Right-hand panel reads cleanly: header → workflow → invoice & DN → line items → discussion
- [ ] Line items section is collapsible when >10 items
- [ ] Sticky bottom bar shows "X invoices ready to submit" with Submit/Clear buttons
- [ ] Ready invoices count is derived from invoices array (not separate state)
- [ ] All existing functionality preserved (selection, detail panel updates, etc.)
- [ ] No viewMode toggle - all invoices shown together
- [ ] OCR confidence always visible as badge on scanned invoices
- [ ] Design matches widget-like aesthetic (dark background, soft rounded cards, clear hierarchy)
- [ ] Scanned/Manual badges use softer colors (neutral blues/greys)
- [ ] Keyboard navigation works with visible focus styles

## Notes

- Preserve all existing API calls and data structures
- Maintain backward compatibility with backend endpoints
- Keep all modal functionality intact
- Ensure responsive behavior is maintained
- Use Promise.all for parallel fetching to improve performance
- Stable sort ensures consistent ordering of merged invoices
- Derived state prevents state synchronization issues
- Test sticky positioning with actual layout container structure