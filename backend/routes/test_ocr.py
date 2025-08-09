#!/usr/bin/env python3
"""
Test OCR API endpoint for debugging and validation.
"""

import os
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import tempfile
import shutil

# Set up logging
logger = logging.getLogger(__name__)

# Import OCR functions
try:
    from ocr.ocr_engine import run_invoice_ocr
    logger.debug("✅ run_invoice_ocr imported successfully")
    # Create alias for backward compatibility
    run_paddle_ocr = run_invoice_ocr
except ImportError as e:
    logger.error(f"❌ Failed to import run_invoice_ocr: {e}")
    run_paddle_ocr = None

router = APIRouter()

@router.post("/api/test-ocr")
async def test_ocr(file: UploadFile = File(...)):
    """
    Test OCR processing on uploaded file.
    
    Args:
        file: Uploaded file to process
        
    Returns:
        OCR results with timing and confidence information
    """
    logger.info(f"🧪 Test OCR request received for: {file.filename}")
    
    # Validate file
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Check file extension
    allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png"}
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type: {file_ext}. Supported types: {', '.join(allowed_extensions)}"
        )
    
    # Create temporary file
    temp_file = None
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_path = temp_file.name
        
        logger.info(f"📁 File saved to temporary location: {temp_path}")
        
        # Check if OCR function is available
        if run_paddle_ocr is None:
            raise HTTPException(status_code=500, detail="OCR engine not available")
        
        # Run OCR processing
        logger.info("🔄 Starting OCR processing...")
        ocr_result = run_paddle_ocr(temp_path)
        
        # Clean up temporary file
        try:
            os.unlink(temp_path)
            logger.debug("🗑️ Temporary file cleaned up")
        except Exception as e:
            logger.warning(f"⚠️ Failed to clean up temporary file: {e}")
        
        # Prepare response
        response_data = {
            "filename": file.filename,
            "file_size": file.size,
            "ocr_result": ocr_result,
            "success": True
        }
        
        logger.info(f"✅ Test OCR completed successfully for {file.filename}")
        return JSONResponse(content=response_data)
        
    except Exception as e:
        # Clean up temporary file on error
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.unlink(temp_file.name)
            except:
                pass
        
        logger.error(f"❌ Test OCR failed for {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")

@router.get("/api/test-ocr/health")
async def test_ocr_health():
    """Health check for test OCR endpoint."""
    return {
        "status": "healthy",
        "ocr_available": run_paddle_ocr is not None,
        "message": "Test OCR endpoint is ready"
    } 