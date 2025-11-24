# Owlin Frontend (Clean)

Clean React + TypeScript + Vite implementation of the Owlin Invoices page.

## Features

- **Invoices Upload Page** (`/invoices`) - Drag-and-drop file upload with OCR processing
- **Health Banner** - Real-time backend health status indicator
- **Progress Tracking** - Live upload progress (0→100%) using XMLHttpRequest
- **Parsed Fields Display** - Shows supplier, date, value, and confidence from OCR results
- **Detail Panel** - Click any scanned invoice card to view full details in a side panel (desktop) or accordion (mobile)
- **Developer Mode** - Toggle dev mode to see raw OCR JSON, network timings, and debug information
- **Keyboard Navigation** - Use `j`/`k` to navigate, `Enter` to toggle selection
- **Deep Linking** - Shareable URLs with invoice selection via hash (`#inv-<id>`)

## HOW TO RUN

### Prerequisites

1. **Backend must be running** at `http://127.0.0.1:8000`
   ```powershell
   # In your backend venv
   python -m uvicorn backend.main:app --reload
   ```

2. **Verify backend health:**
   ```powershell
   curl http://127.0.0.1:8000/api/health
   # Expected: {"status":"ok"}
   ```

### Development

1. **Install dependencies:**
   ```powershell
   npm install
   ```

2. **Set API base URL (optional):**
   ```powershell
   # Create .env file if needed
   echo "VITE_API_BASE_URL=http://127.0.0.1:8000" > .env
   ```

3. **Start dev server:**
   ```powershell
   npm run dev
   ```

4. **Open browser:**
   - Navigate to `http://localhost:5173`
   - Should automatically redirect to `/invoices`
   - Health banner should show ✅ green if backend is healthy

### Using the Invoices Page

**Card Selection:**
- Click any scanned invoice card to open the detail panel
- Click the same card again to close it
- Only one card can be selected at a time

**Keyboard Shortcuts:**
- `j` or `↓` - Navigate to next scanned invoice
- `k` or `↑` - Navigate to previous scanned invoice
- `Enter` - Toggle open/close selected invoice
- `Shift + D` - Toggle developer mode

**Layout:**
- **Desktop (≥1024px):** Two-column layout with detail panel on the right
- **Mobile (<1024px):** Single column with inline accordion below selected card

**Deep Linking:**
- When a card is selected, the URL updates to `/invoices#inv-<id>`
- Sharing this URL will auto-select the invoice on page load
- Works with browser back/forward navigation

### Developer Mode

Enable developer mode to see debug information:

**Methods to Enable:**
1. **Query Parameter:** Add `?dev=1` to the URL (e.g., `http://localhost:5173/invoices?dev=1`)
2. **LocalStorage:** Set `owlin_dev=1` in browser localStorage
3. **Keyboard:** Press `Shift + D` while on the page

**What Dev Mode Shows:**
- **DEV badge** in the page header
- **Debug Panel** below the detail panel with:
  - Raw OCR JSON (pretty-printed, truncatable for large responses)
  - Per-page metrics (confidence, words, PSM if available)
  - Network timings (start time, end time, duration, bytes sent)
  - Last 5 requests log (method, URL, status, duration)
  - "Simulate Error" button (DEV only) for UI testing

**Console Logging:**
- Dev mode uses `console.groupCollapsed` with `DEV:` prefix
- Logs selection changes, hash sync, upload lifecycle, and errors
- No spam loops - only meaningful events are logged

### Build

```powershell
npm run build
```

### BRJ Validation

Run all validation checks (typecheck, build, smoke tests):

```powershell
npm run brj:all
```

Individual checks:

```powershell
# Health check only
npm run brj:smoke

# Upload endpoint test only
npm run brj:upload

# UI contract tests (vitest)
npm run brj:ui

# All unit tests (vitest)
npm run test
```

## Non-Negotiable Behaviour Contracts

