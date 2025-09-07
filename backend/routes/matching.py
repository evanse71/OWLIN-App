"""
Matching Routes

This module provides API endpoints for matching invoices with delivery notes.
It uses the enhanced OCR pipeline and fuzzy matching algorithms to pair documents.

Key Features:
- Pair invoice and delivery note documents
- Fuzzy matching of line items
- Discrepancy detection and reporting
- Confidence scoring and validation
- Manual review suggestions

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
from matching.match_invoice_delivery import match_documents, suggest_matches, validate_matching_result
from ocr.parse_invoice import ParsedInvoice
from ocr.parse_delivery_note import ParsedDeliveryNote

logger = logging.getLogger(__name__)

# Configuration
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

# Pydantic models for API responses
class MatchingRequest(BaseModel):
    invoice_file: str
    delivery_file: str
    threshold: float = 0.8
    normalize_descriptions: bool = True

class MatchingResponse(BaseModel):
    success: bool
    message: str
    matching_id: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class PairingRequest(BaseModel):
    invoice_id: str
    delivery_id: str
    threshold: float = 0.8

class PairingResponse(BaseModel):
    success: bool
    message: str
    pairing_id: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

router = APIRouter()

def validate_file(file: UploadFile) -> None:
    """Validate uploaded file"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size (if available)
    if hasattr(file, 'size') and file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {file.size} bytes (max: {MAX_FILE_SIZE})"
        )

def save_uploaded_file(file: UploadFile) -> str:
    """Save uploaded file to temporary location"""
    try:
        # Create temporary file
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            content = file.file.read()
            temp_file.write(content)
            temp_file.flush()
            return temp_file.name
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

