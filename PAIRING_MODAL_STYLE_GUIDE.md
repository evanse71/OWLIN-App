# Pairing Modal Style Guide

## Design System Integration

The Review Pairing modal now follows the application's glass morphism design system with consistent styling across all components.

## Key Style Patterns

### 1. Glass Morphism Containers

```css
background: rgba(255, 255, 255, 0.03);
border: 1px solid rgba(255, 255, 255, 0.1);
border-radius: 12px;
backdrop-filter: blur(10px);
```

**Used in:**
- Match score section
- Warnings section
- Table containers
- Line items comparison cards

### 2. Color Coding System

#### Severity Levels
- **Critical:** `var(--accent-red)` - #ef4444
- **Warning:** `var(--accent-yellow)` - #f59e0b
- **Info:** `var(--accent-blue)` - #3b82f6
- **Success:** `var(--accent-green)` - #22c55e

#### Application
- Match score values (high/medium/low)
- Table row backgrounds
- Severity badges
- Border accents
- Difference values (positive/negative)

### 3. Typography Hierarchy

```css
/* Section Headers */
font-size: 1.1rem;
font-weight: 600;
color: var(--text-primary);

/* Table Headers */
font-size: 12px;
font-weight: 600;
text-transform: uppercase;
letter-spacing: 0.5px;
color: var(--text-secondary);

/* Body Text */
font-size: 13px;
color: var(--text-primary);
line-height: 1.5;

/* Numeric Values */
font-family: 'SF Mono', 'Monaco', 'Courier New', monospace;
font-weight: 500-700;
```

### 4. Button Styling

```css
/* Primary Action */
.glass-button.primary-action {
  /* Inherits glass button styles */
  /* Prominent for main actions */
}

/* Secondary Action */
.glass-button.secondary-action {
  /* Inherits glass button styles */
  /* Subtle for cancel/back actions */
}
```

### 5. Table Design

#### Header Row
```css
background: rgba(255, 255, 255, 0.05);
border-bottom: 2px solid rgba(255, 255, 255, 0.1);
```

#### Body Rows
```css
/* Default */
background: transparent;
border-bottom: 1px solid rgba(255, 255, 255, 0.05);

/* Hover */
background: rgba(255, 255, 255, 0.03);

/* Critical Severity */
background: rgba(239, 68, 68, 0.08);
border-left: 3px solid var(--accent-red);

/* Warning Severity */
background: rgba(251, 191, 36, 0.08);
border-left: 3px solid var(--accent-yellow);

/* Info Severity */
background: rgba(59, 130, 246, 0.08);
border-left: 3px solid var(--accent-blue);
```

### 6. Badge Design

```css
.severity-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border-radius: 8px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  backdrop-filter: blur(10px);
}

/* Critical Badge */
background: rgba(239, 68, 68, 0.15);
color: var(--accent-red);
border: 1px solid rgba(239, 68, 68, 0.3);

/* Warning Badge */
background: rgba(251, 191, 36, 0.15);
color: var(--accent-yellow);
border: 1px solid rgba(251, 191, 36, 0.3);

/* Info Badge */
background: rgba(59, 130, 246, 0.15);
color: var(--accent-blue);
border: 1px solid rgba(59, 130, 246, 0.3);
```

### 7. Progress Bar

```css
/* Container */
.match-score-bar {
  width: 100%;
  height: 10px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

/* Fill */
.match-score-fill {
  height: 100%;
  background: linear-gradient(90deg, 
    var(--accent-red) 0%, 
    var(--accent-yellow) 50%, 
    var(--accent-green) 100%
  );
  transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 0 10px rgba(255, 255, 255, 0.2);
}
```

### 8. Notification Boxes

#### Success Message
```css
background: rgba(34, 197, 94, 0.08);
border: 1px solid rgba(34, 197, 94, 0.25);
border-left: 4px solid var(--accent-green);
border-radius: 12px;
backdrop-filter: blur(10px);
```

