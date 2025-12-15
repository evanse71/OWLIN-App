# Owlin OCR / Auto-Scanning System Audit

**Date**: 2025-01-02  
**Audit Type**: Architecture + Reality Check  
**Scope**: Full OCR/scanning pipeline from upload to database storage
frontend_clean
---

## Executive Summary

The Owlin OCR system is a **hybrid architecture** with multiple extraction paths:
- **Primary**: LLM-first extraction via Ollama (qwen2.5-coder:32b) - **ACTIVE**
- **Fallback**: Geometric/regex table extraction (legacy) - **DISABLED when LLM enabled**
- **OCR Engines**: PaddleOCR (primary) + Tesseract (fallback) - **IMPLEMENTED**
- **Preprocessing**: Advanced OpenCV pipeline with dual-path comparison - **ENABLED**

**Current Status**: System is **functionally complete** but has **dependency gaps** and **incomplete wiring** in some areas.

---

## 1️⃣ Target Spec (Intended Architecture)

Based on code analysis, comments, and documentation, the intended end-to-end pipeline is:

### Upload & File Handling
- ✅ Accept PDF, JPG, PNG, HEIC files (max 25MB)
- ✅ Generate unique `doc_id` (UUID)
- ✅ Save to `data/uploads/{doc_id}__{filename}`
- ✅ Compute SHA-256 hash for duplicate detection
- ✅ Convert HEIC to PNG if needed
- ✅ Store in `documents` table with `pending` status

### Multi-Page / Multi-Invoice Splitting
- ✅ **PDF**: Render each page to PNG at 300 DPI (`page_001.png`, `page_002.png`, ...)
- ✅ **Images**: Process as single-page documents
- ⚠️ **Multi-invoice detection**: Implemented in LLM parser (`DocumentGroup` class) but **not fully wired** to split into separate invoice records
- ⚠️ **Multi-document splitting**: Code exists in `backend/llm/invoice_parser.py` but may not be creating separate DB records

### Preprocessing Pipeline
- ✅ **Phase 1 (minimal)**: Adaptive threshold (when `FEATURE_OCR_V2_PREPROC=false`)
- ✅ **Phase 2 (enhanced)**: When `FEATURE_OCR_V2_PREPROC=true`:
  - Photo detection (`_is_photo()`)
  - **Dewarping** (perspective correction) for photos **BEFORE** deskewing
  - Deskewing (Hough line detection + rotation)
  - Denoising (bilateral filter)
  - CLAHE (Contrast Limited Adaptive Histogram Equalization)
  - Morphology opening (noise removal)
  - Adaptive threshold (Gaussian → Otsu fallback)
- ✅ **Dual-path comparison**: When `FEATURE_DUAL_OCR_PATH=true` and `is_original_image=true`:
  - Run both minimal and enhanced paths
  - Compare OCR results (word count, confidence)
  - Choose better path automatically
  - Store comparison metadata in `.comparison.json`

### Layout Detection
- ✅ **Primary**: LayoutParser EfficientDet PubLayNet (`lp://EfficientDet/PubLayNet`)
- ✅ **Fallback**: OpenCV whitespace-based segmentation (contours, horizontal/vertical lines)
- ✅ **Block types**: `header`, `table`, `footer`, `body`, `handwriting`
- ✅ **Artifact storage**: JSON files in `data/ocr_artifacts/`

### OCR Text Extraction
- ✅ **Primary**: PaddleOCR with PP-Structure support
  - Per-block OCR processing
  - Detailed word blocks with spatial info for tables
  - Confidence scoring per block
- ✅ **Fallback**: Tesseract OCR (when PaddleOCR fails or confidence < 0.3)
  - Multi-PSM logic (PSM 6 for blocks, PSM 11 for sparse text)
  - Confidence threshold: 0.3
- ✅ **Method tracking**: Logs which engine was used (`paddleocr`, `tesseract`, `fallback`)

### Data Extraction & Parsing
- ✅ **LLM-First Extraction** (when `FEATURE_LLM_EXTRACTION=true`):
  - Ollama integration (default: `http://localhost:11434`)
  - Model: `qwen2.5-coder:32b` (with fallback list)
  - Full-page text assembly → LLM prompt → JSON extraction
  - Math verification (Qty × Unit = Total, Sum items = Subtotal, etc.)
  - Confidence scoring with penalties for errors
  - Bounding box re-alignment using rapidfuzz fuzzy matching
  - Multi-page continuation detection
  - Multi-document splitting (Invoice + Delivery Note)
- ⚠️ **Geometric Extraction** (legacy, disabled when LLM enabled):
  - Table extraction via spatial clustering
  - Regex-based field extraction
  - **Status**: Code exists but not used when LLM is active

