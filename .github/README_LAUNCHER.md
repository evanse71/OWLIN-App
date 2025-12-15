# 🦉 OWLIN Local Environment Launcher

This directory contains launcher scripts to easily start the OWLIN local development environment.

## 🚀 Quick Start

### Option 1: Single Port Mode (Recommended)
```bash
start_owlin.bat
```
- Backend and frontend served from port 8000
- Frontend is built and served as static files
- Best for testing and demos

### Option 2: Split Mode (Development)
```bash
start_owlin_split.bat
```
- Backend on port 8000 (FastAPI)
- Frontend on port 5173 (Vite dev server)
- Best for active development with hot reload

### Option 3: Individual Services
```bash
start_backend_only.bat    # Backend only on port 8000
start_frontend_only.bat   # Frontend only on port 5173
```

### Stop All Services
```bash
stop_owlin.bat
```

## 📋 Prerequisites

1. **Python 3.8+** with pip
2. **Node.js 16+** with npm
3. **Required Python packages** (install with `pip install -r .github/requirements.txt`)

## 🔧 What Each Script Does

### `start_owlin.bat` (Single Port)
1. Kills any existing processes
2. Sets up environment variables
3. Creates necessary directories
4. Builds the frontend (`npm run build`)
5. Starts the backend with static file serving
6. Tests the connection
7. Opens browser to http://127.0.0.1:8000

### `start_owlin_split.bat` (Split Mode)
1. Kills any existing processes
2. Sets up environment variables
3. Creates necessary directories
4. Starts backend on port 8000
5. Starts frontend dev server on port 5173
6. Tests both connections
7. Opens browser to http://127.0.0.1:5173

## 🌐 URLs

### Single Port Mode
- **Main App**: http://127.0.0.1:8000
- **Health Check**: http://127.0.0.1:8000/api/health
- **Upload API**: http://127.0.0.1:8000/api/upload

### Split Mode
- **Frontend**: http://127.0.0.1:5173
- **Backend API**: http://127.0.0.1:8000
- **Health Check**: http://127.0.0.1:8000/api/health

## 🧪 Testing File Uploads

1. Start the environment using one of the launcher scripts
2. Navigate to the Invoices page
3. Upload a PDF invoice or delivery note
4. Check the backend window for OCR processing logs
5. Verify the document appears in the UI

## 🐛 Troubleshooting

### Backend Won't Start
- Check if port 8000 is already in use: `netstat -ano | findstr :8000`
- Kill the process: `taskkill /PID <pid> /F`
- Ensure Python dependencies are installed

### Frontend Won't Start
- Check if port 5173 is already in use: `netstat -ano | findstr :5173`
- Ensure Node.js and npm are installed
- Run `npm install` in the `source_extracted/tmp_lovable` directory

### CORS Errors
- The backend is configured to allow CORS from localhost:3000, localhost:5173, and localhost:8000
- If you're using a different port, you may need to update the CORS configuration

### Upload Directory Issues
- Ensure `data/uploads/` directory exists and is writable
- Check that the backend has permission to create files

## 📁 Directory Structure

```
owlin_backup_2025-10-02_225554/
├── data/                    # Database and uploads
│   ├── owlin.db            # SQLite database
│   ├── uploads/            # Uploaded files
│   └── logs/               # Application logs
├── source_extracted/       # Main application
│   ├── test_backend_simple.py  # FastAPI backend
│   └── tmp_lovable/        # React frontend
│       ├── package.json    # Frontend dependencies
│       └── dist/           # Built frontend (after build)
└── *.bat                   # Launcher scripts
```

## 🔄 Environment Variables

The scripts set these environment variables:

- `OWLIN_ENV=dev` - Development mode
- `OWLIN_DB_PATH` - Path to SQLite database
- `OWLIN_UPLOADS_DIR` - Path to uploads directory
- `OWLIN_DEMO=0` - Demo mode disabled
- `OWLIN_DEFAULT_VENUE=Royal Oak Hotel` - Default venue
- `OWLIN_SINGLE_PORT=1/0` - Single port mode toggle

