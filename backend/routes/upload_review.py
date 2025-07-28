import os
import uuid
import logging
from fastapi import APIRouter, File, UploadFile, HTTPException
from backend.ocr.smart_upload_processor import SmartUploadProcessor

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/upload/review")
async def upload_for_review(file: UploadFile = File(...)):
    """
    Upload a PDF for smart processing and review.
    This endpoint can handle multi-invoice PDFs and intelligently split them.
    """
    logger.debug(f"Upload/review received: {file.filename if file else 'No file'}")
    
    # ✅ Enhanced input validation
    if not file:
        logger.error("❌ No file uploaded")
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    if not file.filename:
        logger.error("❌ No filename provided")
        raise HTTPException(status_code=400, detail="No filename provided")
    
    if not file.filename.lower().endswith('.pdf'):
        logger.error(f"❌ Invalid file type: {file.filename}")
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        logger.info(f"🔄 Processing PDF for review: {file.filename}")
        
        # Save uploaded file temporarily
        contents = await file.read()
        filename = f"{uuid.uuid4()}.pdf"
        upload_dir = "data/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, filename)
        
        logger.debug(f"📁 Saving file to: {filepath}")
        with open(filepath, "wb") as f:
            f.write(contents)
        
        logger.info(f"✅ File saved, starting smart processing...")
        
        # ✅ Use SmartUploadProcessor for multi-invoice PDF handling
        processor = SmartUploadProcessor()
        result = processor.process_multi_invoice_pdf(filepath)
        
        logger.info(f"✅ Smart processing completed")
        
        # Clean up temporary file
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.debug(f"✅ Temporary file cleaned up")
        
        return {
            "message": "PDF processed successfully",
            "original_filename": file.filename,
            "suggested_documents": result["suggested_documents"],
            "processing_summary": result["processing_summary"]
        }
        
    except Exception as e:
        logger.exception(f"❌ Processing failed for {file.filename}")
        
        # Clean up on error
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)
            logger.debug(f"✅ Temporary file cleaned up after error")
        
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}") 