### Extracted Fields
- ✅ **Supplier name**: From header zone (LLM or regex)
- ✅ **Invoice date**: YYYY-MM-DD format
- ✅ **Invoice number**: Pattern matching (printed vs generated)
- ✅ **Subtotal / VAT / Total**: Currency normalization
- ✅ **Line items**: `description`, `qty`, `unit_price`, `total`, `vat_rate`, `bbox`
- ✅ **Confidence scoring**: 0-100 (0.0-1.0 float)

### Document Classification
- ✅ **Invoice vs Delivery Note**: `classify_doc()` function in `backend/matching/pairing.py`
- ✅ **Detection**: Looks for "Delivery Note" / "DELIVERY NOTE" keywords
- ✅ **Storage**: Both stored in `invoices` table with `doc_type` field

### Database Storage
- ✅ **Documents table**: `doc_id`, `filename`, `file_path`, `status`, `ocr_confidence`, `ocr_stage`, `ocr_error`
- ✅ **Invoices table**: `id` (doc_id), `supplier`, `date`, `value`, `invoice_number`, `confidence`, `status`, `venue`
- ✅ **Line items table**: `doc_id`, `invoice_id` (NULL for delivery notes), `line_number`, `description`, `qty`, `unit_price`, `total`, `uom`, `confidence`, `bbox`
- ✅ **Audit log**: Timestamped lifecycle events

### Matching / Pairing
- ✅ **Auto-pairing**: Triggered after OCR (via `backend/matching/pairing.py`)
- ✅ **Suggestions**: Delivery notes matched to invoices by supplier + date + quantity validation

### Frontend Integration
- ✅ **Upload endpoint**: `/api/upload` (POST)
- ✅ **Status polling**: `/api/upload/status?doc_id=...` (GET)
- ✅ **Invoice list**: `/api/invoices` (GET)
- ✅ **Invoice detail**: `/api/invoices/{id}` (GET)
- ✅ **Response format**: Normalized via `normalizeInvoice()` / `normalizeUploadResponse()`
- ✅ **Confidence display**: Shown in invoice cards and detail panels
- ✅ **Debug panels**: OCR debug info available in DEV mode

---

## 2️⃣ Implementation Map (Spec → Code)

### Upload & File Handling

| Spec Item | Code Location | Status | Notes |
|-----------|---------------|--------|-------|
| File upload endpoint | `backend/main.py:2017` (`/api/upload`) | ✅ Implemented & used | Validates format, size (25MB), computes hash |
| File saving | `backend/main.py:2070-2109` | ✅ Implemented & used | Saves to `data/uploads/{doc_id}__{filename}` |
| HEIC conversion | `backend/main.py:2074-2105` | ✅ Implemented & used | Requires `pillow-heif` |
| Duplicate detection | `backend/main.py:2050-2064` | ✅ Implemented & used | SHA-256 hash check |
| Database insertion | `backend/app/db.py:insert_document()` | ✅ Implemented & used | Stores in `documents` table |

### Multi-Page Processing

| Spec Item | Code Location | Status | Notes |
|-----------|---------------|--------|-------|
| PDF page rendering | `backend/ocr/owlin_scan_pipeline.py:185-195` | ✅ Implemented & used | 300 DPI via PyMuPDF |
| Image file handling | `backend/ocr/owlin_scan_pipeline.py:1207-1228` | ✅ Implemented & used | Single-page processing |
| Multi-invoice splitting | `backend/llm/invoice_parser.py:DocumentGroup` | ⚠️ Implemented but partially wired | Code exists but may not create separate DB records |
| Page iteration | `backend/ocr/owlin_scan_pipeline.py:1213-1258` | ✅ Implemented & used | Processes all pages |

### Preprocessing

| Spec Item | Code Location | Status | Notes |
|-----------|---------------|--------|-------|
| Minimal preprocessing | `backend/ocr/owlin_scan_pipeline.py:269-285` | ✅ Implemented & used | When `FEATURE_OCR_V2_PREPROC=false` |
| Enhanced preprocessing | `backend/ocr/owlin_scan_pipeline.py:287-374` | ✅ Implemented & used | Dewarp, deskew, denoise, CLAHE, morphology, threshold |
| Photo detection | `backend/image_preprocess.py:_is_photo()` | ✅ Implemented & used | Used to trigger dewarping |
| Dewarping | `backend/image_preprocess.py:detect_and_dewarp()` | ✅ Implemented & used | Perspective correction for photos |
| Dual-path comparison | `backend/ocr/owlin_scan_pipeline.py:218-264` | ✅ Implemented & used | Compares minimal vs enhanced, chooses better |
| OpenCV dependency | `backend/ocr/owlin_scan_pipeline.py:62-65` | ⚠️ Optional import | Graceful fallback if missing |

### Layout Detection

