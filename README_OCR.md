# OWLIN OCR Backend

This document describes the OCR and document processing backend for the OWLIN application.

## Running the API

```bash
# Install dependencies. The `python-multipart` package is required by
# FastAPI for handling file uploads (UploadFile).
pip install fastapi uvicorn pypdf pypdfium2 paddleocr pytesseract opencv-python python-dateutil Babel rapidfuzz python-multipart

# Ensure database and directories exist
mkdir -p data/uploads data/tmp_images

# Run the app
uvicorn backend.routers.uploads:router --reload
```

## Features

### Document Type Classification
The parser recognises invoices, delivery notes, supermarket receipts, credit notes, purchase orders, utility bills and others by searching for anchored keywords and basic layout cues. Document type classification and annotation detection follow the specification but are conservative in this baseline; they can be improved by tuning cue lists and adding machine learning models.

### Automatic Pairing
Automatic pairing between invoices and delivery notes is implemented via a simple heuristic: documents with the same supplier and invoice/delivery dates within a 30‑day window are paired with a strong score and stored in the `doc_pairs` table. Future versions can refine this by comparing line‑items and fuzzy supplier names.

### Annotation Detection
Handwritten annotation detection searches for coloured pen marks (e.g. green ticks or red circles) on the rasterised pages and records their bounding boxes. Detected annotations are stored in the `annotations` table and can be queried via the API. In this baseline, annotations are not mapped to specific line items and recognised text is not extracted.

## API Endpoints

### Upload Document
- **POST** `/api/uploads`
- Accepts PDF and image files
- Processes documents with OCR, annotation detection, and automatic pairing

### Legacy Upload
- **POST** `/api/upload`
- Legacy endpoint for backward compatibility

## Database Schema

The system uses the following main tables:
- `invoices` - Invoice records
- `delivery_notes` - Delivery note records  
- `line_items` - Line items for invoices
- `annotations` - Detected annotations with coordinates
- `doc_pairs` - Pairings between invoices and delivery notes
- `uploaded_files` - File upload tracking

## Processing Pipeline

1. **File Upload** - Documents are uploaded and stored
2. **OCR Processing** - Text extraction from images/PDFs
3. **Document Classification** - Determine document type
4. **Data Extraction** - Parse supplier, dates, totals, line items
5. **Annotation Detection** - Find handwritten marks using OpenCV
6. **Automatic Pairing** - Match invoices with delivery notes
7. **Database Storage** - Store all extracted data

## Configuration

The system supports configurable parameters for:
- Date window for pairing (default: 30 days)
- Supplier name matching threshold (default: 70%)
- Annotation detection sensitivity
- OCR engine selection

## Dependencies

- **FastAPI** - Web framework
- **OpenCV** - Image processing and annotation detection
- **PaddleOCR/Tesseract** - OCR engines
- **RapidFuzz** - Fuzzy string matching for supplier names
- **SQLite** - Database storage
- **PyPDFium2** - PDF processing
