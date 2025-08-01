"""
Enhanced Upload Route

This module provides the new unified upload endpoint that uses the enhanced
upload pipeline for consistent document processing with confidence scoring
and manual review logic.

Key Features:
- Single entry point for all document processing
- PDF and image file support
- Confidence scoring and manual review flags
- Template parsing and metadata extraction
- Role-based processing workflows
- Comprehensive error handling and logging

Author: OWLIN Development Team
Version: 1.0.0
"""

import os
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import the unified upload pipeline
from ..upload_pipeline import process_document, OCRResult, ParsedInvoice

logger = logging.getLogger(__name__)

router = APIRouter()

# Configuration
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

class UploadResponse(BaseModel):
    """Response model for upload endpoint"""
    success: bool
    message: str
    document_id: Optional[str] = None
    processing_results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

def validate_file(file: UploadFile) -> None:
    """Validate uploaded file"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )

def save_uploaded_file(file: UploadFile) -> str:
    """Save uploaded file to temporary location"""
    try:
        # Create upload directory
        upload_dir = Path("data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_ext = Path(file.filename).suffix
        unique_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}{file_ext}"
        file_path = upload_dir / unique_filename
        
        # Save file
        with open(file_path, "wb") as f:
            content = file.file.read()
            f.write(content)
        
        logger.info(f"💾 File saved: {file_path}")
        return str(file_path)
        
    except Exception as e:
        logger.error(f"❌ Failed to save file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

@router.post("/upload/enhanced")
async def upload_document_enhanced(
    file: UploadFile = File(...),
    parse_templates: bool = Form(True),
    save_debug: bool = Form(False),
    user_role: Optional[str] = Form(None)
) -> UploadResponse:
    """
    Enhanced document upload endpoint using unified pipeline
    
    Args:
        file: Uploaded document file
        parse_templates: Whether to parse invoice templates
        save_debug: Whether to save debug artifacts
        user_role: User role for role-based processing
        
    Returns:
        UploadResponse with processing results
    """
    try:
        logger.info(f"🔄 Starting enhanced upload: {file.filename}")
        
        # Validate file
        validate_file(file)
        
        # Save file
        file_path = save_uploaded_file(file)
        
        # Process document using unified pipeline
        processing_results = process_document(
            file_path=file_path,
            parse_templates=parse_templates,
            save_debug=save_debug
        )
        
        # Generate document ID
        document_id = str(uuid.uuid4())
        
        # Prepare response
        response_data = {
            "document_id": document_id,
            "filename": file.filename,
            "file_path": file_path,
            "processing_time": processing_results["processing_time"],
            "pages_processed": processing_results["pages_processed"],
            "overall_confidence": processing_results["overall_confidence"],
            "manual_review_required": processing_results["manual_review_required"],
            "document_type": processing_results["document_type"],
            "confidence_scores": processing_results["confidence_scores"]
        }
        
        # Add parsed invoice data if available
        if "parsed_invoice" in processing_results:
            parsed_invoice = processing_results["parsed_invoice"]
            response_data["parsed_invoice"] = {
                "invoice_number": parsed_invoice.invoice_number,
                "date": parsed_invoice.date,
                "supplier": parsed_invoice.supplier,
                "net_total": parsed_invoice.net_total,
                "vat_total": parsed_invoice.vat_total,
                "gross_total": parsed_invoice.gross_total,
                "currency": parsed_invoice.currency,
                "vat_rate": parsed_invoice.vat_rate,
                "confidence": parsed_invoice.confidence,
                "line_items": [
                    {
                        "description": item.description,
                        "quantity": item.quantity,
                        "unit_price": item.unit_price,
                        "total_price": item.total_price,
                        "confidence": item.confidence
                    }
                    for item in parsed_invoice.line_items
                ]
            }
        
        # Add OCR results summary
        ocr_results = processing_results["ocr_results"]
        response_data["ocr_summary"] = {
            "total_results": len(ocr_results),
            "field_types": {
                field_type: len([r for r in ocr_results if r.field_type == field_type])
                for field_type in set(r.field_type for r in ocr_results if r.field_type)
            },
            "average_confidence": sum(r.confidence for r in ocr_results) / len(ocr_results) if ocr_results else 0.0
        }
        
        # Role-based processing
        if user_role:
            response_data["role_based_processing"] = {
                "user_role": user_role,
                "can_edit": user_role in ["finance", "admin"],
                "can_approve": user_role in ["finance", "admin"],
                "can_view_details": True
            }
        
        logger.info(f"✅ Enhanced upload completed: {document_id}")
        
        return UploadResponse(
            success=True,
            message="Document processed successfully",
            document_id=document_id,
            processing_results=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Enhanced upload failed: {e}")
        return UploadResponse(
            success=False,
            message="Document processing failed",
            error=str(e)
        )

@router.post("/upload/batch")
async def upload_batch_enhanced(
    files: list[UploadFile] = File(...),
    parse_templates: bool = Form(True),
    save_debug: bool = Form(False),
    user_role: Optional[str] = Form(None)
) -> Dict[str, Any]:
    """
    Batch upload endpoint for multiple documents
    
    Args:
        files: List of uploaded files
        parse_templates: Whether to parse invoice templates
        save_debug: Whether to save debug artifacts
        user_role: User role for role-based processing
        
    Returns:
        Dictionary with batch processing results
    """
    try:
        logger.info(f"🔄 Starting batch upload: {len(files)} files")
        
        results = []
        errors = []
        
        for i, file in enumerate(files):
            try:
                logger.info(f"🔄 Processing file {i+1}/{len(files)}: {file.filename}")
                
                # Validate file
                validate_file(file)
                
                # Save file
                file_path = save_uploaded_file(file)
                
                # Process document
                processing_results = process_document(
                    file_path=file_path,
                    parse_templates=parse_templates,
                    save_debug=save_debug
                )
                
                # Generate document ID
                document_id = str(uuid.uuid4())
                
                # Prepare result
                result = {
                    "document_id": document_id,
                    "filename": file.filename,
                    "file_path": file_path,
                    "processing_time": processing_results["processing_time"],
                    "overall_confidence": processing_results["overall_confidence"],
                    "manual_review_required": processing_results["manual_review_required"],
                    "document_type": processing_results["document_type"]
                }
                
                # Add parsed invoice if available
                if "parsed_invoice" in processing_results:
                    parsed_invoice = processing_results["parsed_invoice"]
                    result["parsed_invoice"] = {
                        "invoice_number": parsed_invoice.invoice_number,
                        "supplier": parsed_invoice.supplier,
                        "gross_total": parsed_invoice.gross_total,
                        "confidence": parsed_invoice.confidence
                    }
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"❌ Failed to process file {file.filename}: {e}")
                errors.append({
                    "filename": file.filename,
                    "error": str(e)
                })
        
        # Calculate batch statistics
        total_files = len(files)
        successful_files = len(results)
        failed_files = len(errors)
        average_confidence = sum(r["overall_confidence"] for r in results) / len(results) if results else 0.0
        manual_review_count = sum(1 for r in results if r["manual_review_required"])
        
        logger.info(f"✅ Batch upload completed: {successful_files}/{total_files} successful")
        
        return {
            "success": True,
            "message": f"Batch processing completed: {successful_files}/{total_files} successful",
            "statistics": {
                "total_files": total_files,
                "successful_files": successful_files,
                "failed_files": failed_files,
                "average_confidence": average_confidence,
                "manual_review_count": manual_review_count
            },
            "results": results,
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"❌ Batch upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")

@router.get("/upload/status/{document_id}")
async def get_upload_status(document_id: str) -> Dict[str, Any]:
    """
    Get processing status for a document
    
    Args:
        document_id: Document ID to check
        
    Returns:
        Dictionary with processing status
    """
    # This would typically check a database or cache for processing status
    # For now, return a mock response
    return {
        "document_id": document_id,
        "status": "completed",
        "processing_time": 2.5,
        "confidence": 0.85,
        "manual_review_required": False
    }

@router.delete("/upload/{document_id}")
async def delete_document(document_id: str) -> Dict[str, Any]:
    """
    Delete a processed document
    
    Args:
        document_id: Document ID to delete
        
    Returns:
        Dictionary with deletion result
    """
    try:
        # This would typically delete from database and file system
        # For now, return a mock response
        logger.info(f"🗑️ Deleting document: {document_id}")
        
        return {
            "success": True,
            "message": f"Document {document_id} deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to delete document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}") 