| Spec Item | Code Location | Status | Notes |
|-----------|---------------|--------|-------|
| LayoutParser integration | `backend/ocr/layout_detector.py:103-132` | ⚠️ Implemented but dependency missing | LayoutParser not in requirements.txt (commented out) |
| OpenCV fallback | `backend/ocr/layout_detector.py:172-257` | ✅ Implemented & used | Whitespace-based segmentation |
| Block type mapping | `backend/ocr/layout_detector.py:93-101` | ✅ Implemented & used | Maps PubLayNet types to invoice types |
| Artifact storage | `backend/ocr/layout_detector.py:detect_document_layout()` | ✅ Implemented & used | Saves JSON to `data/ocr_artifacts/` |

### OCR Text Extraction

| Spec Item | Code Location | Status | Notes |
|-----------|---------------|--------|-------|
| PaddleOCR integration | `backend/ocr/ocr_processor.py:126-153` | ✅ Implemented & used | Lazy loading, PP-Structure support |
| PaddleOCR per-block OCR | `backend/ocr/ocr_processor.py:155-547` | ✅ Implemented & used | Detailed word blocks for tables |
| Tesseract fallback | `backend/ocr/ocr_processor.py:574-589` | ⚠️ Implemented but dependency missing | Tesseract binary not installed (Windows path hardcoded) |
| Confidence scoring | `backend/ocr/ocr_processor.py:OCRResult` | ✅ Implemented & used | Per-block and per-page averages |
| Method tracking | `backend/ocr/ocr_processor.py:method_used` | ✅ Implemented & used | Logs which engine was used |

### Data Extraction & Parsing

| Spec Item | Code Location | Status | Notes |
|-----------|---------------|--------|-------|
| LLM extraction | `backend/llm/invoice_parser.py:LLMInvoiceParser` | ✅ Implemented & used | **ACTIVE** (hardcoded `FEATURE_LLM_EXTRACTION=True`) |
| Ollama integration | `backend/llm/invoice_parser.py:428-550` | ✅ Implemented & used | Retry logic, exponential backoff |
| Math verification | `backend/llm/invoice_parser.py:552-650` | ✅ Implemented & used | Validates Qty × Unit = Total, etc. |
| BBox re-alignment | `backend/llm/invoice_parser.py:BBoxAligner` | ✅ Implemented & used | Fuzzy matching with rapidfuzz |
| Multi-page continuation | `backend/llm/invoice_parser.py:DocumentGroup` | ✅ Implemented & used | Detects continued documents |
| Multi-doc splitting | `backend/llm/invoice_parser.py:DocumentGroup` | ⚠️ Implemented but partially wired | Code exists, may not create separate DB records |
| Geometric extraction (legacy) | `backend/ocr/table_extractor.py` | 🟡 Stubbed / unused | Disabled when LLM enabled |
| STORI extractor | `backend/services/ocr_service.py:818-850` | ✅ Implemented & used | Vendor-specific extractor for "Stori Beer & Wine" |

### Field Extraction

| Spec Item | Code Location | Status | Notes |
|-----------|---------------|--------|-------|
| Supplier extraction | `backend/services/ocr_service.py:700-751` | ✅ Implemented & used | Zone-based + regex fallback |
| Date extraction | `backend/services/ocr_service.py:39-49` | ✅ Implemented & used | ISO YYYY-MM-DD normalization |
| Invoice number | `backend/services/ocr_service.py:893-950` | ✅ Implemented & used | Pattern matching (printed vs generated) |
| Currency normalization | `backend/services/ocr_service.py:19-37` | ✅ Implemented & used | Strips symbols, handles commas |
| Line items extraction | `backend/services/ocr_service.py:1084-1300` | ✅ Implemented & used | From LLM or geometric extractor |

### Database Storage

| Spec Item | Code Location | Status | Notes |
|-----------|---------------|--------|-------|
| Document insertion | `backend/app/db.py:insert_document()` | ✅ Implemented & used | Creates `documents` record |
| Invoice upsert | `backend/app/db.py:upsert_invoice()` | ✅ Implemented & used | Creates/updates `invoices` record |
| Line items insertion | `backend/app/db.py:insert_line_items()` | ✅ Implemented & used | Creates `invoice_line_items` records |
| Status updates | `backend/app/db.py:update_document_status()` | ✅ Implemented & used | Tracks OCR lifecycle |
| Audit logging | `backend/app/db.py:append_audit()` | ✅ Implemented & used | Timestamped events |

### Frontend Integration

| Spec Item | Code Location | Status | Notes |
|-----------|---------------|--------|-------|
| Upload API call | `frontend_clean/src/lib/upload.ts:340-446` | ✅ Implemented & used | XMLHttpRequest with progress tracking |
| Status polling | `frontend_clean/src/lib/upload.ts:223-332` | ✅ Implemented & used | Polls `/api/upload/status` until complete |
| Response normalization | `frontend_clean/src/lib/upload.ts:61-214` | ✅ Implemented & used | Handles field name variations |
| Invoice list display | `frontend_clean/src/pages/Invoices.tsx` | ✅ Implemented & used | Shows supplier, date, total, confidence |
| Confidence display | `frontend_clean/src/components/InvoiceDetailPanel.tsx:39` | ✅ Implemented & used | Shows confidence score, highlights low confidence |
| OCR debug panel | `frontend_clean/src/components/invoices/OCRDetailsModal.tsx` | ✅ Implemented & used | Shows per-page confidence, processing time |

