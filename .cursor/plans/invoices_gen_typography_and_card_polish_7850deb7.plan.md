---
name: Invoices Gen Typography and Card Polish
overview: Apply typography scale and card polish to the /invoices-gen experimental page to achieve a clean, high-end, Apple-inspired widget aesthetic. Update all component styles with consistent typography classes, refined card shadows/borders, and improved visual hierarchy.
todos:
  - id: create-typography-scale
    content: Add typography scale classes (h1, h2, label, body, micro), text color utilities, card shell classes, and divider utility to invoices-gen.css
    status: completed
  - id: polish-upload-bar
    content: Update UploadBarGen.tsx with typography classes and UploadBarGen.css with refined dropzone styling and gradient background
    status: completed
    dependencies:
      - create-typography-scale
  - id: polish-invoice-cards
    content: Restructure InvoiceColumnGen.tsx card content with typography classes, update InvoiceColumnGen.css with refined spacing and card styling
    status: completed
    dependencies:
      - create-typography-scale
  - id: polish-delivery-cards
    content: Restructure DeliveryNoteColumnGen.tsx card content with typography classes, update DeliveryNoteColumnGen.css with refined styling
    status: completed
    dependencies:
      - create-typography-scale
  - id: polish-detail-view
    content: Apply typography classes to DetailViewGen.tsx, add divider, update DetailViewGen.css with enhanced card styling (20px radius, better shadow)
    status: completed
    dependencies:
      - create-typography-scale
  - id: polish-analysis-assistant
    content: Apply typography classes to AnalysisAssistantGen.tsx, update AnalysisAssistantGen.css with radial gradient and refined styling (22px radius)
    status: completed
    dependencies:
      - create-typography-scale
  - id: polish-review-footer
    content: Apply typography classes to ReviewFooterGen.tsx, update ReviewFooterGen.css with enhanced styling (20px radius, better shadow) for CTA bar feel
    status: completed
    dependencies:
      - create-typography-scale
  - id: verify-visual-polish
    content: Verify all components have consistent typography, refined card styling, and improved visual hierarchy matching the Apple-inspired aesthetic
    status: completed
    dependencies:
      - polish-upload-bar
      - polish-invoice-cards
      - polish-delivery-cards
      - polish-detail-view
      - polish-analysis-assistant
      - polish-review-footer
---

# Invoices Gen Typography + Card Polish Pass

## Overview

Refine the experimental `/invoices-gen` page with a comprehensive typography and styling pass to achieve a clean, high-end, Apple-inspired widget aesthetic. All changes are styling-only, no logic modifications.

## Implementation Steps

### Step 1: Create Typography Scale and Utility Classes

**File**: `frontend_clean/src/styles/invoices-gen.css`

Add typography scale classes:

- `.invoices-gen__h1` - 20px, 600 weight, 1.4 line-height
- `.invoices-gen__h2` - 16px, 600 weight, 1.4 line-height
- `.invoices-gen__label` - 13px, 500 weight
- `.invoices-gen__body` - 14px, 400 weight, 1.5 line-height
- `.invoices-gen__micro` - 12px, 400 weight, 1.5 line-height

Add text color utilities:

- `.invoices-gen__text-muted` - #6b7280
- `.invoices-gen__text-soft` - #9ca3af

Add card shell classes:

- `.invoices-gen-card` - 18px radius, white background, subtle border, shadow
- `.invoices-gen-card--subtle` - 16px radius, lighter shadow

Add divider utility:

- `.invoices-gen-divider` - gradient line divider

### Step 2: Update UploadBarGen Typography and Styling

**File**: `frontend_clean/src/components/invoices-gen/UploadBarGen.tsx`

- Apply typography classes to title, subtitle, and hint
- Add card classes to dropzone

**File**: `frontend_clean/src/components/invoices-gen/UploadBarGen.css`

- Remove background from wrapper, apply only to dropzone
- Update dropzone with gradient background
- Refine padding and spacing
- Update active state styling

