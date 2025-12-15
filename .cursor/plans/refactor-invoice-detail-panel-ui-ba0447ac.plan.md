---
name: Animated Border and Remove Blur
overview: ""
todos: []
---

# Animated Border and Remove Blur

## Overview

Remove blur effect from selected invoice card and create an animated flowing light border around the content card that visually connects to the selected invoice card in the list.

## Changes Required

### 1. Remove Blur from Selected Invoice Card

**File**: `frontend_clean/src/components/invoices/DocumentList.css`

- Check for any `backdrop-filter: blur()` or `filter: blur()` on `.invoice-card-new.selected`
- Remove any blur effects that may have been added

### 2. Create Animated Border Around Content Card

**File**: `frontend_clean/src/components/invoices/DocumentDetailPanel.css`

- Add a thin animated border (2-3px) around the entire `.invoices-detail-column-selected` container
- Border should follow the widget boundaries (just outside the card edges)
- Use CSS animations with multiple light sources/origins
- Colors: Blue (#3b82f6) and Purple (#a855f7 or similar)
- Animation should be subtle but visible
- Multiple animated gradients/particles flowing around the border

### 3. Connect Border to Selected Invoice Card

**File**: `frontend_clean/src/components/invoices/DocumentDetailPanel.css` and `DocumentList.css`

- Extend the animated border to visually connect to the selected invoice card
- Lights should converge/flow toward the selected invoice card's vertical position
- Create a visual "bridge" or "stream" of light from content card to invoice card
- Lights should flow into and around the selected invoice card
- Remove the existing blue left border on `.invoice-card-new.selected::before`
- Replace with the animated light effect that's brighter around the invoice card

### 4. Add Spacing Around Selected Invoice Card

**File**: `frontend_clean/src/components/invoices/DocumentList.css` or `InvoicesNew.css`

- Add margin-top and margin-bottom to `.invoice-card-new.selected` to create spacing
- This enhances visibility of which card is selected
- Spacing should be subtle (8-12px above and below)

### 5. Animation Implementation Details

**Border Animation:**

- Use CSS `@keyframes` with multiple light sources
- Create flowing gradient animations around the border
- Use `linear-gradient` with blue and purple colors
- Multiple animation delays for different light sources
- Animation should loop continuously
- Use `box-shadow` or `border-image` with animated gradients

**Connection Animation:**

- Create a visual connection line/stream from content card to invoice card
- Use pseudo-elements (::before, ::after) for the connection
- Animate particles/lights flowing along the connection
- Brighter intensity around the invoice card area

## Implementation Approach

### CSS Animation Strategy:

1. Use `border-image` with animated gradient (if supported)
2. Or use multiple `box-shadow` layers with different animation delays
3. Or use pseudo-elements positioned around the border with animated backgrounds
4. Use `conic-gradient` or `linear-gradient` for flowing light effect
5. Multiple keyframe animations with different timings for natural flow

### Visual Connection:

- Use absolute positioning to create a connection line
- Calculate position based on selected card's vertical position
- Animate lights flowing along the connection path
- Use CSS transforms and opacity for smooth animation

## Files to Modify

1. `frontend_clean/src/components/invoices/DocumentDetailPanel.css` - Animated border around content card
2. `frontend_clean/src/components/invoices/DocumentList.css` - Remove blur, add spacing, animated highlight
3. `frontend_clean/src/pages/InvoicesNew.css` - May need spacing adjustments

## Technical Considerations

- Performance: Use `transform` and `opacity` for animations (GPU accelerated)
- Browser compatibility: Fallback for browsers that don't support advanced gradients
- Responsive: Ensure animation works on different screen sizes
- Accessibility: Ensure animation doesn't cause motion sickness (consider `prefers-reduced-motion`)