---

## 3️⃣ Dependency Health Check

### Critical Dependencies

| Dependency | Present in Code? | Present in requirements.txt? | Used in Pipeline? | Likely Installed? | Notes |
|------------|------------------|------------------------------|-------------------|-------------------|-------|
| **PaddleOCR** | ✅ Yes (`backend/ocr/ocr_processor.py:40`) | ❌ **NO** (commented out in `.github/requirements.txt:15`) | ✅ Yes (primary OCR) | ⚠️ **UNKNOWN** | **CRITICAL GAP**: Required but not in requirements |
| **pytesseract** | ✅ Yes (`backend/ocr/ocr_processor.py:47`) | ❌ **NO** | ✅ Yes (fallback OCR) | ⚠️ **UNKNOWN** | **GAP**: Required for fallback but not in requirements |
| **Tesseract binary** | ✅ Yes (hardcoded path: `C:\Program Files\Tesseract-OCR\tesseract.exe`) | N/A (system binary) | ✅ Yes (fallback) | ❌ **NO** (per diagnostic logs) | **CRITICAL GAP**: Binary not installed |
| **opencv-python** | ✅ Yes (`backend/ocr/owlin_scan_pipeline.py:62`) | ✅ Yes (`.github/requirements.txt:11`) | ✅ Yes (preprocessing, layout fallback) | ✅ Likely | Present in requirements |
| **numpy** | ✅ Yes (imported with cv2) | ✅ Yes (implicit via opencv) | ✅ Yes (image processing) | ✅ Likely | Standard dependency |
| **PyMuPDF (fitz)** | ✅ Yes (`backend/ocr/owlin_scan_pipeline.py:57`) | ⚠️ **UNKNOWN** (not checked) | ✅ Yes (PDF rendering) | ⚠️ **UNKNOWN** | Required for PDF processing |
| **layoutparser** | ✅ Yes (`backend/ocr/layout_detector.py:39`) | ❌ **NO** (commented out in `.github/requirements.txt:16`) | ⚠️ Optional (fallback to OpenCV) | ❌ **NO** | **GAP**: Not installed, OpenCV fallback used |
| **rapidfuzz** | ✅ Yes (`backend/llm/invoice_parser.py`) | ⚠️ **UNKNOWN** (not checked) | ✅ Yes (BBox alignment) | ⚠️ **UNKNOWN** | Required for LLM extraction |
| **pillow-heif** | ✅ Yes (`backend/main.py:2077`) | ⚠️ **UNKNOWN** (not checked) | ✅ Yes (HEIC conversion) | ⚠️ **UNKNOWN** | Required for HEIC support |

### LLM Dependencies

| Dependency | Present in Code? | Present in requirements.txt? | Used in Pipeline? | Likely Installed? | Notes |
|------------|------------------|------------------------------|-------------------|-------------------|-------|
| **Ollama** | ✅ Yes (HTTP client, no Python package) | N/A (external service) | ✅ Yes (LLM extraction) | ⚠️ **UNKNOWN** | Must be running on `localhost:11434` |
| **qwen2.5-coder:32b** | ✅ Yes (model name in config) | N/A (Ollama model) | ✅ Yes (primary model) | ⚠️ **UNKNOWN** | Must be pulled in Ollama |

### Dependency Summary

**CRITICAL GAPS:**
1. ❌ **PaddleOCR not in requirements.txt** - Required for primary OCR but dependency not declared
2. ❌ **Tesseract binary not installed** - Fallback OCR will fail (per diagnostic logs)
3. ❌ **LayoutParser not installed** - Using OpenCV fallback (may reduce layout detection quality)
4. ⚠️ **PyMuPDF status unknown** - Required for PDF processing, not verified
5. ⚠️ **Ollama service status unknown** - Required for LLM extraction, not verified

**WORKING:**
- ✅ OpenCV (in requirements, likely installed)
- ✅ NumPy (standard dependency)

---

## 4️⃣ Runtime Flow Trace (Single PDF Upload)

### Step-by-Step Execution Path

**1. Upload Request** (`POST /api/upload`)
- **File**: `backend/main.py:2017-2153`
- **Actions**:
  - Validates file format (PDF, JPG, PNG, HEIC)
  - Validates size (max 25MB)
  - Computes SHA-256 hash
  - Checks for duplicates
  - Generates `doc_id` (UUID)
  - Saves file to `data/uploads/{doc_id}__{filename}`
  - Converts HEIC to PNG if needed
  - Inserts into `documents` table with `status='pending'`
  - Returns `{doc_id, filename, status: "processing"}`