### Step 3: Polish Invoice Cards

**File**: `frontend_clean/src/components/invoices-gen/InvoiceColumnGen.tsx`

- Apply typography classes to header (label, micro)
- Restructure card content: supplier as body, invoice number as micro uppercase, total as h2
- Add divider between meta and footer
- Apply card classes

**File**: `frontend_clean/src/components/invoices-gen/InvoiceColumnGen.css`

- Update card padding and gap spacing
- Refine hover and selected states
- Update status pill styling
- Adjust typography sizing

### Step 4: Polish Delivery Note Cards

**File**: `frontend_clean/src/components/invoices-gen/DeliveryNoteColumnGen.tsx`

- Apply typography classes to header
- Restructure card content similar to invoice cards
- Apply card classes with subtle variant

**File**: `frontend_clean/src/components/invoices-gen/DeliveryNoteColumnGen.css`

- Update card styling to match invoice cards but lighter
- Refine spacing and typography
- Update status pill colors (blue theme)

### Step 5: Refine Detail View Card

**File**: `frontend_clean/src/components/invoices-gen/DetailViewGen.tsx`

- Apply typography classes throughout
- Add divider between sections
- Update placeholder text styling

**File**: `frontend_clean/src/components/invoices-gen/DetailViewGen.css`

- Increase border radius to 20px
- Enhance shadow for "floaty widget" feel
- Refine padding and spacing
- Update section and field row styling

### Step 6: Polish Analysis Assistant

**File**: `frontend_clean/src/components/invoices-gen/AnalysisAssistantGen.tsx`

- Apply typography classes to all text elements

**File**: `frontend_clean/src/components/invoices-gen/AnalysisAssistantGen.css`

- Update border radius to 22px
- Add radial gradient background
- Enhance shadow for depth
- Refine typography sizing

### Step 7: Refine Review Footer

**File**: `frontend_clean/src/components/invoices-gen/ReviewFooterGen.tsx`

- Apply typography classes to title and subtitle

**File**: `frontend_clean/src/components/invoices-gen/ReviewFooterGen.css`

- Update border radius to 20px
- Enhance shadow and border
- Refine padding and spacing
- Make it feel like a deliberate CTA bar

## File Changes Summary

**Modified Files:**

- `frontend_clean/src/styles/invoices-gen.css` - Add typography scale and utilities
- `frontend_clean/src/components/invoices-gen/UploadBarGen.tsx` - Apply typography classes
- `frontend_clean/src/components/invoices-gen/UploadBarGen.css` - Refine dropzone styling
- `frontend_clean/src/components/invoices-gen/InvoiceColumnGen.tsx` - Restructure card content, apply classes
- `frontend_clean/src/components/invoices-gen/InvoiceColumnGen.css` - Polish card styling
- `frontend_clean/src/components/invoices-gen/DeliveryNoteColumnGen.tsx` - Restructure card content, apply classes
- `frontend_clean/src/components/invoices-gen/DeliveryNoteColumnGen.css` - Polish card styling
- `frontend_clean/src/components/invoices-gen/DetailViewGen.tsx` - Apply typography classes, add divider
- `frontend_clean/src/components/invoices-gen/DetailViewGen.css` - Enhance card styling
- `frontend_clean/src/components/invoices-gen/AnalysisAssistantGen.tsx` - Apply typography classes
- `frontend_clean/src/components/invoices-gen/AnalysisAssistantGen.css` - Refine dark widget styling
- `frontend_clean/src/components/invoices-gen/ReviewFooterGen.tsx` - Apply typography classes
- `frontend_clean/src/components/invoices-gen/ReviewFooterGen.css` - Enhance footer styling

## Visual Goals

- Upload bar: Big hero drop card with clear hierarchy
- Invoice/DN cards: Job-card aesthetic with supplier bold, meta uppercase, amount prominent
- Detail card: Large, floaty widget with clear sections
- Analysis panel: Dark finance widget chip with proper typography
- Review footer: Deliberate CTA bar, not just a line