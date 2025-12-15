# Upload Progress Bar & Card Animations

## Overview
Implemented a smooth, calm upload progress bar and animated card appearance system for the documents section, matching the design reference provided.

## Features Implemented

### 1. Upload Progress Bar Component
**File**: `frontend_clean/src/components/invoices/UploadProgressBar.tsx`

Features:
- **Accurate Progress Tracking**: Shows real-time upload percentage (0-100%)
- **Estimated Time Remaining**: Calculates and displays time left (e.g., "~25s" or "~2m")
- **Smooth Animations**: 
  - Slides in from top with scale animation
  - Progress bar fills smoothly with shimmer effect
  - Completion state with green color transition
  - Auto-hides after 2 seconds when complete
- **Visual States**:
  - Uploading: Blue spinner icon, blue progress bar
  - Complete: Green checkmark icon, green progress bar
- **Design Elements**:
  - Glass morphism effect with backdrop blur
  - Subtle shadows and borders
  - Responsive to dark mode

### 2. Card Slide-In Animations
**File**: `frontend_clean/src/components/invoices/DocumentList.css`

Features:
- **Staggered Appearance**: Cards slide in one after another with 50ms delays
- **Smooth Motion**: Uses cubic-bezier(0.16, 1, 0.3, 1) for natural easing
- **New Upload Highlight**: Special animation for newly uploaded cards:
  - Slides down from above
  - Slight scale bounce effect (1.02x)
  - Settles into place smoothly
- **Initial Load**: All cards animate in when page first loads

### 3. Upload Flow Integration
**File**: `frontend_clean/src/pages/Invoices.tsx`

Features:
- **Progress Tracking**: Real-time percentage updates during upload
- **State Management**:
  - `uploadProgress`: Map of file IDs to percentages
  - `newlyUploadedIds`: Set of recently uploaded invoice IDs
  - `uploadingFiles`: Set of currently uploading files
- **Animation Timing**:
  - Progress bar shows during upload
  - Marks card as "newly uploaded" when complete
  - Removes marker after 1 second (animation duration)
  - Cleans up progress state after 2.5 seconds
- **Toast Notifications**: Success/error messages for user feedback

## User Experience Flow

1. **User Drops/Selects File**
   - Upload begins immediately
   - Progress bar appears at top of documents list

2. **During Upload** (0-99%)
   - Progress bar shows:
     - File name
     - Current percentage (e.g., "46%")
     - Estimated time left (e.g., "~25s")
     - Animated progress fill with shimmer
     - Spinning blue icon

3. **Upload Complete** (100%)
   - Progress bar turns green
   - Checkmark icon appears
   - Shows "Complete" status
   - Auto-hides after 2 seconds

4. **Card Appears**
   - New invoice card slides in from top
   - Slight bounce effect for emphasis
   - Settles into sorted position
   - Animation completes in ~600ms

## Design Specifications

### Progress Bar
- **Height**: 4px progress track
- **Colors**:
  - Uploading: Blue (#3b82f6)
  - Complete: Green (#10b981)
- **Typography**:
  - Filename: 13px, weight 500
  - Stats: 11px, tabular numbers
- **Spacing**: 14px padding, 12px margin-bottom

### Card Animation
- **Duration**: 400ms (staggered), 600ms (newly uploaded)
- **Easing**: cubic-bezier(0.16, 1, 0.3, 1)
- **Transform**: translateY(-10px to 0) + scale(0.98 to 1)
- **Stagger Delay**: 50ms per card

## Technical Implementation

### Time Estimation Algorithm
```typescript
const elapsed = (Date.now() - startTime) / 1000 // seconds
const rate = percentage / elapsed // percentage per second
const remaining = (100 - percentage) / rate // seconds remaining

if (remaining < 60) {
  return `~${Math.ceil(remaining)}s`
} else {
  return `~${Math.ceil(remaining / 60)}m`
}
```

### Animation Keyframes
```css
@keyframes cardSlideIn {
  from {
    opacity: 0;
    transform: translateY(-10px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes newCardAppear {
  0% {
    opacity: 0;
    transform: translateY(-20px) scale(0.95);
  }
  50% {
    opacity: 1;
    transform: translateY(0) scale(1.02);
  }
  100% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
```

## Browser Compatibility
- Modern browsers (Chrome, Firefox, Safari, Edge)
- CSS animations with hardware acceleration
- Backdrop blur with fallback
- Dark mode support via `prefers-color-scheme`

## Performance Considerations
- Hardware-accelerated transforms (translateY, scale)
- Efficient state updates using Maps and Sets
- Cleanup timers to prevent memory leaks
- Minimal re-renders with proper React keys

## Future Enhancements
- Multiple file upload progress (parallel uploads)
- Pause/resume functionality
- Upload queue management
- Drag handle for reordering during upload
- Cancel button for individual uploads