#### Error Message
```css
background: rgba(239, 68, 68, 0.08);
border: 1px solid rgba(239, 68, 68, 0.25);
border-left: 4px solid var(--accent-red);
border-radius: 12px;
backdrop-filter: blur(10px);
```

#### Warning Section
```css
background: rgba(251, 191, 36, 0.08);
border: 1px solid rgba(251, 191, 36, 0.25);
border-left: 4px solid var(--accent-yellow);
border-radius: 12px;
backdrop-filter: blur(10px);
```

## Spacing System

### Padding
- **Small:** 0.875rem (14px)
- **Medium:** 1.25rem (20px)
- **Large:** 1.5rem (24px)

### Margins
- **Section spacing:** 1.5rem (24px)
- **Element spacing:** 0.75rem (12px)
- **Tight spacing:** 0.5rem (8px)

### Gaps
- **Flex/Grid gaps:** 0.75rem - 1rem (12px - 16px)
- **Icon gaps:** 0.375rem - 0.5rem (6px - 8px)

## Border Radius

- **Small elements:** 8px (badges, buttons)
- **Medium containers:** 12px (cards, sections)
- **Large elements:** 16px (modals)

## Transitions

```css
/* Standard transition */
transition: all 0.2s ease;

/* Smooth easing */
transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);

/* Background transitions */
transition: background-color 0.2s ease;
```

## Responsive Breakpoints

### Mobile (≤768px)
- Single column layouts
- Reduced padding (1rem)
- Smaller font sizes
- Compact badges
- Adjusted table cell padding

```css
@media (max-width: 768px) {
  .pairing-preview-modal {
    max-width: 95vw;
    margin: 1rem;
  }
  
  .comparison-grid {
    grid-template-columns: 1fr;
  }
  
  .match-score-value {
    font-size: 1.25rem;
  }
}
```

## Accessibility Features

1. **Focus States:** All interactive elements have visible focus indicators
2. **Color Contrast:** All text meets WCAG AA standards
3. **Semantic HTML:** Proper heading hierarchy and table structure
4. **Icon Labels:** Icons paired with text for clarity
5. **Keyboard Navigation:** Full keyboard support for all interactions

## Component Composition

### Match Score Section
```
┌─────────────────────────────────────┐
│ Quantity Match Score          85%   │ ← Header with value
│ ████████████████░░░░░░░░░░░░░░░░░  │ ← Gradient progress bar
└─────────────────────────────────────┘
```

### Warnings Section
```
┌─────────────────────────────────────┐
│ ⚠️  Warnings                        │ ← Icon + header
│ • Warning message 1                 │
│ • Warning message 2                 │
└─────────────────────────────────────┘
```

### Discrepancies Table
```
┌──────────────────────────────────────────────────┐
│ ITEM        │ INVOICE QTY │ DELIVERY QTY │ ... │ ← Headers
├──────────────────────────────────────────────────┤
│ Item 1      │    10.00    │    12.00     │ ... │ ← Row (color-coded)
│ Item 2      │     5.00    │     5.00     │ ... │
└──────────────────────────────────────────────────┘
```

### Severity Badge
```
┌──────────────┐
│ ⚠️ CRITICAL  │ ← Icon + text, color-coded
└──────────────┘
```

## Implementation Notes

1. **CSS Variables:** Always use CSS variables for colors to maintain consistency
2. **Backdrop Blur:** Use `backdrop-filter: blur(10px)` for glass morphism effect
3. **Border Colors:** Use `rgba(255, 255, 255, 0.1)` for subtle borders
4. **Hover Effects:** Add subtle background changes on hover for interactive elements
5. **Monospace Fonts:** Use for all numeric values to improve readability and alignment

## Future Enhancements

1. Dark mode support (already using CSS variables)
2. Animation on modal open/close
3. Skeleton loading states for table rows
4. Expandable row details for discrepancies
5. Export functionality for discrepancy data

---

This style guide ensures consistency across the pairing modal and can be referenced when creating or updating similar components in the application.

