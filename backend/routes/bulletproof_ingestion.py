"""
Bulletproof Ingestion v3 Routes

FastAPI routes for the bulletproof ingestion system that handles:
- Multiple invoices in one file
- Split documents across multiple files
- Out-of-order pages
- Duplicate detection
- Cross-file stitching
- Document classification
"""

import json
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from pydantic import BaseModel

# Import the bulletproof ingestion components
try:
    from backend.ingest.intake_router import IntakeRouter
    from backend.ingest.page_fingerprints import PageFingerprinter
    from backend.ingest.page_classifier import PageClassifier
    from backend.ingest.cross_file_stitcher import CrossFileStitcher
    from backend.ingest.deduper import Deduper
    from backend.ingest.canonical_builder import CanonicalBuilder
    from backend.ocr.multi_document_segmenter import MultiDocumentSegmenter
    BULLETPROOF_INGESTION_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Bulletproof ingestion components not available: {e}")
    BULLETPROOF_INGESTION_AVAILABLE = False

from backend.utils.db_manager import get_db_connection
from backend.ocr.unified_ocr_engine import get_unified_ocr_engine

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize components
intake_router = None
if BULLETPROOF_INGESTION_AVAILABLE:
    try:
        intake_router = IntakeRouter()
        logger.info("✅ Bulletproof ingestion router initialized")
    except Exception as e:
        logger.error(f"Failed to initialize bulletproof ingestion router: {e}")
        BULLETPROOF_INGESTION_AVAILABLE = False

class BulletproofUploadResponse(BaseModel):
    """Response model for bulletproof upload"""
    success: bool
    file_id: str
    filename: str
    processing_time: float
    canonical_invoices: List[Dict[str, Any]]
    canonical_documents: List[Dict[str, Any]]
    duplicate_groups: List[Dict[str, Any]]
    stitch_groups: List[Dict[str, Any]]
    warnings: List[str]
    errors: List[str]
    metadata: Dict[str, Any]
    needs_review: bool = False
    proposed_segments: List[Dict[str, Any]] = []
    summary: Dict[str, Any] = {}

