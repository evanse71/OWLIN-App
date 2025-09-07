# Owlin Backend (FastAPI + SQLite)

## Setup
- Python 3.10+
- `pip install fastapi uvicorn[standard] pytesseract opencv-python`

## Run
```bash
uvicorn app:app --reload --port 8000
```

The SQLite DB is backend/owlin.db. OCR uses Tesseract via pytesseract. 