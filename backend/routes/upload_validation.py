"""
Upload Validation Routes

This module provides API endpoints for upload validation, including
file type checking, duplicate detection, and descriptive naming.

Author: OWLIN Development Team
Version: 1.0.0
"""

import os
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from upload_pipeline import process_document
from upload_validator import (
    validate_upload, get_validation_summary, create_upload_metadata,
    is_supported_file, validate_file_size, check_duplicate_invoice,
    check_duplicate_file_hash, generate_temp_invoice_name
)

logger = logging.getLogger(__name__)

# Pydantic models for request/response
class ValidationRequest(BaseModel):
    """Request model for validation"""
    file_path: str
    extracted_data: Dict[str, Optional[str]]
    db_path: Optional[str] = "data/owlin.db"
    max_file_size_mb: Optional[int] = 50

class ValidationResponse(BaseModel):
    """Response model for validation"""
    allowed: bool
    messages: Dict[str, str]
    validation_data: Dict[str, Any]
    summary: Dict[str, Any]
    metadata: Dict[str, Any]

class UploadValidationResponse(BaseModel):
    """Response model for upload validation"""
    success: bool
    validation: ValidationResponse
    processing_results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

router = APIRouter()

@router.post("/validation/check")
async def validate_upload_file(
    file: UploadFile = File(...),
    db_path: str = Form("data/owlin.db"),
    max_file_size_mb: int = Form(50),
    process_document: bool = Form(True),
    parse_templates: bool = Form(True),
    save_debug: bool = Form(False)
) -> UploadValidationResponse:
    """
    Validate an uploaded file and optionally process it
    
    This endpoint performs comprehensive validation including:
    - File type and size validation
    - Duplicate detection (invoice number and file hash)
    - Descriptive naming generation
    - Optional document processing and parsing
    """
    try:
        logger.info(f"🔄 Starting upload validation for: {file.filename}")
        
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Basic file validation
            if not is_supported_file(file.filename):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {file.filename}"
                )
            
            # File size validation
            size_valid, size_error = validate_file_size(temp_file_path, max_file_size_mb)
            if not size_valid:
                raise HTTPException(status_code=400, detail=size_error)
            
            # Initialize extracted data (will be populated if processing is enabled)
            extracted_data = {}
            
            # Process document if requested
            processing_results = None
            if process_document:
                logger.info("🔄 Processing document for validation...")
                processing_results = process_document(
                    temp_file_path,
                    parse_templates=parse_templates,
                    save_debug=save_debug,
                    validate_upload=False,  # We'll do validation separately
                    db_path=db_path
                )
                
                # Extract data from processing results
                if 'parsed_invoice' in processing_results:
                    invoice = processing_results['parsed_invoice']
                    extracted_data = {
                        'supplier_name': invoice.supplier,
                        'invoice_number': invoice.invoice_number,
                        'invoice_date': invoice.date
                    }
                elif 'parsed_delivery_note' in processing_results:
                    delivery_note = processing_results['parsed_delivery_note']
                    extracted_data = {
                        'supplier_name': delivery_note.supplier,
                        'delivery_number': delivery_note.delivery_number,
                        'invoice_date': delivery_note.date
                    }
            
            # Perform upload validation
            upload_allowed, validation_messages, validation_data = validate_upload(
                temp_file_path, extracted_data, db_path, max_file_size_mb
            )
            
            # Create response
            validation_response = ValidationResponse(
                allowed=upload_allowed,
                messages=validation_messages,
                validation_data=validation_data,
                summary=get_validation_summary(validation_data),
                metadata=create_upload_metadata(validation_data)
            )
            
            response = UploadValidationResponse(
                success=True,
                validation=validation_response,
                processing_results=processing_results
            )
            
            logger.info(f"✅ Upload validation completed for: {file.filename}")
            return response
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"⚠️ Failed to clean up temp file: {e}")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Upload validation failed: {e}")
        return UploadValidationResponse(
            success=False,
            validation=ValidationResponse(
                allowed=False,
                messages={"error": f"Validation failed: {str(e)}"},
                validation_data={},
                summary={},
                metadata={}
            ),
            error=str(e)
        )