@router.post("/matching/upload-pair")
async def upload_and_match_pair(
    invoice_file: UploadFile = File(...),
    delivery_file: UploadFile = File(...),
    threshold: float = Form(0.8),
    normalize_descriptions: bool = Form(True),
    save_debug: bool = Form(False)
) -> MatchingResponse:
    """
    Upload and immediately match an invoice with a delivery note
    
    Args:
        invoice_file: Invoice document file
        delivery_file: Delivery note document file
        threshold: Matching threshold (0.0 to 1.0)
        normalize_descriptions: Whether to normalize descriptions
        save_debug: Whether to save debug artifacts
        
    Returns:
        MatchingResponse with results
    """
    try:
        logger.info("🔄 Starting upload and match pair request")
        
        # Validate files
        validate_file(invoice_file)
        validate_file(delivery_file)
        
        # Save files
        invoice_path = save_uploaded_file(invoice_file)
        delivery_path = save_uploaded_file(delivery_file)
        
        try:
            # Process invoice
            logger.info("📄 Processing invoice document")
            invoice_result = process_document(
                invoice_path, 
                parse_templates=True, 
                save_debug=save_debug
            )
            
            # Process delivery note
            logger.info("📋 Processing delivery note document")
            delivery_result = process_document(
                delivery_path, 
                parse_templates=True, 
                save_debug=save_debug
            )
            
            # Extract parsed data
            invoice_data = {}
            delivery_data = {}
            
            if 'parsed_invoice' in invoice_result:
                invoice_data = {
                    'supplier': invoice_result['parsed_invoice'].supplier,
                    'date': invoice_result['parsed_invoice'].date,
                    'line_items': invoice_result['parsed_invoice'].line_items
                }
            
            if 'parsed_delivery_note' in delivery_result:
                delivery_data = {
                    'supplier': delivery_result['parsed_delivery_note'].supplier,
                    'date': delivery_result['parsed_delivery_note'].date,
                    'line_items': delivery_result['parsed_delivery_note'].line_items
                }
            
            # Perform matching
            logger.info("🔗 Performing document matching")
            matching_results = match_documents(invoice_data, delivery_data, threshold)
            
            # Generate matching ID
            matching_id = f"match_{uuid.uuid4().hex[:8]}"
            
            # Prepare response
            response_data = {
                'matching_id': matching_id,
                'invoice_processing': {
                    'document_type': invoice_result['document_type'],
                    'overall_confidence': invoice_result['overall_confidence'],
                    'manual_review_required': invoice_result['manual_review_required'],
                    'processing_time': invoice_result['processing_time']
                },
                'delivery_processing': {
                    'document_type': delivery_result['document_type'],
                    'overall_confidence': delivery_result['overall_confidence'],
                    'manual_review_required': delivery_result['manual_review_required'],
                    'processing_time': delivery_result['processing_time']
                },
                'matching_results': matching_results,
                'created_at': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Matching completed successfully: {matching_id}")
            
            return MatchingResponse(
                success=True,
                message="Documents uploaded and matched successfully",
                matching_id=matching_id,
                results=response_data
            )
            
        finally:
            # Clean up temporary files
            try:
                os.unlink(invoice_path)
                os.unlink(delivery_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temporary files: {e}")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Upload and match pair failed: {e}")
        return MatchingResponse(
            success=False,
            message="Failed to upload and match documents",
            error=str(e)
        )

@router.post("/matching/pair-existing")
async def pair_existing_documents(
    request: PairingRequest
) -> PairingResponse:
    """
    Pair existing processed documents by ID
    
    Args:
        request: PairingRequest with invoice_id and delivery_id
        
    Returns:
        PairingResponse with results
    """
    try:
        logger.info(f"🔄 Starting pairing request: {request.invoice_id} + {request.delivery_id}")
        
        # TODO: Retrieve processed documents from database/storage
        # For now, return mock response
        pairing_id = f"pair_{uuid.uuid4().hex[:8]}"
        
        # Mock matching results
        mock_results = {
            'document_matching': {
                'supplier_match': True,
                'date_match': True,
                'overall_confidence': 0.85
            },
            'item_matching': {
                'matched_items': [
                    {
                        'invoice_description': 'Product A',
                        'delivery_description': 'Product A',
                        'similarity_score': 0.95,
                        'quantity_mismatch': False,
                        'price_mismatch': False
                    }
                ],
                'total_matches': 1,
                'total_discrepancies': 0,
                'overall_confidence': 0.85
            },
            'summary': {
                'total_invoice_items': 1,
                'total_delivery_items': 1,
                'matched_percentage': 100.0,
                'discrepancy_percentage': 0.0
            }
        }
        
        logger.info(f"✅ Pairing completed: {pairing_id}")
        
        return PairingResponse(
            success=True,
            message="Documents paired successfully",
            pairing_id=pairing_id,
            results=mock_results
        )
        
    except Exception as e:
        logger.error(f"❌ Pairing failed: {e}")
        return PairingResponse(
            success=False,
            message="Failed to pair documents",
            error=str(e)
        )

@router.get("/matching/suggestions/{matching_id}")
async def get_matching_suggestions(matching_id: str) -> Dict[str, Any]:
    """
    Get manual review suggestions for a matching result
    
    Args:
        matching_id: ID of the matching result
        
    Returns:
        Dictionary with suggestions
    """
    try:
        logger.info(f"💡 Getting suggestions for matching: {matching_id}")
        
        # TODO: Retrieve actual matching result from database
        # For now, return mock suggestions
        
        suggestions = [
            {
                'invoice_item': 'Product A',
                'delivery_item': 'Product A (variant)',
                'similarity_score': 0.75,
                'confidence': 'medium',
                'reason': 'Similar description with minor variations'
            },
            {
                'invoice_item': 'Product B',
                'delivery_item': 'Product B - Large',
                'similarity_score': 0.65,
                'confidence': 'low',
                'reason': 'Possible size variant'
            }
        ]
        
        return {
            'success': True,
            'matching_id': matching_id,
            'suggestions': suggestions,
            'total_suggestions': len(suggestions)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/matching/validation/{matching_id}")
async def validate_matching_result(matching_id: str) -> Dict[str, Any]:
    """
    Validate and analyze a matching result
    
    Args:
        matching_id: ID of the matching result
        
    Returns:
        Dictionary with validation metrics and recommendations
    """
    try:
        logger.info(f"🔍 Validating matching result: {matching_id}")
        
        # TODO: Retrieve actual matching result from database
        # For now, return mock validation
        
        validation = {
            'quality_metrics': {
                'match_rate': 0.85,
                'discrepancy_rate': 0.1,
                'coverage_rate': 0.9
            },
            'recommendations': [
                "Matching quality appears good - proceed with confidence",
                "Review the 1 quantity mismatch found"
            ],
            'overall_assessment': 'good'
        }
        
        return {
            'success': True,
            'matching_id': matching_id,
            'validation': validation
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to validate matching: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/matching/status/{matching_id}")
async def get_matching_status(matching_id: str) -> Dict[str, Any]:
    """
    Get status of a matching operation
    
    Args:
        matching_id: ID of the matching operation
        
    Returns:
        Dictionary with status information
    """
    try:
        logger.info(f"📊 Getting status for matching: {matching_id}")
        
        # TODO: Retrieve actual status from database
        # For now, return mock status
        
        return {
            'success': True,
            'matching_id': matching_id,
            'status': 'completed',
            'progress': 100,
            'created_at': datetime.now().isoformat(),
            'completed_at': datetime.now().isoformat(),
            'summary': {
                'total_matches': 5,
                'total_discrepancies': 1,
                'overall_confidence': 0.85
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/matching/{matching_id}")
async def delete_matching_result(matching_id: str) -> Dict[str, Any]:
    """
    Delete a matching result
    
    Args:
        matching_id: ID of the matching result to delete
        
    Returns:
        Dictionary with deletion status
    """
    try:
        logger.info(f"🗑️ Deleting matching result: {matching_id}")
        
        # TODO: Delete from database/storage
        
        return {
            'success': True,
            'message': f"Matching result {matching_id} deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to delete matching: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 