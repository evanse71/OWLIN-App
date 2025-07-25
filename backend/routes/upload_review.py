import os
import uuid
from fastapi import APIRouter, File, UploadFile, HTTPException
from backend.ocr.smart_upload_processor import SmartUploadProcessor

router = APIRouter()

@router.post("/upload/review")
async def upload_for_review(file: UploadFile = File(...)):
    """
    Upload a PDF for smart processing and review.
    This endpoint can handle multi-invoice PDFs and intelligently split them.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Save uploaded file temporarily
        contents = await file.read()
        filename = f"{uuid.uuid4()}.pdf"
        upload_dir = "data/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, filename)
        
        with open(filepath, "wb") as f:
            f.write(contents)
        
        # ✅ Use SmartUploadProcessor for multi-invoice PDF handling
        processor = SmartUploadProcessor()
        result = processor.process_multi_invoice_pdf(filepath)
        
        # Clean up temporary file
        if os.path.exists(filepath):
            os.remove(filepath)
        
        return {
            "message": "PDF processed successfully",
            "original_filename": file.filename,
            "suggested_documents": result["suggested_documents"],
            "processing_summary": result["processing_summary"]
        }
        
    except Exception as e:
        # Clean up on error
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)
        
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}") 