@router.post("/validation/check-duplicate")
async def check_duplicate_invoice_endpoint(
    invoice_number: str = Form(...),
    db_path: str = Form("data/owlin.db")
) -> Dict[str, Any]:
    """
    Check if an invoice number already exists in the database
    """
    try:
        duplicate = check_duplicate_invoice(invoice_number, db_path)
        return {
            "duplicate": duplicate,
            "invoice_number": invoice_number,
            "message": f"Invoice number '{invoice_number}' {'already exists' if duplicate else 'not found'} in database"
        }
    except Exception as e:
        logger.error(f"❌ Duplicate check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Duplicate check failed: {str(e)}")

@router.post("/validation/check-file-hash")
async def check_duplicate_file_hash_endpoint(
    file: UploadFile = File(...),
    db_path: str = Form("data/owlin.db")
) -> Dict[str, Any]:
    """
    Check if a file with the same hash already exists in the database
    """
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            duplicate, file_hash = check_duplicate_file_hash(temp_file_path, db_path)
            return {
                "duplicate": duplicate,
                "file_hash": file_hash,
                "message": f"File hash {'already exists' if duplicate else 'not found'} in database"
            }
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"⚠️ Failed to clean up temp file: {e}")
                
    except Exception as e:
        logger.error(f"❌ File hash check failed: {e}")
        raise HTTPException(status_code=500, detail=f"File hash check failed: {str(e)}")

@router.post("/validation/generate-name")
async def generate_invoice_name_endpoint(
    supplier: Optional[str] = Form(None),
    date: Optional[str] = Form(None),
    invoice_number: Optional[str] = Form(None)
) -> Dict[str, str]:
    """
    Generate a descriptive name for an invoice
    """
    try:
        name = generate_temp_invoice_name(supplier, date, invoice_number)
        return {"suggested_name": name}
    except Exception as e:
        logger.error(f"❌ Name generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Name generation failed: {str(e)}")

@router.get("/validation/supported-formats")
async def get_supported_formats() -> Dict[str, Any]:
    """
    Get list of supported file formats
    """
    from upload_validator import SUPPORTED_EXTENSIONS
    
    formats = {}
    for ext, mime_type in SUPPORTED_EXTENSIONS.items():
        formats[ext] = {
            "mime_type": mime_type,
            "description": f"{ext.upper()[1:]} file"
        }
    
    return {
        "supported_formats": formats,
        "total_formats": len(formats)
    }

@router.post("/validation/quick-check")
async def quick_validation_check(
    file: UploadFile = File(...),
    max_file_size_mb: int = Form(50)
) -> Dict[str, Any]:
    """
    Perform a quick validation check without database queries
    """
    try:
        # Check file type
        file_type_valid = is_supported_file(file.filename)
        
        # Check file size (read content to get size)
        content = await file.read()
        file_size = len(content)
        max_size_bytes = max_file_size_mb * 1024 * 1024
        size_valid = file_size <= max_size_bytes
        
        return {
            "file_name": file.filename,
            "file_size_bytes": file_size,
            "file_size_mb": file_size / (1024 * 1024),
            "file_type_valid": file_type_valid,
            "file_size_valid": size_valid,
            "overall_valid": file_type_valid and size_valid,
            "max_size_mb": max_file_size_mb
        }
        
    except Exception as e:
        logger.error(f"❌ Quick validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Quick validation failed: {str(e)}")

@router.get("/validation/status")
async def get_validation_status() -> Dict[str, Any]:
    """
    Get validation system status and configuration
    """
    try:
        from upload_validator import DEFAULT_DB_PATH, INVOICE_TABLES
        
        # Check database existence
        db_exists = os.path.exists(DEFAULT_DB_PATH)
        
        return {
            "system_status": "operational",
            "database_path": DEFAULT_DB_PATH,
            "database_exists": db_exists,
            "invoice_tables": INVOICE_TABLES,
            "supported_extensions": list(SUPPORTED_EXTENSIONS.keys()),
            "max_file_size_mb": 50,
            "validation_features": [
                "file_type_validation",
                "file_size_validation", 
                "duplicate_invoice_detection",
                "duplicate_file_hash_detection",
                "descriptive_naming"
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Status check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}") 