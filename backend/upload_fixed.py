import os
import uuid
from fastapi import APIRouter, File, UploadFile, HTTPException
from datetime import datetime
from backend.ocr.ocr_engine import run_ocr
from backend.ocr.parse_invoice import extract_invoice_metadata
from backend.db import insert_invoice_record

router = APIRouter()

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and process a PDF invoice."""
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Read file contents
        contents = await file.read()
        filename = f"{uuid.uuid4()}.pdf"
        path = os.path.join(UPLOAD_DIR, filename)

        # Save PDF
        with open(path, "wb") as f:
            f.write(contents)

        # Run OCR
        ocr_text, confidence = run_ocr(path)

        # Parse metadata
        parsed = extract_invoice_metadata(ocr_text)

        # Save to DB
        invoice_id = insert_invoice_record(
            invoice_number=parsed["invoice_number"],
            supplier_name=parsed["supplier_name"],
            invoice_date=parsed["invoice_date"],
            total_amount=parsed["total_amount"],
            confidence=confidence,
            ocr_text=ocr_text,
            filename=filename,
            status="scanned",
            upload_time=datetime.utcnow().isoformat()
        )

        return {
            "message": "Uploaded and saved",
            "invoice_id": invoice_id,
            "filename": file.filename,
            "parsed_data": parsed,
            "confidence": confidence
        }

    except Exception as e:
        # Clean up file if it was created
        if 'path' in locals() and os.path.exists(path):
            os.remove(path)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}") 