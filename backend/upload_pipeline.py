"""
Enhanced Upload Pipeline with 100% Reliability

This module serves as the single entry point for all document processing,
providing consistent handling of PDF and image files with enhanced OCR
and comprehensive error recovery.

Key Features:
- Enhanced OCR with multiple fallback strategies
- Robust line item extraction with table detection
- Multi-page document processing with aggregation
- Adaptive timeouts and progress tracking
- Comprehensive error recovery
- Database integration with audit logging

Author: OWLIN Development Team
Version: 2.0.0
"""

import os
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
import uuid
import time

# PDF processing
import pypdfium2 as pdfium
from PIL import Image
import io

# Local imports
from ocr.enhanced_ocr_engine import enhanced_ocr_engine
from ocr.enhanced_line_item_extractor import enhanced_line_item_extractor, LineItem
from upload.adaptive_processor import adaptive_processor
from upload.multi_page_processor import multi_page_processor, DocumentResult
from upload_validator import validate_upload, get_validation_summary, create_upload_metadata
from db_manager import (
    init_db, save_invoice, save_delivery_note, save_file_hash,
    check_duplicate_invoice, check_duplicate_file_hash, log_processing_result
)

logger = logging.getLogger(__name__)

# Configuration constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB limit
CONFIDENCE_REVIEW_THRESHOLD = 0.65  # Flag for manual review if below this

@dataclass
class ProcessingResult:
    """Enhanced processing result with comprehensive data"""
    success: bool
    document_type: str
    supplier: str
    invoice_number: str
    date: str
    line_items: List[LineItem]
    overall_confidence: float
    processing_time: float
    pages_processed: int
    pages_failed: int
    error_message: Optional[str] = None
    warnings: List[str] = None
    debug_info: Dict[str, Any] = None

def process_document_enhanced(file_path: str, parse_templates: bool = True, 
                           save_debug: bool = False, validate_upload: bool = True,
                           db_path: str = "data/owlin.db") -> ProcessingResult:
    """
    Enhanced document processing with 100% reliability
    
    Args:
        file_path: Path to the document file
        parse_templates: Whether to parse invoice templates
        save_debug: Whether to save debug artifacts
        validate_upload: Whether to validate upload
        db_path: Database path
        
    Returns:
        ProcessingResult with comprehensive data
    """
    start_time = time.time()
    warnings = []
    debug_info = {}
    
    try:
        logger.info(f"🔄 Starting enhanced document processing: {file_path}")
        
        # Step 1: Validate file
        if validate_upload:
            logger.info("📋 Step 1: Validating file")
            validation_result = validate_upload(file_path)
            if not validation_result['valid']:
                error_msg = f"File validation failed: {validation_result.get('error', 'Unknown error')}"
                logger.error(f"❌ {error_msg}")
                return ProcessingResult(
                    success=False,
                    document_type='unknown',
                    supplier='Unknown',
                    invoice_number='Unknown',
                    date='Unknown',
                    line_items=[],
                    overall_confidence=0.0,
                    processing_time=time.time() - start_time,
                    pages_processed=0,
                    pages_failed=1,
                    error_message=error_msg,
                    warnings=warnings,
                    debug_info=debug_info
                )
        
        # Step 2: Process with adaptive processor
        logger.info("📋 Step 2: Processing document with adaptive processor")
        document_result = adaptive_processor.process_with_recovery(file_path)
        
        # Step 3: Save to database if successful
        if document_result.line_items or document_result.supplier != 'Unknown Supplier':
            logger.info("📋 Step 3: Saving to database")
            try:
                _save_to_database(document_result, file_path, db_path)
                logger.info("✅ Document saved to database")
            except Exception as e:
                logger.warning(f"⚠️ Database save failed: {e}")
                warnings.append(f"Database save failed: {e}")
        
        # Step 4: Log processing result
        logger.info("📋 Step 4: Logging processing result")
        _log_processing_result(file_path, document_result, time.time() - start_time)
        
        # Step 5: Prepare result
        processing_time = time.time() - start_time
        success = document_result.pages_processed > 0 or len(document_result.line_items) > 0
        
        # Check for manual review requirement
        if document_result.overall_confidence < CONFIDENCE_REVIEW_THRESHOLD:
            warnings.append("Low confidence - manual review recommended")
        
        if document_result.pages_failed > 0:
            warnings.append(f"{document_result.pages_failed} pages failed to process")
        
        result = ProcessingResult(
            success=success,
            document_type=document_result.document_type,
            supplier=document_result.supplier,
            invoice_number=document_result.invoice_number,
            date=document_result.date,
            line_items=document_result.line_items,
            overall_confidence=document_result.overall_confidence,
            processing_time=processing_time,
            pages_processed=document_result.pages_processed,
            pages_failed=document_result.pages_failed,
            warnings=warnings,
            debug_info={
                'total_processing_time': document_result.total_processing_time,
                'page_results_count': len(document_result.page_results),
                'line_items_count': len(document_result.line_items),
                'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
            }
        )
        
        logger.info(f"✅ Enhanced processing completed in {processing_time:.2f}s")
        logger.info(f"📊 Results: {result.pages_processed} pages processed, {len(result.line_items)} line items")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Enhanced processing failed: {e}")
        
        # Try emergency fallback processing
        try:
            logger.info("🔄 Attempting emergency fallback processing...")
            emergency_result = adaptive_processor._fallback_minimal_processing(file_path)
            
            if emergency_result and emergency_result.line_items:
                logger.info("✅ Emergency processing succeeded")
                return ProcessingResult(
                    success=True,
                    document_type=emergency_result.document_type,
                    supplier=emergency_result.supplier,
                    invoice_number=emergency_result.invoice_number,
                    date=emergency_result.date,
                    line_items=emergency_result.line_items,
                    overall_confidence=emergency_result.overall_confidence,
                    processing_time=time.time() - start_time,
                    pages_processed=emergency_result.pages_processed,
                    pages_failed=emergency_result.pages_failed,
                    error_message=None,
                    warnings=warnings + ["Emergency processing used"],
                    debug_info=debug_info
                )
        except Exception as fallback_error:
            logger.error(f"❌ Emergency fallback also failed: {fallback_error}")
        
        return ProcessingResult(
            success=False,
            document_type='unknown',
            supplier='Unknown',
            invoice_number='Unknown',
            date='Unknown',
            line_items=[],
            overall_confidence=0.0,
            processing_time=time.time() - start_time,
            pages_processed=0,
            pages_failed=1,
            error_message=str(e),
            warnings=warnings,
            debug_info=debug_info
        )