@router.post("/upload-bulletproof", response_model=BulletproofUploadResponse)
async def upload_file_bulletproof(
    file: UploadFile = File(...),
    background_tasks: Optional[BackgroundTasks] = None
):
    """
    Upload file using bulletproof ingestion v3 system
    
    This endpoint uses the comprehensive ingestion system that can handle:
    - Multiple invoices in one file
    - Split documents across multiple files
    - Out-of-order pages
    - Duplicate detection
    - Cross-file stitching
    - Document classification
    
    Returns:
        BulletproofUploadResponse with processing results
    """
    if not BULLETPROOF_INGESTION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Bulletproof ingestion system not available")
    
    start_time = datetime.now()
    
    try:
        logger.info(f"🚀 Starting bulletproof ingestion for: {file.filename}")
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Check file size (max 50MB)
        content = await file.read()
        if len(content) > 50 * 1024 * 1024:  # 50MB
            raise HTTPException(status_code=413, detail="File too large (max 50MB)")
        
        # Save uploaded file
        file_id = str(uuid.uuid4())
        upload_dir = Path("data/uploads")
        upload_dir.mkdir(exist_ok=True)
        file_path = upload_dir / f"{file_id}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        logger.info(f"💾 File saved to: {file_path}")
        
        # Prepare file data for bulletproof ingestion
        file_data = {
            'id': file_id,
            'file_path': str(file_path),
            'filename': file.filename,
            'file_size': len(content),
            'upload_time': datetime.now(),
            'images': [],
            'ocr_texts': []
        }
        
        # Process file to extract images and OCR text
        try:
            logger.info("📄 Extracting images and OCR text...")
            unified_engine = get_unified_ocr_engine()
            
            # Get images from the file
            images = await unified_engine.extract_images_from_file(str(file_path))
            file_data['images'] = images
            
            # Get OCR text for each image
            ocr_texts = []
            for i, image in enumerate(images):
                try:
                    # Use unified engine to get OCR text
                    text_result = await unified_engine.extract_text_from_image(image)
                    ocr_texts.append(text_result.get('text', ''))
                    logger.debug(f"✅ Extracted OCR text from image {i+1}/{len(images)}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to extract OCR text from image {i}: {e}")
                    ocr_texts.append('')
            
            file_data['ocr_texts'] = ocr_texts
            
        except Exception as e:
            logger.error(f"Failed to process file for bulletproof ingestion: {e}")
            # Fallback to basic processing
            file_data['images'] = []
            file_data['ocr_texts'] = ['']
        
        # Process with bulletproof ingestion
        logger.info("🔄 Processing with bulletproof ingestion pipeline...")
        files_to_process = [file_data]
        intake_result = intake_router.process_upload(files_to_process)
        
        if not intake_result.success:
            error_msg = f"Bulletproof ingestion failed: {intake_result.errors}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Convert canonical entities to response format
        canonical_invoices = []
        for invoice in intake_result.canonical_invoices:
            canonical_invoices.append({
                'id': invoice.canonical_id,
                'supplier_name': invoice.supplier_name,
                'invoice_number': invoice.invoice_number,
                'invoice_date': invoice.invoice_date,
                'currency': invoice.currency,
                'subtotal': invoice.subtotal,
                'tax': invoice.tax,
                'total_amount': invoice.total_amount,
                'field_confidence': invoice.field_confidence,
                'warnings': invoice.warnings,
                'raw_extraction': invoice.raw_extraction,
                'source_segments': invoice.source_segments,
                'source_pages': invoice.source_pages,
                'confidence': invoice.confidence,
                'created_at': invoice.created_at.isoformat() if invoice.created_at else None
            })
        
        canonical_documents = []
        for doc in intake_result.canonical_documents:
            canonical_documents.append({
                'id': doc.canonical_id,
                'doc_type': doc.doc_type,
                'supplier_name': doc.supplier_name,
                'document_number': doc.document_number,
                'document_date': doc.document_date,
                'content': doc.content,
                'confidence': doc.confidence,
                'source_segments': doc.source_segments,
                'source_pages': doc.source_pages,
                'created_at': doc.created_at.isoformat() if doc.created_at else None
            })
        
        # Convert duplicate groups
        duplicate_groups = []
        for group in intake_result.duplicate_groups:
            duplicate_groups.append({
                'id': group.group_id,
                'primary_id': group.primary_id,
                'duplicates': group.duplicates,
                'confidence': group.confidence,
                'duplicate_type': group.duplicate_type,
                'reasons': group.reasons
            })
        
        # Convert stitch groups
        stitch_groups = []
        for group in intake_result.stitch_groups:
            stitch_groups.append({
                'id': group.group_id,
                'segments': [
                    {
                        'id': seg.get('id', ''),
                        'file_id': seg.get('file_id', ''),
                        'doc_type': seg.get('doc_type', ''),
                        'supplier_guess': seg.get('supplier_guess', ''),
                        'page_range': seg.get('page_numbers', []),
                        'confidence': seg.get('confidence', 0.0)
                    }
                    for seg in group.segments
                ],
                'confidence': group.confidence,
                'doc_type': group.doc_type,
                'supplier_guess': group.supplier_guess,
                'invoice_numbers': group.invoice_numbers,
                'dates': group.dates,
                'reasons': group.reasons
            })
        
        # Determine if review is needed
        needs_review = len(intake_result.warnings) > 0 or len(duplicate_groups) > 0
        
        # Create summary
        summary = {
            'files_processed': intake_result.metadata.get('files_processed', 1),
            'pages_processed': intake_result.metadata.get('pages_processed', 0),
            'canonical_invoices_created': len(canonical_invoices),
            'canonical_documents_created': len(canonical_documents),
            'duplicates_found': intake_result.metadata.get('duplicates_found', 0),
            'stitch_groups_created': len(stitch_groups),
            'processing_time_seconds': processing_time,
            'needs_review': needs_review
        }
        
        logger.info(f"✅ Bulletproof ingestion completed successfully: {summary}")
        
        return BulletproofUploadResponse(
            success=True,
            file_id=file_id,
            filename=file.filename,
            processing_time=processing_time,
            canonical_invoices=canonical_invoices,
            canonical_documents=canonical_documents,
            duplicate_groups=duplicate_groups,
            stitch_groups=stitch_groups,
            warnings=intake_result.warnings,
            errors=intake_result.errors,
            metadata=intake_result.metadata,
            needs_review=needs_review,
            proposed_segments=[],  # TODO: Implement proposed segments
            summary=summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Bulletproof ingestion failed: {str(e)}"
        logger.error(error_msg)
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return BulletproofUploadResponse(
            success=False,
            file_id=file_id if 'file_id' in locals() else str(uuid.uuid4()),
            filename=file.filename if hasattr(file, 'filename') else "unknown",
            processing_time=processing_time,
            canonical_invoices=[],
            canonical_documents=[],
            duplicate_groups=[],
            stitch_groups=[],
            warnings=[],
            errors=[error_msg],
            metadata={'error': error_msg},
            needs_review=False,
            proposed_segments=[],
            summary={'error': error_msg}
        )

@router.get("/bulletproof-status")
async def get_bulletproof_status():
    """Get the status of the bulletproof ingestion system"""
    return {
        "available": BULLETPROOF_INGESTION_AVAILABLE,
        "components": {
            "intake_router": intake_router is not None,
            "page_fingerprinter": "PageFingerprinter" in globals(),
            "page_classifier": "PageClassifier" in globals(),
            "cross_file_stitcher": "CrossFileStitcher" in globals(),
            "deduper": "Deduper" in globals(),
            "canonical_builder": "CanonicalBuilder" in globals(),
            "multi_document_segmenter": "MultiDocumentSegmenter" in globals()
        },
        "config_loaded": Path("data/config/ingestion_thresholds.json").exists()
    }

@router.get("/bulletproof-config")
async def get_bulletproof_config():
    """Get the current bulletproof ingestion configuration"""
    try:
        config_path = Path("data/config/ingestion_thresholds.json")
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
            return {"success": True, "config": config}
        else:
            return {"success": False, "error": "Configuration file not found"}
    except Exception as e:
        return {"success": False, "error": f"Failed to load configuration: {e}"}

@router.post("/bulletproof-test")
async def test_bulletproof_components():
    """Test the bulletproof ingestion components"""
    if not BULLETPROOF_INGESTION_AVAILABLE:
        return {"success": False, "error": "Bulletproof ingestion not available"}
    
    try:
        # Test each component
        test_results = {}
        
        # Test intake router
        if intake_router:
            test_results["intake_router"] = "✅ Available"
        else:
            test_results["intake_router"] = "❌ Not available"
        
        # Test other components
        components = [
            "PageFingerprinter",
            "PageClassifier", 
            "CrossFileStitcher",
            "Deduper",
            "CanonicalBuilder",
            "MultiDocumentSegmenter"
        ]
        
        for component in components:
            try:
                exec(f"import {component}")
                test_results[component] = "✅ Available"
            except Exception as e:
                test_results[component] = f"❌ Not available: {e}"
        
        return {"success": True, "test_results": test_results}
        
    except Exception as e:
        return {"success": False, "error": f"Test failed: {e}"} 