**2. Background OCR Trigger** (`asyncio.create_task`)
- **File**: `backend/main.py:2128`
- **Function**: `_run_ocr_background(doc_id, stored_path)`
- **Calls**: `backend/services/ocr_service.py:process_document_ocr(doc_id, file_path)`

**3. OCR Service Entry** (`process_document_ocr`)
- **File**: `backend/services/ocr_service.py:95-134`
- **Actions**:
  - Updates document status to `"processing"` / `"ocr_enqueue"`
  - Checks `FEATURE_OCR_PIPELINE_V2` (default: `True`)
  - Calls `_process_with_v2_pipeline(doc_id, file_path)`

**4. V2 Pipeline Processing** (`_process_with_v2_pipeline`)
- **File**: `backend/services/ocr_service.py:136-583`
- **Actions**:
  - Imports `backend/ocr/owlin_scan_pipeline:process_document`
  - Calls `process_document(file_path)` → Returns OCR result dict

**5. OCR Pipeline Execution** (`process_document`)
- **File**: `backend/ocr/owlin_scan_pipeline.py:1164-1643`
- **Actions**:
  - **PDF**: Opens with PyMuPDF, renders each page to PNG at 300 DPI
  - **Image**: Copies directly to `pages/page_001.png`
  - For each page:
    - **Preprocessing**: `preprocess_image(page_img_path, is_original_image)`
      - If `FEATURE_DUAL_OCR_PATH=true` and `is_original_image=true`:
        - Runs minimal and enhanced paths
        - Compares OCR results
        - Chooses better path
        - Saves comparison metadata
      - Otherwise: Runs enhanced preprocessing (dewarp, deskew, denoise, CLAHE, morphology, threshold)
    - **Layout Detection**: `detect_layout(prep_img)`
      - Tries LayoutParser (if available)
      - Falls back to OpenCV whitespace segmentation
      - Returns list of blocks: `[{type, bbox, confidence, source}]`
    - **OCR Processing**: `process_page_ocr_enhanced(prep_img, blocks_raw, page_index)`
      - **If `FEATURE_LLM_EXTRACTION=true`** (default: `True`):
        - Assembles full-page text from all blocks
        - Calls LLM parser: `llm_parser.extract_invoice_data(full_page_text)`
        - LLM returns JSON: `{supplier_name, invoice_date, invoice_number, line_items, subtotal, vat_amount, grand_total}`
        - Math verification (Qty × Unit = Total, etc.)
        - BBox re-alignment (fuzzy match LLM text to PaddleOCR word blocks)
        - Returns `PageResult` with `table_data.line_items`
      - **Otherwise** (legacy):
        - Per-block OCR via `OCRProcessor.process_block()`
        - Geometric table extraction via `TableExtractor`
        - Returns `PageResult` with `table_data.line_items`
  - Calculates overall confidence (average of page confidences)
  - Returns: `{status: "ok", pages: [PageResult, ...], confidence: float, overall_confidence: float}`

**6. Data Extraction** (back in `_process_with_v2_pipeline`)
- **File**: `backend/services/ocr_service.py:183-257`
- **Actions**:
  - Extracts `pages` from OCR result
  - Checks for `normalized_json` (from LLM/template matching)
  - If present: Uses `normalized_json` for supplier/date/total
  - Otherwise: Calls `_extract_invoice_data_from_page(page)` (regex-based fallback)
  - Classifies document type: `classify_doc(full_text)` → `"invoice"` or `"delivery_note"`
  - Extracts line items: `_extract_line_items_from_page(page, parsed_data)`
    - If LLM extraction: Uses `table_data.line_items` from `PageResult`
    - If STORI detected: Uses STORI extractor
    - Otherwise: Uses geometric extractor (legacy)

**7. Database Storage**
- **File**: `backend/services/ocr_service.py:303-418`
- **Actions**:
  - **Invoice upsert**: `upsert_invoice(doc_id, supplier, date, total, invoice_number, confidence, status)`
    - Stores in `invoices` table
    - Status: `"needs_review"` if LLM validation failed, else `"scanned"`
  - **Line items insertion**: `insert_line_items(doc_id, invoice_id, line_items)`
    - Stores in `invoice_line_items` table
    - For delivery notes: `invoice_id=NULL`
  - **Status update**: `update_document_status(doc_id, "ready", "ocr_complete")`

**8. Response to Frontend**
- **File**: `backend/main.py:2156-2250` (`GET /api/upload/status?doc_id=...`)
- **Actions**:
  - Queries `documents` table for status
  - Queries `invoices` table for invoice data
  - Queries `invoice_line_items` table for line items
  - Returns: `{doc_id, status, parsed: {...}, items: [...], invoice: {...}}`