## 📝 Notes

- The Royal Oak launcher (`source_extracted/Start-RoyalOak-Now.bat`) is preserved for Royal Oak specific deployments
- All launchers ensure the same localhost:8000 port as requested
- The backend includes OCR processing, file upload validation, and document pairing
- The frontend is a modern React app with Vite, TypeScript, and Tailwind CSS

## OCR Pipeline — Phase 1 & Phase 2

This repository includes a **safe scaffolding** for an offline OCR pipeline with Phase 2 accuracy upgrades:

- Module: `backend/ocr/owlin_scan_pipeline.py`
- Tests: `tests/test_scan_pipeline_skeleton.py`, `tests/test_phase2_preproc_layout.py`

### Quick Start
1) Create a virtualenv and install minimal deps:
   ```bash
   pip install -r requirements.txt
   ```

2. (Optional) Install heavy OCR deps when ready:

   ```bash
   pip install paddleocr "layoutparser[paddledetection]" pdf2image rapidfuzz
   ```
3. Run tests:

   ```bash
   pytest -q
   ```

> The pipeline is intentionally **not wired** to production endpoints yet.

### OCR v2 Endpoint (feature-flagged)
- **POST** `/api/ocr/run` (form field: `file`)
- Default: **disabled** unless `FEATURE_OCR_PIPELINE_V2=true`
- Health: `/api/health` includes `ocr_v2_enabled`

Enable locally:
```bash
export FEATURE_OCR_PIPELINE_V2=true
uvicorn backend.main:app --reload
# then POST a PDF: curl -F "file=@tests/fixtures/sample.pdf" http://127.0.0.1:8000/api/ocr/run
```

## Phase 2 Accuracy Upgrade

Phase 2 introduces enhanced preprocessing, layout detection, and confidence routing with feature flags:

### Feature Flags
- `FEATURE_OCR_V2_PREPROC` (default: false): Advanced OpenCV preprocessing
- `FEATURE_OCR_V2_LAYOUT` (default: false): LayoutParser block detection
- `CONF_FIELD_MIN` (default: 0.55): Minimum field confidence threshold
- `CONF_PAGE_MIN` (default: 0.60): Minimum page confidence threshold

### Enhanced Preprocessing (FEATURE_OCR_V2_PREPROC=true)
- **Deskew**: Hough line detection and rotation correction
- **Denoise**: Bilateral filtering for noise reduction
- **CLAHE**: Contrast Limited Adaptive Histogram Equalization
- **Morphology**: Opening operation to remove noise
- **Threshold**: Adaptive Gaussian with Otsu fallback
- **Dewarp**: 4-point contour detection and perspective correction

### Layout Detection (FEATURE_OCR_V2_LAYOUT=true)
- **EfficientDet PubLayNet**: Document layout analysis
- **Block Detection**: Text, Title, List, Table, Figure regions
- **Coordinate Mapping**: [x, y, w, h] format for OCR processing

### Confidence Routing
- **Field Penalties**: Blocks below `CONF_FIELD_MIN` get 50% confidence reduction
- **Page Penalties**: Pages below `CONF_PAGE_MIN` get 30% confidence reduction
- **Graceful Degradation**: Missing dependencies don't crash the system

### Enable Phase 2 Features
```bash
export FEATURE_OCR_PIPELINE_V2=true
export FEATURE_OCR_V2_PREPROC=true
export FEATURE_OCR_V2_LAYOUT=true
export CONF_FIELD_MIN=0.55
export CONF_PAGE_MIN=0.60
uvicorn backend.main:app --reload
```

### Optional Dependencies for Phase 2
```bash
# Core image processing
pip install opencv-python numpy

# Advanced OCR and layout detection
pip install paddleocr "layoutparser[paddledetection]" rapidfuzz

# Additional accuracy improvements
pip install scikit-image pillow
```

