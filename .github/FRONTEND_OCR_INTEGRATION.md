# Frontend OCR v2 Integration

This document describes the frontend integration with the new OCR v2 pipeline.

## Feature Flags

### Frontend Flags
- `VITE_FEATURE_OCR_V2` (Vite) or `NEXT_PUBLIC_FEATURE_OCR_V2` (Next.js)
- Default: `false` (disabled)
- Controls whether the frontend calls the new OCR v2 endpoint

### Backend Flags
- `FEATURE_OCR_PIPELINE_V2`
- Default: `false` (disabled)
- Controls whether the backend processes requests with the new pipeline

## Usage

### Enable OCR v2 (Full Stack)

1. **Backend**: Set `FEATURE_OCR_PIPELINE_V2=true`
2. **Frontend**: Set `VITE_FEATURE_OCR_V2=true` (or `NEXT_PUBLIC_FEATURE_OCR_V2=true`)
3. **API Base URL**: Set `VITE_API_BASE_URL=http://127.0.0.1:8000` (or `NEXT_PUBLIC_API_BASE_URL`)

### Environment Files

#### Vite (.env.local)
```env
VITE_FEATURE_OCR_V2=true
VITE_API_BASE_URL=http://127.0.0.1:8000
```

#### Next.js (.env.local)
```env
NEXT_PUBLIC_FEATURE_OCR_V2=true
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

#### Backend (.env)
```env
FEATURE_OCR_PIPELINE_V2=true
OCR_ARTIFACT_ROOT=data/uploads
```

## Components

### UploadCard
- **Location**: `src/components/invoices/UploadCard.tsx`
- **Features**:
  - Feature flag banner (shows current state)
  - Progress bar during processing
  - Error handling with "Copy error" button
  - Success state with confidence and artifact path
  - Abort functionality

### ErrorNotice
- **Location**: `src/components/common/ErrorNotice.tsx`
- **Features**:
  - Copy error to clipboard
  - Dismiss functionality
  - Clean error display

### API Integration
- **Location**: `src/lib/api/ocrV2.ts`
- **Features**:
  - TypeScript types for OCR responses
  - Fetch wrapper with error handling
  - Abort signal support

## Testing

### Test Scenarios

1. **Both flags OFF**: Upload card shows "OCR v2 is off" message
2. **Frontend ON, Backend OFF**: Shows "Backend flag disabled" error
3. **Both flags ON**: Full OCR processing with progress and results

### Manual Testing

1. Start backend: `uvicorn backend.main:app --reload`
2. Start frontend: `npm run dev`
3. Navigate to Invoices page
4. Upload a PDF and observe the behavior

## File Structure

```
src/
├── lib/
│   ├── featureFlags.ts          # Feature flag configuration
│   └── api/
│       └── ocrV2.ts            # OCR v2 API client
├── components/
│   ├── common/
│   │   └── ErrorNotice.tsx     # Reusable error component
│   └── invoices/
│       └── UploadCard.tsx      # Enhanced upload card
└── pages/
    └── InvoicesPage.tsx        # Invoices page with OCR integration
```

## Error Handling

The integration includes comprehensive error handling:

- **Network errors**: Displayed with copy functionality
- **Backend errors**: Parsed and shown with context
- **Feature flag mismatches**: Clear messaging about required flags
- **Abort functionality**: Cancel in-progress requests

## Progress States

The upload card shows clear progress states:

- **0%**: No file selected
- **25%**: File selected, starting upload
- **50%**: Upload in progress
- **75%**: Processing complete, finalizing
- **100%**: Complete with results

## Results Display

Successful OCR processing shows:

- **Confidence score**: Overall confidence percentage
- **Page count**: Number of pages processed
- **Artifact path**: Location of saved files
- **Trace ID**: For debugging and support