def _save_to_database(document_result: DocumentResult, file_path: str, db_path: str):
    """Save document result to database"""
    try:
        # Generate file hash for duplicate detection
        import hashlib
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        
        file_size = os.path.getsize(file_path)
        file_ext = Path(file_path).suffix.lower()
        content_type = "application/pdf" if file_ext == '.pdf' else "image/jpeg"
        
        # Save file hash
        save_file_hash(file_hash, file_path, file_size, content_type)
        
        # Convert line items to database format
        line_items_data = []
        for item in document_result.line_items:
            line_items_data.append({
                'description': item.description,
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'total_price': item.total_price,
                'confidence': item.confidence,
                'item_description': item.item_description,
                'unit_price_excl_vat': item.unit_price_excl_vat,
                'line_total_excl_vat': item.line_total_excl_vat
            })
        
        # Prepare invoice data
        invoice_data = {
            'supplier_name': document_result.supplier,
            'invoice_number': document_result.invoice_number,
            'invoice_date': document_result.date,
            'net_amount': sum(item.total_price for item in document_result.line_items),
            'vat_amount': 0.0,  # Will be calculated if needed
            'total_amount': sum(item.total_price for item in document_result.line_items),
            'currency': 'GBP',
            'file_path': file_path,
            'file_hash': file_hash,
            'ocr_confidence': document_result.overall_confidence * 100,
            'page_numbers': list(range(1, document_result.pages_processed + 1)),
            'line_items': line_items_data,
            'subtotal': sum(item.total_price for item in document_result.line_items),
            'vat': 0.0,
            'vat_rate': 0.2,
            'total_incl_vat': sum(item.total_price for item in document_result.line_items)
        }
        
        # Save invoice
        save_invoice(invoice_data, db_path)
        logger.info(f"💾 Invoice saved to database: {document_result.invoice_number}")
        
    except Exception as e:
        logger.error(f"❌ Database save failed: {e}")
        raise

def _log_processing_result(file_path: str, document_result: DocumentResult, processing_time: float):
    """Log processing result for audit trail"""
    try:
        log_processing_result(
            file_path=file_path,
            status='success' if document_result.pages_processed > 0 else 'error',
            ocr_confidence=document_result.overall_confidence * 100,
            processing_time=processing_time,
            pages_processed=document_result.pages_processed,
            pages_failed=document_result.pages_failed,
            line_items_count=len(document_result.line_items)
        )
    except Exception as e:
        logger.warning(f"⚠️ Failed to log processing result: {e}")

def process_document(file_path: str, parse_templates: bool = True, 
                   save_debug: bool = False, validate_upload: bool = True,
                   db_path: str = "data/owlin.db") -> Dict[str, Any]:
    """
    Legacy wrapper for enhanced document processing
    
    Args:
        file_path: Path to the document file
        parse_templates: Whether to parse invoice templates
        save_debug: Whether to save debug artifacts
        validate_upload: Whether to validate upload
        db_path: Database path
        
    Returns:
        Dictionary with processing results (legacy format)
    """
    # Use enhanced processing
    result = process_document_enhanced(file_path, parse_templates, save_debug, validate_upload, db_path)
    
    # Convert to legacy format
    return {
        'success': result.success,
        'document_type': result.document_type,
        'supplier': result.supplier,
        'invoice_number': result.invoice_number,
        'date': result.date,
        'line_items': [
            {
                'description': item.description,
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'total_price': item.total_price,
                'confidence': item.confidence
            }
            for item in result.line_items
        ],
        'overall_confidence': result.overall_confidence,
        'processing_time': result.processing_time,
        'pages_processed': result.pages_processed,
        'pages_failed': result.pages_failed,
        'error_message': result.error_message,
        'warnings': result.warnings or [],
        'debug_info': result.debug_info or {}
    }

# Legacy functions for backward compatibility
def run_invoice_ocr(image: Image.Image, page_number: int = 1):
    """Legacy OCR function - now uses enhanced engine"""
    return enhanced_ocr_engine.run_ocr_with_retry(image, page_number)

def convert_pdf_to_images(file_path: str) -> List[Image.Image]:
    """Legacy PDF conversion - now uses multi-page processor"""
    return multi_page_processor._convert_to_images(file_path)

# Global instances for easy access
enhanced_ocr_engine = enhanced_ocr_engine
enhanced_line_item_extractor = enhanced_line_item_extractor
adaptive_processor = adaptive_processor
multi_page_processor = multi_page_processor 