### FormData Contract
- **FormData key must be exactly `file`** (not `files`, `document`, etc.)
- Backend expects: `POST /api/upload` with `FormData` containing key `file`

### Progress Display Contract
- Progress must show **0→100%** **before** "scanned" state renders
- Progress bar updates in real-time during upload
- Card status transitions: `pending → uploading → scanned | error`

### Health Banner Contract
- Polls backend every **10 seconds** (not more frequently)
- **Never spams console** with errors
- On error, shows red state **and** keeps uploader functional (does not disable)
- Health check endpoint: `GET /api/health` expecting `{"status":"ok"}`

### Upload Response Contract
- Backend must return HTTP 200 with JSON body containing:
  - `supplier?` (string, optional)
  - `date?` (string, optional)
  - `value?` (number, optional)
  - `confidence?` (number, optional)
- All fields are nullable/optional - missing fields are acceptable

### Error Handling Contract
- Network errors surface message: "Network error: Failed to connect to server"
- HTTP errors surface: "Upload failed: {status} {statusText}"
- Parse errors surface: "Failed to parse response: {error}"
- All errors visible on card, no silent failures

## Testing

### Unit Tests (Vitest)

Tests are located in `tests/` directory:

- `tests/upload_xhr.spec.ts` - XMLHttpRequest upload logic with mocked XHR
  - Progress handler receives ascending values (10, 30, 90, 100)
  - Error paths surface messages correctly
  - FormData key contract verification

Run tests:
```powershell
npm run test
```

### Smoke Tests (Node.js)

Integration smoke tests in `tests/brj/`:

- `smoke.js` - Health check validation
- `upload.js` - Upload endpoint validation with real backend

These tests require the backend to be running.

## Project Structure

```
frontend_clean/
├── src/
│   ├── pages/
│   │   └── Invoices.tsx          # Main invoices upload page with selection & layout
│   ├── components/
│   │   ├── HealthBanner.tsx       # Backend health indicator
│   │   ├── InvoiceDetailPanel.tsx # Friendly detail view for selected invoice
│   │   └── InvoiceDebugPanel.tsx  # Dev mode debug drawer with raw JSON & timings
│   ├── lib/
│   │   ├── config.ts              # API configuration
│   │   ├── api.ts                 # Health check helper
│   │   ├── upload.ts              # XMLHttpRequest upload with progress
│   │   └── ui_state.ts            # Selection, devMode, hash sync utilities
│   ├── App.tsx                    # Router setup
│   └── main.tsx                   # Entry point
├── tests/
│   ├── brj/
│   │   ├── smoke.js               # Health check smoke test
│   │   └── upload.js              # Upload smoke test
│   ├── upload_xhr.spec.ts         # Unit tests for upload logic
│   ├── ui_state.spec.ts           # Unit tests for UI state utilities
│   └── invoices_ui.spec.ts        # UI contract tests for Invoices page
└── package.json
```

## Troubleshooting

### CORS Errors
- Ensure backend CORS allows `http://localhost:5173` and `http://127.0.0.1:5173`
- Backend should allow methods: `POST, GET`
- Backend should allow headers: `*` or specific headers

### 413 Payload Too Large
- Backend request size limit too small
- Try uploading a smaller file first
- Increase backend middleware limits

### Wrong Route
- Contract is `POST /api/upload` with FormData key `file`
- If backend differs, align frontend or add compatibility route

### Health Check Fails
- Verify backend is running: `curl http://127.0.0.1:8000/api/health`
- Check `VITE_API_BASE_URL` in `.env` matches backend URL
- Check browser console for network errors

## Next Phase

After Phase 1 validation passes:

- **Persistent Invoice List** - Load previously scanned invoices from SQLite (`/api/invoices/recent`)
- **OCR Debug Panel** - Per-page confidence + PSM display (`/api/ocr/debug`)
- **Delivery Note Pairing** - Visible "Match Delivery Note" status for each card
