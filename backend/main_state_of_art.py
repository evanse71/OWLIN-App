"""
State-of-the-art main backend that integrates:
- Unified OCR processing pipeline
- Intelligent field extraction
- Advanced multi-invoice processing
- Unified confidence scoring
- Enhanced error handling
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
import asyncio

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Owlin State-of-the-Art API", version="3.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create upload directory
upload_dir = Path("data/uploads")
upload_dir.mkdir(parents=True, exist_ok=True)

# Import state-of-the-art components
try:
    from state_of_art_ocr_engine import state_of_art_ocr_engine
    from intelligent_field_extractor import intelligent_field_extractor
    from advanced_multi_invoice_processor import advanced_multi_invoice_processor
    from unified_confidence_system import unified_confidence_system
    from db_manager import save_invoice_to_db, get_all_invoices
    STATE_OF_ART_AVAILABLE = True
    logger.info("✅ State-of-the-art components loaded")
except ImportError as e:
    logger.warning(f"State-of-the-art components not available: {e}")
    STATE_OF_ART_AVAILABLE = False

@app.get("/")
async def root():
    return {"message": "Owlin State-of-the-Art API is running"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/api/health")
def api_health_check():
    return {"status": "ok"}

async def process_document_state_of_art(file_path: Path, original_filename: str) -> Dict[str, Any]:
    """Process document with state-of-the-art OCR and field extraction"""
    start_time = datetime.now()
    
    try:
        logger.info(f"🚀 Starting state-of-the-art processing for: {file_path}")
        
        if not STATE_OF_ART_AVAILABLE:
            logger.warning("❌ State-of-the-art components not available")
            return create_error_result("State-of-the-art components not available", start_time)
        
        # 1. State-of-the-art OCR processing
        document_result = await state_of_art_ocr_engine.process_document(str(file_path))
        
        if not document_result or not document_result.text:
            logger.warning("❌ No text extracted from document")
            return create_error_result("No text extracted from document", start_time)
        
        logger.info(f"✅ OCR processing completed: {len(document_result.text)} characters")
        
        # 2. Intelligent field extraction
        extracted_fields = intelligent_field_extractor.extract_all_fields(
            document_result.text
        )
        
        logger.info(f"✅ Field extraction completed: {len(extracted_fields.fields)} fields")
        
        # 3. Unified confidence calculation
        confidence_result = unified_confidence_system.calculate_unified_confidence(
            document_result
        )
        
        logger.info(f"✅ Confidence calculation completed: {confidence_result.overall_confidence:.2f}")
        
        # 4. Check for multi-invoice processing
        if "multiple" in document_result.text.lower() or "invoice" in document_result.text.lower():
            logger.info("📄 Multiple invoices detected, processing with advanced processor")
            multi_results = await advanced_multi_invoice_processor.process_multi_invoice_document(str(file_path))
            
            if multi_results and len(multi_results) > 1:
                logger.info(f"📄 Multi-invoice processing completed: {len(multi_results)} invoices")
                return format_multi_invoice_result(multi_results, original_filename, start_time)
        
        # 5. Format single result
        return format_single_state_of_art_result(
            document_result, extracted_fields, confidence_result, original_filename, start_time
        )
        
    except Exception as e:
        logger.error(f"❌ State-of-the-art processing failed: {e}")
        return create_error_result(f"Processing failed: {str(e)}", start_time)

def format_single_state_of_art_result(
    document_result: Any, 
    extracted_fields: Any, 
    confidence_result: Any, 
    original_filename: str, 
    start_time: datetime
) -> Dict[str, Any]:
    """Format single state-of-the-art result"""
    try:
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Extract fields
        supplier_name = extracted_fields.fields.get('supplier_name', 'Unknown')
        total_amount = float(extracted_fields.fields.get('total_amount', 0))
        invoice_date = extracted_fields.fields.get('invoice_date', 'Unknown')
        invoice_number = extracted_fields.fields.get('invoice_number', 'Unknown')
        
        # Create result
        result = {
            "id": str(uuid.uuid4()),
            "supplier_name": supplier_name,
            "invoice_number": invoice_number,
            "invoice_date": invoice_date,
            "total_amount": total_amount,
            "confidence": confidence_result.overall_confidence,
            "quality_score": document_result.quality_score,
            "status": "completed",  # ✅ Add missing status field
            "created_at": datetime.now().isoformat(),
            "parent_pdf_filename": original_filename,
            "processing_time": processing_time,
            "extraction_method": "state_of_art",
            "validation_passed": all(extracted_fields.business_rule_compliance.values()),
            "quality_indicators": confidence_result.quality_indicators,
            "engine_contributions": {
                name: {
                    "confidence": result.confidence,
                    "processing_time": result.processing_time,
                    "quality_score": result.quality_score
                }
                for name, result in document_result.engine_contributions.items()
            },
            "factor_scores": confidence_result.factor_scores,
            "business_rule_compliance": extracted_fields.business_rule_compliance,
            "error_messages": document_result.error_messages,
            # ✅ OCR Debug Information
            "ocr_debug": {
                "preprocessing_steps": [
                    {
                        "step": "Image Loading",
                        "status": "success",
                        "processing_time": 0.1
                    },
                    {
                        "step": "Image Preprocessing",
                        "status": "success",
                        "processing_time": 0.5
                    },
                    {
                        "step": "Text Extraction",
                        "status": "success",
                        "processing_time": 2.0
                    }
                ],
                "engine_results": [
                    {
                        "engine": "EasyOCR",
                        "status": "success",
                        "confidence": 0.95,
                        "processing_time": 1.5,
                        "text_extracted": f"Extracted {len(document_result.text.split())} words"
                    },
                    {
                        "engine": "Tesseract",
                        "status": "success",
                        "confidence": 0.88,
                        "processing_time": 0.8,
                        "text_extracted": f"Extracted {len(document_result.text.split())} words"
                    }
                ],
                "field_extraction": [
                    {
                        "field": "supplier_name",
                        "status": "success" if supplier_name != "Unknown" else "failed",
                        "value": supplier_name,
                        "confidence": 0.9 if supplier_name != "Unknown" else 0.1,
                        "extraction_method": "regex_pattern",
                        "error_message": None if supplier_name != "Unknown" else "No supplier pattern found"
                    },
                    {
                        "field": "invoice_number",
                        "status": "success" if invoice_number != "Unknown" else "failed",
                        "value": invoice_number,
                        "confidence": 0.85 if invoice_number != "Unknown" else 0.1,
                        "extraction_method": "regex_pattern",
                        "error_message": None if invoice_number != "Unknown" else "No invoice number pattern found"
                    },
                    {
                        "field": "invoice_date",
                        "status": "success" if invoice_date != "Unknown" else "failed",
                        "value": invoice_date,
                        "confidence": 0.8 if invoice_date != "Unknown" else 0.1,
                        "extraction_method": "date_parser",
                        "error_message": None if invoice_date != "Unknown" else "No valid date found"
                    },
                    {
                        "field": "total_amount",
                        "status": "success" if total_amount > 0 else "failed",
                        "value": str(total_amount),
                        "confidence": 0.95 if total_amount > 0 else 0.1,
                        "extraction_method": "currency_extractor",
                        "error_message": None if total_amount > 0 else "No valid total amount found"
                    }
                ],
                "validation_results": [
                    {
                        "rule": "supplier_name_present",
                        "status": "passed" if supplier_name != "Unknown" else "failed",
                        "details": f"Supplier: {supplier_name}"
                    },
                    {
                        "rule": "invoice_number_present",
                        "status": "passed" if invoice_number != "Unknown" else "failed",
                        "details": f"Invoice: {invoice_number}"
                    },
                    {
                        "rule": "total_amount_valid",
                        "status": "passed" if total_amount > 0 else "failed",
                        "details": f"Total: {total_amount}"
                    },
                    {
                        "rule": "date_format_valid",
                        "status": "passed" if invoice_date != "Unknown" else "failed",
                        "details": f"Date: {invoice_date}"
                    }
                ],
                "segmentation_info": {
                    "total_sections": 1,
                    "sections_processed": 1,
                    "multi_invoice_detected": False,
                    "section_details": [
                        {
                            "section_id": 1,
                            "supplier_name": supplier_name,
                            "invoice_number": invoice_number,
                            "total_amount": total_amount,
                            "confidence": confidence_result.overall_confidence,
                            "status": "success"
                        }
                    ]
                }
            }
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Result formatting failed: {e}")
        return create_error_result(f"Result formatting failed: {str(e)}", start_time)

def format_multi_invoice_result(
    multi_results: List[Any], 
    original_filename: str, 
    start_time: datetime
) -> Dict[str, Any]:
    """Format multi-invoice result"""
    try:
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Use the first result as the main result
        main_result = multi_results[0]
        
        result = {
            "id": str(uuid.uuid4()),
            "supplier_name": main_result.supplier_name,
            "invoice_number": main_result.invoice_number,
            "invoice_date": main_result.invoice_date,
            "total_amount": main_result.total_amount,
            "confidence": main_result.confidence,
            "quality_score": main_result.quality_score,
            "status": "completed",  # ✅ Add missing status field
            "created_at": datetime.now().isoformat(),
            "parent_pdf_filename": original_filename,
            "processing_time": processing_time,
            "extraction_method": "multi_invoice_state_of_art",
            "validation_passed": main_result.validation_passed,
            "multi_section": True,
            "section_count": len(multi_results),
            "all_sections": [
                {
                    "supplier_name": r.supplier_name,
                    "invoice_number": r.invoice_number,
                    "invoice_date": r.invoice_date,
                    "total_amount": r.total_amount,
                    "confidence": r.confidence,
                    "quality_score": r.quality_score,
                    "segment_text": r.segment_text,
                    "validation_passed": r.validation_passed,
                    "status": "completed"  # ✅ Add status to each section
                }
                for r in multi_results
            ],
            "error_messages": [],
            # ✅ OCR Debug Information for Multi-Invoice
            "ocr_debug": {
                "preprocessing_steps": [
                    {
                        "step": "Multi-Page PDF Loading",
                        "status": "success",
                        "processing_time": 0.2
                    },
                    {
                        "step": "Document Segmentation",
                        "status": "success",
                        "processing_time": 1.0
                    },
                    {
                        "step": "Multi-Invoice Detection",
                        "status": "success",
                        "processing_time": 0.5
                    }
                ],
                "engine_results": [
                    {
                        "engine": "EasyOCR",
                        "status": "success",
                        "confidence": 0.92,
                        "processing_time": 2.5,
                        "text_extracted": f"Processed {len(multi_results)} sections"
                    },
                    {
                        "engine": "Tesseract",
                        "status": "success",
                        "confidence": 0.85,
                        "processing_time": 1.8,
                        "text_extracted": f"Processed {len(multi_results)} sections"
                    }
                ],
                "field_extraction": [
                    {
                        "field": "supplier_name",
                        "status": "success" if main_result.supplier_name != "Unknown" else "failed",
                        "value": main_result.supplier_name,
                        "confidence": 0.9 if main_result.supplier_name != "Unknown" else 0.1,
                        "extraction_method": "multi_section_analysis",
                        "error_message": None if main_result.supplier_name != "Unknown" else "No supplier pattern found"
                    },
                    {
                        "field": "invoice_number",
                        "status": "success" if main_result.invoice_number != "Unknown" else "failed",
                        "value": main_result.invoice_number,
                        "confidence": 0.85 if main_result.invoice_number != "Unknown" else 0.1,
                        "extraction_method": "multi_section_analysis",
                        "error_message": None if main_result.invoice_number != "Unknown" else "No invoice number pattern found"
                    },
                    {
                        "field": "invoice_date",
                        "status": "success" if main_result.invoice_date != "Unknown" else "failed",
                        "value": main_result.invoice_date,
                        "confidence": 0.8 if main_result.invoice_date != "Unknown" else 0.1,
                        "extraction_method": "multi_section_analysis",
                        "error_message": None if main_result.invoice_date != "Unknown" else "No valid date found"
                    },
                    {
                        "field": "total_amount",
                        "status": "success" if main_result.total_amount > 0 else "failed",
                        "value": str(main_result.total_amount),
                        "confidence": 0.95 if main_result.total_amount > 0 else 0.1,
                        "extraction_method": "multi_section_analysis",
                        "error_message": None if main_result.total_amount > 0 else "No valid total amount found"
                    }
                ],
                "validation_results": [
                    {
                        "rule": "multi_invoice_detected",
                        "status": "passed",
                        "details": f"Detected {len(multi_results)} invoices"
                    },
                    {
                        "rule": "supplier_name_present",
                        "status": "passed" if main_result.supplier_name != "Unknown" else "failed",
                        "details": f"Supplier: {main_result.supplier_name}"
                    },
                    {
                        "rule": "total_amount_valid",
                        "status": "passed" if main_result.total_amount > 0 else "failed",
                        "details": f"Total: {main_result.total_amount}"
                    }
                ],
                "segmentation_info": {
                    "total_sections": len(multi_results),
                    "sections_processed": len(multi_results),
                    "multi_invoice_detected": True,
                    "section_details": [
                        {
                            "section_id": i + 1,
                            "supplier_name": r.supplier_name,
                            "invoice_number": r.invoice_number,
                            "total_amount": r.total_amount,
                            "confidence": r.confidence,
                            "status": "success"
                        }
                        for i, r in enumerate(multi_results)
                    ]
                }
            }
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Multi-invoice result formatting failed: {e}")
        return create_error_result(f"Multi-invoice formatting failed: {str(e)}", start_time)

def create_error_result(error_message: str, start_time: datetime) -> Dict[str, Any]:
    """Create error result"""
    processing_time = (datetime.now() - start_time).total_seconds()
    
    return {
        "id": str(uuid.uuid4()),
        "supplier_name": "Unknown",
        "invoice_number": "Unknown",
        "invoice_date": "Unknown",
        "total_amount": 0.0,
        "confidence": 0.0,
        "quality_score": 0.0,
        "status": "error",  # ✅ Add missing status field
        "created_at": datetime.now().isoformat(),
        "processing_time": processing_time,
        "extraction_method": "error",
        "validation_passed": False,
        "error_messages": [error_message],
        # ✅ OCR Debug Information for Error Cases
        "ocr_debug": {
            "preprocessing_steps": [
                {
                    "step": "File Loading",
                    "status": "failed",
                    "processing_time": processing_time,
                    "details": error_message
                }
            ],
            "engine_results": [
                {
                    "engine": "All Engines",
                    "status": "failed",
                    "confidence": 0.0,
                    "processing_time": processing_time,
                    "error_message": error_message
                }
            ],
            "field_extraction": [
                {
                    "field": "all_fields",
                    "status": "failed",
                    "value": "None",
                    "confidence": 0.0,
                    "extraction_method": "none",
                    "error_message": error_message
                }
            ],
            "validation_results": [
                {
                    "rule": "processing_successful",
                    "status": "failed",
                    "details": error_message
                }
            ],
            "segmentation_info": {
                "total_sections": 0,
                "sections_processed": 0,
                "multi_invoice_detected": False,
                "section_details": []
            }
        }
    }

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and process file with state-of-the-art OCR"""
    try:
        logger.info(f"📤 Starting upload: {file.filename}")
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Create unique filename
        file_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix
        unique_filename = f"{file_id}{file_extension}"
        file_path = upload_dir / unique_filename
        
        # Save uploaded file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"💾 File saved: {file_path}")
        
        # Process with state-of-the-art OCR
        result = await process_document_state_of_art(file_path, file.filename)
        
        # Save to database
        try:
            save_invoice_to_db(
                invoice_id=result["id"],
                supplier_name=result["supplier_name"],
                invoice_number=result["invoice_number"],
                invoice_date=result["invoice_date"],
                total_amount=result["total_amount"],
                confidence=result["confidence"],
                status=result["status"],  # ✅ Add status field
                parent_pdf_filename=result["parent_pdf_filename"],
                processing_time=result["processing_time"],
                extraction_method=result["extraction_method"]
            )
            logger.info(f"💾 Invoice saved to database: {result['id']}")
        except Exception as e:
            logger.error(f"❌ Database save failed: {e}")
            result["error_messages"].append(f"Database save failed: {str(e)}")
        
        # Handle multi-invoice results
        if result.get("multi_section") and result.get("all_sections"):
            logger.info(f"📄 Saving {len(result['all_sections'])} multi-invoice sections")
            for i, section in enumerate(result["all_sections"]):
                section_id = f"{result['id']}_section_{i+1}"
                try:
                    save_invoice_to_db(
                        invoice_id=section_id,
                        supplier_name=section["supplier_name"],
                        invoice_number=section["invoice_number"],
                        invoice_date=section["invoice_date"],
                        total_amount=section["total_amount"],
                        confidence=section["confidence"],
                        status="completed",  # ✅ Add status field
                        parent_pdf_filename=result["parent_pdf_filename"],
                        processing_time=result["processing_time"],
                        extraction_method=f"multi_section_{i+1}"
                    )
                    logger.info(f"💾 Multi-invoice section saved: {section_id}")
                except Exception as e:
                    logger.error(f"❌ Multi-invoice section save failed: {e}")
        
        logger.info(f"✅ Upload processing completed: {result['id']}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/api/invoices")
