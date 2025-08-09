# OWLIN-App
Invoice auditing and supplier insights tool for hospitality

## Improved OCR Pipeline
This update introduces an optional module `backend/ocr_pipeline.py` which preprocesses images (grayscale, deskew, threshold, noise reduction) before running Tesseract with a tuned configuration. The module provides `parse_document()` returning structured line items, totals and a confidence score with a flag for low-confidence results.