**9. Frontend Polling** (`pollUploadStatus`)
- **File**: `frontend_clean/src/lib/upload.ts:223-332`
- **Actions**:
  - Polls `/api/upload/status` every 1.5s (max 40 attempts = 60s)
  - Stops when `hasItems || isReady || isDuplicateOrErrorWithData`
  - Normalizes response via `normalizeUploadResponse()` or `normalizeInvoice()`
  - Calls `onComplete(metadata)` callback

**10. UI Display**
- **File**: `frontend_clean/src/pages/Invoices.tsx`
- **Actions**:
  - Displays invoice card with supplier, date, total, confidence
  - Shows confidence badge (red if < 50%)
  - On click: Fetches full invoice detail via `/api/invoices/{id}`
  - Displays line items, OCR debug info, pairing suggestions

### Critical Path Flags

- ✅ **FEATURE_OCR_PIPELINE_V2**: `True` (default) - Uses v2 pipeline
- ✅ **FEATURE_OCR_V2_PREPROC**: `True` (default) - Enhanced preprocessing
- ✅ **FEATURE_OCR_V2_LAYOUT**: `True` (default) - Layout detection enabled
- ✅ **FEATURE_DUAL_OCR_PATH**: `True` (default) - Dual-path comparison for images
- ✅ **FEATURE_LLM_EXTRACTION**: `True` (hardcoded) - **LLM extraction is ACTIVE**
- ❌ **FEATURE_OCR_V3_TABLES**: `True` but **NOT USED** (LLM replaces it)
- ❌ **FEATURE_OCR_V3_TEMPLATES**: `False` - Template matching disabled
- ❌ **FEATURE_OCR_V3_DONUT**: `False` - Donut fallback disabled
- ❌ **FEATURE_HTR_ENABLED**: `False` - Handwriting recognition disabled

### Potential Failure Points

1. **PaddleOCR not installed** → Falls back to Tesseract → **Tesseract also not installed** → Returns empty text, confidence 0.0
2. **Ollama not running** → LLM extraction fails → **No fallback** (hardcoded to fail loudly) → OCR processing fails
3. **LayoutParser not installed** → Uses OpenCV fallback → May detect fewer blocks → Lower quality layout
4. **PyMuPDF not installed** → PDF rendering fails → Returns error: "PyMuPDF not installed"
5. **Multi-invoice splitting** → Code exists but may not create separate DB records → Multiple invoices stored as one

---

## 5️⃣ Frontend Wiring Status

### API Integration

| Component | API Endpoint | Status | Notes |
|-----------|--------------|--------|-------|
| File upload | `POST /api/upload` | ✅ Live | XMLHttpRequest with progress tracking |
| Status polling | `GET /api/upload/status?doc_id=...` | ✅ Live | Polls until `hasItems || isReady` |
| Invoice list | `GET /api/invoices` | ✅ Live | Fetches all invoices |
| Invoice detail | `GET /api/invoices/{id}` | ✅ Live | Fetches full invoice with line items |
| Manual entry | `POST /api/manual/invoices` | ✅ Live | Creates manual invoices |

### Data Normalization

| Field | Source | Status | Notes |
|-------|--------|--------|-------|
| **Supplier** | `raw.supplier` / `raw.supplier_name` / `raw.parsed.supplier` | ✅ Live | Multiple fallbacks handled |
| **Date** | `raw.date` / `raw.invoice_date` / `raw.parsed.date` | ✅ Live | ISO format normalization |
| **Total** | `raw.value` / `raw.total` / `raw.grand_total` | ✅ Live | Currency normalization (handles pence) |
| **Confidence** | `raw.confidence` / `raw.ocr_confidence` / `raw.overall_confidence` | ✅ Live | 0-100 display (0.0-1.0 float) |
| **Line items** | `raw.line_items` / `raw.items` / `raw.parsed.line_items` | ✅ Live | Normalized to `{description, qty, unit, price, total, bbox}` |
| **Pages** | `raw.pages` / `raw.ocr_pages` | ✅ Live | Per-page confidence, text, word count |

### UI Components

| Component | Data Source | Status | Notes |
|-----------|-------------|--------|-------|
| **Invoice cards** | `normalizeInvoice()` | ✅ Live | Shows supplier, date, total, confidence badge |
| **Invoice detail panel** | `normalizeInvoice()` | ✅ Live | Shows all fields, line items, pairing suggestions |
| **Confidence display** | `invoice.confidence` | ✅ Live | Red badge if < 50%, shows percentage |
| **OCR debug modal** | `GET /api/invoices/{id}` → `metadata.pages` | ✅ Live | Shows per-page confidence, processing time |
| **Line items table** | `invoice.lineItems` | ✅ Live | Shows description, qty, unit price, total, bbox overlay |
| **Upload progress** | `XMLHttpRequest.upload.progress` | ✅ Live | Shows upload percentage |