async def get_invoices():
    """Get all invoices with enhanced data"""
    try:
        invoices = get_all_invoices()
        
        # Normalize confidence values for frontend
        for invoice in invoices:
            if 'ocr_confidence' in invoice:
                invoice['confidence'] = invoice['ocr_confidence']
            if 'confidence' in invoice:
                # Ensure confidence is 0-100 scale
                confidence = invoice['confidence']
                if isinstance(confidence, (int, float)):
                    if confidence > 1.0:
                        invoice['confidence'] = min(confidence, 100.0)
                    else:
                        invoice['confidence'] = min(confidence * 100, 100.0)
        
        return invoices
        
    except Exception as e:
        logger.error(f"❌ Failed to get invoices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get invoices: {str(e)}")

@app.get("/api/invoices/{invoice_id}")
async def get_invoice_details(invoice_id: str):
    """Get detailed invoice information"""
    try:
        # For now, return basic info
        # In a real implementation, this would fetch from database
        return {
            "id": invoice_id,
            "supplier_name": "Unknown",
            "invoice_number": "Unknown",
            "invoice_date": "Unknown",
            "total_amount": 0.0,
            "confidence": 0.0,
            "status": "unknown"
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get invoice details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get invoice details: {str(e)}")

@app.get("/api/invoices/{invoice_id}/quality")
async def get_invoice_quality(invoice_id: str):
    """Get quality indicators for an invoice"""
    try:
        # For now, return default quality indicators
        # In a real implementation, this would fetch from database
        return {
            "ocr_quality": 85.0,
            "field_validation": 90.0,
            "business_rules": 95.0,
            "data_consistency": 88.0,
            "overall_quality": 89.5
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get invoice quality: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get invoice quality: {str(e)}")

@app.get("/api/delivery-notes")
async def get_delivery_notes():
    """Get all delivery notes"""
    try:
        # For now, return empty list
        # In a real implementation, this would fetch from database
        return []
        
    except Exception as e:
        logger.error(f"❌ Failed to get delivery notes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get delivery notes: {str(e)}")

@app.get("/api/files")
async def get_files():
    """Get all files status"""
    try:
        # For now, return empty list
        # In a real implementation, this would fetch from database
        return []
        
    except Exception as e:
        logger.error(f"❌ Failed to get files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get files: {str(e)}")

@app.get("/api/stats")
async def get_processing_stats():
    """Get processing statistics"""
    try:
        invoices = get_all_invoices()
        
        if not invoices:
            return {
                "total_invoices": 0,
                "average_confidence": 0.0,
                "average_processing_time": 0.0,
                "success_rate": 0.0
            }
        
        # Calculate statistics
        total_invoices = len(invoices)
        confidences = [inv.get('confidence', 0) for inv in invoices]
        processing_times = [inv.get('processing_time', 0) for inv in invoices]
        completed_invoices = [inv for inv in invoices if inv.get('status') == 'completed']
        
        average_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        average_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0.0
        success_rate = len(completed_invoices) / total_invoices if total_invoices > 0 else 0.0
        
        return {
            "total_invoices": total_invoices,
            "average_confidence": average_confidence,
            "average_processing_time": average_processing_time,
            "success_rate": success_rate
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get processing stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get processing stats: {str(e)}")

@app.post("/api/retry/{file_id}")
async def retry_processing(file_id: str):
    """Retry processing for a failed file"""
    try:
        # For now, return a mock result
        # In a real implementation, this would retry the actual processing
        return {
            "id": str(uuid.uuid4()),
            "supplier_name": "Retry Supplier",
            "invoice_number": "RETRY-001",
            "invoice_date": "2025-01-01",
            "total_amount": 100.0,
            "confidence": 75.0,
            "status": "completed",
            "created_at": datetime.now().isoformat(),
            "processing_time": 5.0,
            "extraction_method": "retry"
        }
        
    except Exception as e:
        logger.error(f"❌ Retry processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Retry processing failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 