### Testing Phase 2
```bash
# Test with flags off (Phase 1 behavior)
pytest tests/test_phase2_preproc_layout.py -v

# Test graceful degradation
pytest tests/test_phase2_preproc_layout.py::TestPhase2GracefulDegradation -v
```

## Phase 3 — Tables + Templates + Donut + LLM (feature-flagged)

Phase 3 introduces table extraction, supplier templates, Donut fallback, and local LLM normalization:

### Feature Flags
- `FEATURE_OCR_V3_TABLES` (default: false): Table extraction and line-item parsing
- `FEATURE_OCR_V3_TEMPLATES` (default: false): Supplier template matching
- `FEATURE_OCR_V3_DONUT` (default: false): HuggingFace Donut fallback for low-confidence pages
- `FEATURE_OCR_V3_LLM` (default: false): Local LLM normalization to structured JSON
- `CONF_FALLBACK_PAGE` (default: 0.45): Page confidence threshold for Donut fallback
- `CONF_FALLBACK_OVERALL` (default: 0.50): Overall confidence threshold for Donut fallback

### Table Extraction (FEATURE_OCR_V3_TABLES=true)
- **Cell Clustering**: Groups table cells into columns based on x-coordinate proximity
- **Row Assembly**: Assembles cells into rows based on y-coordinate proximity
- **Line Item Parsing**: Extracts structured line items from table data
- **Header Detection**: Automatically detects table headers and maps to line items

### Supplier Templates (FEATURE_OCR_V3_TEMPLATES=true)
- **Template Matching**: Fuzzy matching against supplier invoice patterns
- **Auto-Acceptance**: Boosts confidence for known supplier formats
- **Pattern Recognition**: Logo hints, invoice number patterns, date formats, table headers
- **Currency Detection**: Automatic currency symbol and code recognition

### Donut Fallback (FEATURE_OCR_V3_DONUT=true)
- **Low-Confidence Routing**: Triggers when page confidence < `CONF_FALLBACK_PAGE` or overall < `CONF_FALLBACK_OVERALL`
- **HuggingFace Integration**: Uses `naver-clova-ix/donut-base-finetuned-docvqa` model
- **Graceful Degradation**: Falls back to standard OCR when Donut unavailable
- **Offline-First**: Lazy loading, no forced dependencies

### Local LLM Normalization (FEATURE_OCR_V3_LLM=true)
- **Schema JSON**: Normalizes OCR text to structured invoice schema
- **Field Extraction**: Supplier name, invoice number, date, currency, amounts, line items
- **Confidence Scoring**: Provides confidence scores for extracted fields
- **Heuristic Fallback**: Deterministic parsing when LLM unavailable

### Enable Phase 3 Features
```bash
export FEATURE_OCR_PIPELINE_V2=true
export FEATURE_OCR_V3_TABLES=true
export FEATURE_OCR_V3_TEMPLATES=true
export FEATURE_OCR_V3_DONUT=false
export FEATURE_OCR_V3_LLM=true
export CONF_FALLBACK_PAGE=0.45
export CONF_FALLBACK_OVERALL=0.50
uvicorn backend.main:app --reload
```

### Optional Dependencies for Phase 3
```bash
# Core dependencies
pip install rapidfuzz pydantic pyyaml

# For Donut fallback (optional)
pip install transformers torch sentencepiece timm pillow

# For enhanced table extraction
pip install scikit-image opencv-python
```

### Testing Phase 3
```bash
# Test with flags off (Phase 2 behavior)
pytest tests/test_phase3_tables_templates.py -v

# Test graceful degradation
pytest tests/test_phase3_tables_templates.py::TestPhase3Integration -v
```

### Output Fields (Phase 3)
- **per-block**: `table_data` (when table extraction enabled)
- **per-page**: `fallback_text` (when Donut fallback used)
- **per-page**: `template_match` (when supplier template matched)
- **top-level**: `normalized_json` (when LLM normalization used)