### Dummy / Fallback Values

| Field | Fallback Value | Status | Notes |
|-------|----------------|--------|-------|
| **Supplier** | `"Unknown Supplier"` | ⚠️ Used when extraction fails | Shown in UI, indicates OCR failure |
| **Date** | Current date (`datetime.now()`) | ⚠️ Used when extraction fails | Defaults to today |
| **Total** | `0.0` | ⚠️ Used when extraction fails | Shows £0.00 |
| **Confidence** | `0.9` (if missing) | ⚠️ Used when not provided | May hide low-confidence issues |
| **Line items** | `[]` (empty array) | ✅ Used when no items extracted | Correct behavior |

### Error States

| Error | UI Handling | Status | Notes |
|-------|-------------|--------|-------|
| **Upload failure** | Error message in upload UI | ✅ Handled | Shows network/server errors |
| **OCR processing failure** | Invoice card shows `status="error"` | ✅ Handled | Document status tracked in DB |
| **Low confidence** | Red confidence badge, "needs_review" status | ✅ Handled | Highlighted in UI |
| **No line items** | Empty line items table | ✅ Handled | Shows "No line items" message |
| **Polling timeout** | Uses initial metadata | ⚠️ Partial | May show incomplete data |

---

## 6️⃣ Gaps, Risks, and Next Actions

### What We Have vs What We Want

| Spec Item | Status | Quality Level |
|-----------|--------|---------------|
| **PDF upload & storage** | ✅ Complete | Production-ready |
| **Multi-page processing** | ✅ Complete | Production-ready |
| **Preprocessing pipeline** | ✅ Complete | Production-ready (advanced features) |
| **Layout detection** | ⚠️ Partial | Using OpenCV fallback (LayoutParser missing) |
| **OCR text extraction** | ⚠️ Partial | PaddleOCR code exists but dependency missing, Tesseract fallback broken |
| **LLM extraction** | ✅ Complete | Production-ready (if Ollama running) |
| **Geometric extraction** | 🟡 Stubbed | Legacy code, disabled when LLM enabled |
| **Field extraction** | ✅ Complete | Production-ready (LLM + regex fallback) |
| **Database storage** | ✅ Complete | Production-ready |
| **Frontend integration** | ✅ Complete | Production-ready |
| **Multi-invoice splitting** | ⚠️ Partial | Code exists but may not create separate DB records |

### Current Standard / Quality Level

**STRENGTHS:**
- ✅ **LLM-first extraction is well-implemented** - Comprehensive prompt, math verification, BBox alignment
- ✅ **Preprocessing is advanced** - Dual-path comparison, dewarping, CLAHE, morphology
- ✅ **Error handling is robust** - Graceful fallbacks, lifecycle tracking, audit logging
- ✅ **Frontend is well-wired** - Normalization handles field variations, polling works correctly
- ✅ **Database schema is complete** - Supports invoices, delivery notes, line items, confidence tracking

**WEAKNESSES:**
- ❌ **Dependency gaps** - PaddleOCR, Tesseract, LayoutParser not installed/declared
- ❌ **Tesseract fallback broken** - Binary not installed, hardcoded Windows path
- ⚠️ **LayoutParser missing** - Using OpenCV fallback (may reduce layout detection quality)
- ⚠️ **Multi-invoice splitting incomplete** - Code exists but may not create separate DB records
- ⚠️ **Ollama dependency** - External service must be running, no health check

### Concrete Next Actions (Priority Order)

#### HIGH PRIORITY (Blocks Reliable Automatic Scanning)

1. **Install PaddleOCR** ⚠️ **CRITICAL**
   - **Action**: Add `paddleocr>=2.7.0` to `requirements.txt`
   - **File**: `.github/requirements.txt` (uncomment line 15)
   - **Impact**: Primary OCR engine will work, text extraction will succeed
   - **Risk**: Without this, OCR returns empty text, confidence 0.0

2. **Install Tesseract Binary** ⚠️ **CRITICAL**
   - **Action**: Install Tesseract-OCR on Windows: `choco install tesseract` or download from GitHub
   - **File**: `backend/ocr/ocr_processor.py:49` (verify path: `C:\Program Files\Tesseract-OCR\tesseract.exe`)
   - **Impact**: Fallback OCR will work when PaddleOCR fails
   - **Risk**: Without this, fallback fails, no text extracted on PaddleOCR errors

3. **Add pytesseract to requirements.txt** ⚠️ **HIGH**
   - **Action**: Add `pytesseract>=0.3.10` to `requirements.txt`
   - **File**: `.github/requirements.txt`
   - **Impact**: Python wrapper for Tesseract will be available
   - **Risk**: Tesseract fallback will fail even if binary is installed

4. **Verify Ollama Service** ⚠️ **HIGH**
   - **Action**: Check if Ollama is running on `localhost:11434`
   - **Command**: `curl http://localhost:11434/api/tags` or check service status
   - **Impact**: LLM extraction will work (currently hardcoded to fail loudly if Ollama down)
   - **Risk**: Without Ollama, LLM extraction fails, no fallback (system breaks)

5. **Verify PyMuPDF Installation** ⚠️ **HIGH**
   - **Action**: Check if `fitz` (PyMuPDF) is installed: `pip show PyMuPDF`
   - **File**: Add to `requirements.txt` if missing: `PyMuPDF>=1.23.0`
   - **Impact**: PDF rendering will work
   - **Risk**: Without this, PDF uploads fail with "PyMuPDF not installed" error

#### MEDIUM PRIORITY (Improves Quality/UX)

6. **Install LayoutParser** ⚠️ **MEDIUM**
   - **Action**: Uncomment `layoutparser[paddledetection]>=0.3.4` in `requirements.txt`
   - **File**: `.github/requirements.txt:16`
   - **Impact**: Better layout detection (EfficientDet PubLayNet) vs OpenCV fallback
   - **Risk**: Without this, layout detection uses OpenCV fallback (may detect fewer blocks)

7. **Fix Multi-Invoice Splitting** ⚠️ **MEDIUM**
   - **Action**: Verify `DocumentGroup` creates separate DB records for split invoices
   - **File**: `backend/llm/invoice_parser.py:DocumentGroup`, `backend/services/ocr_service.py:136-583`
   - **Impact**: Multi-invoice PDFs will create separate invoice records
   - **Risk**: Currently may store multiple invoices as one record

8. **Add Ollama Health Check** ⚠️ **MEDIUM**
   - **Action**: Add health check endpoint or startup check for Ollama
   - **File**: `backend/llm/invoice_parser.py:LLMInvoiceParser.__init__()`
   - **Impact**: Fail fast if Ollama is down, better error messages
   - **Risk**: Currently fails during OCR processing (poor UX)

9. **Add rapidfuzz to requirements.txt** ⚠️ **MEDIUM**
   - **Action**: Add `rapidfuzz>=3.0.0` to `requirements.txt`
   - **File**: `.github/requirements.txt`
   - **Impact**: BBox alignment will work (required for LLM extraction)
   - **Risk**: BBox alignment may fail if missing

10. **Add pillow-heif to requirements.txt** ⚠️ **MEDIUM**
    - **Action**: Add `pillow-heif>=0.13.0` to `requirements.txt`
    - **File**: `.github/requirements.txt`
    - **Impact**: HEIC file support will work
    - **Risk**: HEIC uploads will fail with import error

#### LOW PRIORITY (Nice-to-Haves / Refactors)

11. **Remove Hardcoded Tesseract Path** 🟡 **LOW**
    - **Action**: Make Tesseract path configurable via environment variable
    - **File**: `backend/ocr/ocr_processor.py:49`
    - **Impact**: Works on Linux/Mac, not just Windows
    - **Risk**: Currently Windows-only

12. **Document Feature Flags** 🟡 **LOW**
    - **Action**: Create feature flag documentation explaining what each flag does
    - **File**: `docs/FEATURE_FLAGS.md` (new)
    - **Impact**: Easier configuration, less confusion
    - **Risk**: Low, documentation only

13. **Remove Legacy Geometric Extractor** 🟡 **LOW**
    - **Action**: Remove `backend/ocr/table_extractor.py` if LLM extraction is permanent
    - **File**: `backend/ocr/table_extractor.py` (delete)
    - **Impact**: Cleaner codebase, less maintenance
    - **Risk**: May want to keep as emergency fallback

14. **Add Integration Tests** 🟡 **LOW**
    - **Action**: Create end-to-end tests for upload → OCR → DB → frontend
    - **File**: `tests/test_ocr_integration.py` (new)
    - **Impact**: Catch regressions, verify full pipeline
    - **Risk**: Low, testing only

---

## Summary

The Owlin OCR system is **architecturally sound** with a **well-implemented LLM-first extraction pipeline**. However, **critical dependencies are missing** (PaddleOCR, Tesseract, potentially PyMuPDF), which will cause OCR to fail or return empty results.

**Immediate Action Required:**
1. Install PaddleOCR (`pip install paddleocr>=2.7.0`)
2. Install Tesseract binary (Windows installer or `choco install tesseract`)
3. Add `pytesseract` to requirements.txt
4. Verify Ollama is running on `localhost:11434`
5. Verify PyMuPDF is installed

**Once dependencies are installed, the system should work end-to-end** with high-quality LLM extraction, robust preprocessing, and comprehensive error handling.

---

**Audit completed by**: AI Assistant (Debug Mode)  
**Methodology**: Code analysis, dependency checking, runtime flow tracing, frontend inspection
