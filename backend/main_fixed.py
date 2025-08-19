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
import json

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import analytics routes
try:
    from routes.analytics import router as analytics_router
except ImportError:
    # If analytics routes aren't available, create a dummy router
    from fastapi import APIRouter
    analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])
    
    @analytics_router.get("/dashboard")
    async def get_dashboard_analytics():
        return {"message": "Analytics not available in this server"}

# Import document queue routes
try:
    from routes.document_queue import router as document_queue_router
except ImportError:
    # If document queue routes aren't available, create a dummy router
    from fastapi import APIRouter
    document_queue_router = APIRouter(prefix="/documents", tags=["documents"])
    
    @document_queue_router.get("/queue")
    async def get_documents_for_review():
        return {"documents": []}

# Import updates routes
try:
    from routes.updates import router as updates_router
except ImportError:
    # If updates routes are not available, create a dummy router
    from fastapi import APIRouter
    updates_router = APIRouter(prefix="/updates", tags=["updates"])
    
    @updates_router.get("/available")
    async def get_available_updates():
        return {"updates": []}

# Import backup routes
try:
    from routes.backups import router as backups_router
except ImportError:
    # If backup routes are not available, create a dummy router
    from fastapi import APIRouter
    backups_router = APIRouter(prefix="/backups", tags=["backups"])
    
    @backups_router.get("")
    async def list_backups():
        return {"backups": []}

# Import support pack routes
# Import suppliers routes
try:
    from routes.suppliers import router as suppliers_router
except ImportError:
    # If suppliers routes are not available, create a dummy router
    from fastapi import APIRouter
    suppliers_router = APIRouter(prefix="/suppliers", tags=["suppliers"])
    
    @suppliers_router.get("")
    async def list_suppliers():
        return {"suppliers": []}

# Import delivery matching routes
try:
    from routes.delivery_matching import router as delivery_matching_router
except ImportError:
    # If delivery matching routes are not available, create a dummy router
    from fastapi import APIRouter
    delivery_matching_router = APIRouter(prefix="/matching", tags=["matching"])
    
    @delivery_matching_router.get("/candidates/{invoice_id}")
    async def get_match_candidates():
        return {"candidates": []}

# Import matching v2 routes
try:
    from routes.matching_v2 import router as matching_v2_router
except ImportError:
    # If matching v2 routes are not available, create a dummy router
    from fastapi import APIRouter
    matching_v2_router = APIRouter(prefix="/matching", tags=["matching-v2"])
    
    @matching_v2_router.get("/summary")
    async def get_matching_summary():
        return {"totals": {}, "pairs": []}

# Import flagged issues routes
try:
    from routes.flagged_issues import router as flagged_issues_router
except ImportError:
    # If flagged issues routes are not available, create a dummy router
    from fastapi import APIRouter
    flagged_issues_router = APIRouter(prefix="/flagged-issues", tags=["flagged-issues"])
    
    @flagged_issues_router.get("")
    async def get_flagged_issues():
        return {"flagged_issues": []}

# Import flagged issues bulk routes
try:
    from routes.flagged_issues_bulk import router as flagged_issues_bulk_router
except ImportError:
    # If flagged issues bulk routes are not available, create a dummy router
    from fastapi import APIRouter
    flagged_issues_bulk_router = APIRouter(prefix="/flagged-issues", tags=["flagged-issues-bulk"])
    
    @flagged_issues_bulk_router.post("/bulk-update")
    async def bulk_update_flagged_issues():
        return {"message": "Bulk actions not available"}

# Import supplier behaviour routes
try:
    from routes.supplier_behaviour import router as supplier_behaviour_router
except ImportError:
    # If supplier behaviour routes are not available, create a dummy router
    from fastapi import APIRouter
    supplier_behaviour_router = APIRouter(prefix="/supplier-behaviour", tags=["supplier-behaviour"])
    
    @supplier_behaviour_router.post("/event")
    async def create_supplier_event():
        return {"message": "Supplier behaviour tracking not available"}

try:
    from routes.support_packs import router as support_packs_router
except ImportError:
    # If support pack routes are not available, create a dummy router
    from fastapi import APIRouter
    support_packs_router = APIRouter(prefix="/support-packs", tags=["support-packs"])
    
    @support_packs_router.get("")
    async def list_support_packs():
        return {"support_packs": []}

# Import license routes
try:
    from routes.license import router as license_router
except ImportError as e:
    print(f"License routes import error: {e}")
    # If license routes are not available, create a dummy router
    from fastapi import APIRouter
    license_router = APIRouter(prefix="/license", tags=["license"])
    
    @license_router.get("/status")
    async def get_license_status():
        return {"message": "License system not available"}

# Import bulletproof ingestion system
try:
    from ingest.intake_router import IntakeRouter
    BULLETPROOF_INGESTION_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ Bulletproof ingestion system available")
except ImportError as e:
    BULLETPROOF_INGESTION_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️ Bulletproof ingestion system not available: {e}")

# Import recovery routes
try:
    from routes.recovery_new import router as recovery_router
except ImportError:
    # Create dummy router if import fails
    recovery_router = APIRouter(prefix="/recovery", tags=["recovery"])
    @recovery_router.get("/status")
    async def dummy_recovery_status():
        return {"error": "Recovery routes not available"}

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Optional OCR feature modules and flags
try:
    from ocr.signature_detector import SignatureDetector  # type: ignore
except Exception:
    SignatureDetector = None  # type: ignore
try:
    from ocr.confidence_calculator import ConfidenceCalculator  # type: ignore
except Exception:
    ConfidenceCalculator = None  # type: ignore
try:
    from ocr.receipt_processor import ReceiptProcessor  # type: ignore
except Exception:
    ReceiptProcessor = None  # type: ignore
try:
    from ocr.utility_processor import UtilityProcessor  # type: ignore
except Exception:
    UtilityProcessor = None  # type: ignore


def _read_ocr_flags() -> Dict[str, Any]:
    try:
        with open("data/config/ocr_flags.json", "r") as f:
            return json.load(f)
    except Exception:
        return {
            "signature_detection": True,
            "field_confidence": True,
            "per_line_confidence": True,
            "enable_receipt_mode": True,
            "enable_utility_mode": True,
        }

FLAGS = _read_ocr_flags()

app = FastAPI(title="Owlin API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include analytics routes
app.include_router(analytics_router, prefix="/api")

# Include document queue routes
app.include_router(document_queue_router, prefix="/api")

# Include updates routes
app.include_router(updates_router, prefix="/api")

# Include backup routes
app.include_router(backups_router, prefix="/api")

# Include support pack routes
# Include suppliers routes
app.include_router(suppliers_router, prefix="/api")
app.include_router(delivery_matching_router, prefix="/api")
app.include_router(matching_v2_router, prefix="/api")
app.include_router(support_packs_router, prefix="/api")

# Include license routes
app.include_router(license_router, prefix="/api")

# Include flagged issues routes
app.include_router(flagged_issues_router, prefix="/api")
app.include_router(flagged_issues_bulk_router, prefix="/api")

# Include supplier behaviour routes
app.include_router(supplier_behaviour_router, prefix="/api")

# Include recovery routes
app.include_router(recovery_router, prefix="/api")

# Create upload directory
upload_dir = Path("data/uploads")
upload_dir.mkdir(parents=True, exist_ok=True)

# Initialize bulletproof ingestion router if available
intake_router = None
if BULLETPROOF_INGESTION_AVAILABLE:
    try:
        intake_router = IntakeRouter()
        logger.info("✅ Bulletproof ingestion router initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize bulletproof ingestion router: {e}")
        BULLETPROOF_INGESTION_AVAILABLE = False

@app.get("/")
async def root():
    return {"message": "Owlin API is running"}

@app.get("/health")
async def health_check():
    return {"status": "ok", "bulletproof_ingestion": BULLETPROOF_INGESTION_AVAILABLE}

@app.get("/api/health")
def api_health_check():
    return {"status": "ok", "bulletproof_ingestion": BULLETPROOF_INGESTION_AVAILABLE}

# Real OCR processing function
async def process_file_with_real_ocr(file_path: Path, original_filename: str) -> Dict[str, Any]:
    """Process file with real OCR and extract invoice data"""
    try:
        logger.info(f"🔍 Starting real OCR processing for: {file_path}")
        
        # Import unified OCR engine
        try:
            from ocr.unified_ocr_engine import get_unified_ocr_engine
            from db_manager import save_invoice_to_db, save_uploaded_file_to_db
        except ImportError as import_error:
            logger.error(f"❌ Failed to import unified OCR modules: {import_error}")
            # Fallback to basic text processing
            return await process_file_with_basic_ocr(file_path, original_filename)
        
        # Process the file with unified engine
        logger.info(f"📄 Processing document with unified OCR: {file_path}")
        try:
            unified_engine = get_unified_ocr_engine()
            logger.info("✅ Got unified OCR engine")
            
            result = unified_engine.process_document(str(file_path))
            logger.info(f"📝 Unified OCR result: success={result.success}, confidence={result.overall_confidence}, supplier={result.supplier}, total={result.total_amount}")
            
            if result.success:
                logger.info(f"✅ OCR completed: {result.engine_used}, confidence: {result.overall_confidence:.2f}")
                
                # Clean the OCR text for better field extraction
                cleaned_text = clean_ocr_text(result.raw_text)
                logger.debug(f"📝 Raw OCR text: {result.raw_text[:200]}...")
                logger.debug(f"🧹 Cleaned text: {cleaned_text[:200]}...")
                
                # Use cleaned text for field extraction if needed
                all_text = cleaned_text
                word_count = result.word_count
                avg_confidence = result.overall_confidence
                line_items = result.line_items
                document_type = result.document_type

                # Optional: run signature detection per page if images are available
                signature_regions = []
                try:
                    if FLAGS.get("signature_detection") and SignatureDetector is not None:
                        images = await unified_engine.extract_images_from_file(str(file_path))
                        det = SignatureDetector()
                        for img in images:
                            signature_regions.extend(det.detect(img))
                except Exception:
                    signature_regions = []
                
                # Ensure confidence is properly normalized (0-100 for UI)
                if avg_confidence <= 1.0:
                    ui_confidence = max(30.0, min(95.0, avg_confidence * 100.0))  # Minimum 30%, max 95%
                else:
                    ui_confidence = max(30.0, min(95.0, avg_confidence))  # Already in 0-100 range
                
                # Create extracted_data dict for compatibility
                extracted_data = {
                    "supplier_name": result.supplier,
                    "invoice_number": result.invoice_number,
                    "invoice_date": result.date,
                    "total_amount": result.total_amount,
                    "line_items": line_items,
                }

                # Field & line confidences
                field_confidence = None
                overall_confidence = avg_confidence
                if FLAGS.get("field_confidence") and ConfidenceCalculator is not None:
                    calc = ConfidenceCalculator()
                    ocr_signals = {"avg_confidence": float(avg_confidence) if avg_confidence is not None else 0.6}
                    field_confidence = calc.field_confidences(extracted_data, ocr_signals)
                    if FLAGS.get("per_line_confidence") and isinstance(line_items, list):
                        line_items = calc.line_item_confidences(line_items)
                    overall_confidence = calc.overall(field_confidence or {}, line_items or [])
                
                logger.info(f"📊 Unified OCR completed: {word_count} words, {ui_confidence:.2f} confidence, engine: {result.engine_used}")
            else:
                logger.error(f"❌ Unified OCR failed: {result.error_message}")
                # Fallback to basic text processing
                return await process_file_with_basic_ocr(file_path, original_filename)
            
        except Exception as e:
            logger.error(f"❌ Unified OCR import/processing failed: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            # Fallback to basic text processing
            return await process_file_with_basic_ocr(file_path, original_filename)
        
        # Save to database
        file_id = str(uuid.uuid4())
        try:
            # Save uploaded file record
            save_uploaded_file_to_db(
                file_id=file_id,
                original_filename=original_filename,
                file_path=str(file_path),
                file_type=document_type,
                confidence=avg_confidence
            )
            
            # Save invoice data if it's an invoice
            if document_type == "invoice":
                logger.info(f"💾 Attempting to save invoice to database: {file_id}")
                logger.info(f"💾 Document type: {document_type}")
                logger.info(f"💾 Supplier: {extracted_data['supplier_name']}")
                logger.info(f"💾 Invoice number: {extracted_data['invoice_number']}")
                try:
                    # Check if this was LLM processing
                    _field_conf_for_db = field_confidence if field_confidence else None
                    raw_extraction = None
                    warnings = []
                    result_save = save_invoice_to_db(
                        invoice_id=file_id,
                        supplier_name=extracted_data["supplier_name"],
                        invoice_number=extracted_data["invoice_number"],
                        invoice_date=extracted_data["invoice_date"],
                        total_amount=extracted_data["total_amount"],
                        confidence=avg_confidence,
                        ocr_text=all_text,
                        line_items=line_items,
                        field_confidence=_field_conf_for_db,
                        raw_extraction=raw_extraction,
                        warnings=warnings,
                        addresses={},
                        signature_regions=signature_regions,
                    )
                    logger.info(f"✅ Invoice save result: {result_save}")
                except Exception as db_error:
                    logger.error(f"❌ Database save failed: {db_error}")
                    import traceback
                    logger.error(f"❌ Database save traceback: {traceback.format_exc()}")
        except Exception as db_error:
            logger.error(f"❌ Database save failed: {db_error}")
        
        return {
            "confidence": ui_confidence,
            "supplier_name": extracted_data["supplier_name"],
            "invoice_number": extracted_data["invoice_number"],
            "total_amount": extracted_data["total_amount"],
            "invoice_date": extracted_data["invoice_date"],
            "raw_text": all_text[:1000] + "..." if len(all_text) > 1000 else all_text,
            "word_count": word_count,
            "line_items": [item.__dict__ if hasattr(item, '__dict__') else item for item in line_items[:10]],  # Limit to first 10 items
            "document_type": document_type,
            "file_id": file_id,
            "engine_used": result.engine_used,
            "signature_regions": signature_regions,
            "field_confidence": field_confidence or {},
            "overall_confidence": overall_confidence,
        }
        
    except Exception as e:
        logger.error(f"❌ Real OCR processing failed: {e}")
        # Final fallback to basic processing
        return await process_file_with_basic_ocr(file_path, original_filename)

async def process_file_with_basic_ocr(file_path: Path, original_filename: str) -> Dict[str, Any]:
    """Basic OCR processing as fallback"""
    try:
        logger.info(f"🔄 Using basic OCR processing for: {file_path}")
        
        file_extension = file_path.suffix.lower()
        
        # Handle text files
        if file_extension in {'.txt', '.md'}:
            logger.info("📝 Processing as text file")
            with open(file_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
            
            extracted_data = extract_invoice_data_from_text(text_content)
            document_type = classify_document_type(text_content)
            
            logger.info(f"📄 Basic OCR - Document type: {document_type}")
            logger.info(f"📄 Basic OCR - Supplier: {extracted_data['supplier_name']}")
            
            return {
                "confidence": 85.0,  # High confidence for text files (0-100 scale)
                "supplier_name": extracted_data["supplier_name"],
                "invoice_number": extracted_data["invoice_number"],
                "total_amount": extracted_data["total_amount"],
                "invoice_date": extracted_data["invoice_date"],
                "raw_text": text_content[:1000] + "..." if len(text_content) > 1000 else text_content,
                "word_count": len(text_content.split()),
                "line_items": [],
                "document_type": document_type,
                "file_id": str(uuid.uuid4())
            }
        
        # Handle image files with basic Tesseract
        elif file_extension in {'.jpg', '.jpeg', '.png', '.tiff', '.tif'}:
            try:
                import pytesseract
                from PIL import Image
                
                image = Image.open(file_path)
                text_content = pytesseract.image_to_string(image)
                
                if text_content.strip():
                    extracted_data = extract_invoice_data_from_text(text_content)
                    document_type = classify_document_type(text_content)
                    
                    return {
                        "confidence": 75.0,  # Medium confidence for image OCR (0-100 scale)
                        "supplier_name": extracted_data["supplier_name"],
                        "invoice_number": extracted_data["invoice_number"],
                        "total_amount": extracted_data["total_amount"],
                        "invoice_date": extracted_data["invoice_date"],
                        "raw_text": text_content[:1000] + "..." if len(text_content) > 1000 else text_content,
                        "word_count": len(text_content.split()),
                        "line_items": [],
                        "document_type": document_type,
                        "file_id": str(uuid.uuid4())
                    }
                else:
                    # No text extracted from image
                    return {
                        "confidence": 30.0,  # Low confidence for no text extracted (0-100 scale)
                        "supplier_name": "No text extracted",
                        "invoice_number": "Unknown",
                        "total_amount": 0.0,
                        "invoice_date": datetime.now().strftime("%Y-%m-%d"),
                        "raw_text": "No text could be extracted from this image",
                        "word_count": 0,
                        "line_items": [],
                        "document_type": "unknown",
                        "file_id": str(uuid.uuid4())
                    }
                    
            except Exception as img_error:
                logger.error(f"❌ Basic image OCR failed: {img_error}")
                return {
                    "confidence": 30.0,  # Low confidence for processing failure (0-100 scale)
                    "supplier_name": "Image processing failed",
                    "invoice_number": "Unknown",
                    "total_amount": 0.0,
                    "invoice_date": datetime.now().strftime("%Y-%m-%d"),
                    "raw_text": f"Image processing error: {str(img_error)}",
                    "word_count": 0,
                    "line_items": [],
                    "document_type": "unknown",
                    "file_id": str(uuid.uuid4())
                }
        
        # Handle PDF files
        elif file_extension == '.pdf':
            try:
                import fitz  # PyMuPDF
                
                doc = fitz.open(file_path)
                text_content = ""
                
                # Extract text from all pages
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    text_content += page.get_text()
                
                doc.close()
                
                if text_content.strip():
                    logger.info(f"📄 PDF text extraction successful: {len(text_content)} characters")
                    
                    # Check for multiple invoices
                    invoice_indicators = text_content.lower().count('invoice')
                    if invoice_indicators > 1:
                        logger.info(f"📄 Multiple invoices detected: {invoice_indicators} invoice indicators")
                        # For now, process as single invoice but flag for future multi-invoice handling
                        extracted_data = extract_invoice_data_from_text(text_content)
                        document_type = classify_document_type(text_content)
                        
                        # Calculate confidence based on data extraction success
                        word_count = len(text_content.split())
                        base_confidence = min(0.95, max(0.3, word_count / 50))
                        
                        # Boost confidence if key data was extracted
                        confidence_boost = 0.0
                        if extracted_data["supplier_name"] != "Unknown Supplier":
                            confidence_boost += 0.2
                        if extracted_data["invoice_number"] != "Unknown":
                            confidence_boost += 0.2
                        if extracted_data["total_amount"] > 0:
                            confidence_boost += 0.2
                        if extracted_data["invoice_date"] != datetime.now().strftime("%Y-%m-%d"):
                            confidence_boost += 0.1
                        
                        final_confidence = min(0.95, base_confidence + confidence_boost)
                        
                        return {
                            "confidence": final_confidence,
                            "supplier_name": extracted_data["supplier_name"],
                            "invoice_number": extracted_data["invoice_number"],
                            "total_amount": extracted_data["total_amount"],
                            "invoice_date": extracted_data["invoice_date"],
                            "raw_text": text_content[:1000] + "..." if len(text_content) > 1000 else text_content,
                            "word_count": word_count,
                            "line_items": [],
                            "document_type": document_type,
                            "file_id": str(uuid.uuid4()),
                            "multi_invoice": True,
                            "invoice_count": invoice_indicators
                        }
                    else:
                        # Single invoice processing
                        extracted_data = extract_invoice_data_from_text(text_content)
                        document_type = classify_document_type(text_content)
                        
                        # Extract line items
                        line_items = []
                        try:
                            # Enhanced line item extraction from text
                            lines = text_content.split('\n')
                            for line in lines:
                                # Look for specific patterns like "2 BUCK-EK30 Buckskin - 30L E-keg £98.50"
                                if re.search(r'(\d+)\s+([A-Z0-9\-]+)\s+(.*?)\s+[£$€](\d+\.?\d*)', line, re.IGNORECASE):
                                    match = re.search(r'(\d+)\s+([A-Z0-9\-]+)\s+(.*?)\s+[£$€](\d+\.?\d*)', line, re.IGNORECASE)
                                    if match:
                                        try:
                                            qty = int(match.group(1))
                                            code = match.group(2)
                                            description = match.group(3).strip()
                                            unit_price = float(match.group(4))
                                            
                                            line_items.append({
                                                "quantity": qty,
                                                "code": code,
                                                "description": description,
                                                "unit_price": unit_price,
                                                "total_price": qty * unit_price
                                            })
                                        except:
                                            continue
                                
                                # Also look for simpler patterns like "2 BUCK-EK30 £98.50"
                                elif re.search(r'(\d+)\s+([A-Z0-9\-]+)\s+[£$€](\d+\.?\d*)', line, re.IGNORECASE):
                                    match = re.search(r'(\d+)\s+([A-Z0-9\-]+)\s+[£$€](\d+\.?\d*)', line, re.IGNORECASE)
                                    if match:
                                        try:
                                            qty = int(match.group(1))
                                            code = match.group(2)
                                            unit_price = float(match.group(3))
                                            
                                            line_items.append({
                                                "quantity": qty,
                                                "code": code,
                                                "description": f"Item {code}",
                                                "unit_price": unit_price,
                                                "total_price": qty * unit_price
                                            })
                                        except:
                                            continue
                                
                                # Look for patterns like "QTY CODE ITEM UNIT PRICE" or "2 BUCK-EK30 Buckskin - 30L E-keg £98.50"
                                elif re.search(r'\d+\s+[A-Z]+\s+[A-Z\s\-]+\s+[£$€]?\d+', line, re.IGNORECASE):
                                    parts = line.split()
                                    if len(parts) >= 4:
                                        try:
                                            qty = int(parts[0])
                                            code = parts[1]
                                            # Look for price at end of line
                                            price_match = re.search(r'[£$€]?(\d+\.?\d*)', line)
                                            if price_match:
                                                unit_price = float(price_match.group(1))
                                                # Extract description between code and price
                                                price_start = line.find(price_match.group(0))
                                                description = line[len(parts[0]) + len(parts[1]) + 2:price_start].strip()
                                                
                                                line_items.append({
                                                    "quantity": qty,
                                                    "code": code,
                                                    "description": description,
                                                    "unit_price": unit_price,
                                                    "total_price": qty * unit_price
                                                })
                                        except:
                                            continue
                        except Exception as line_error:
                            logger.error(f"❌ Line item extraction failed: {line_error}")
                        
                        # Calculate confidence based on data extraction success
                        word_count = len(text_content.split())
                        base_confidence = max(0.3, min(0.95, word_count / 30))  # Minimum 30%, more generous calculation
                        
                        # Boost confidence if key data was extracted
                        confidence_boost = 0.0
                        if extracted_data["supplier_name"] != "Unknown Supplier":
                            confidence_boost += 0.3
                        if extracted_data["invoice_number"] != "Unknown":
                            confidence_boost += 0.2
                        if extracted_data["total_amount"] > 0:
                            confidence_boost += 0.2
                        if extracted_data["invoice_date"] != datetime.now().strftime("%Y-%m-%d"):
                            confidence_boost += 0.1
                        if line_items:
                            confidence_boost += 0.2  # Bonus for line items
                        
                        final_confidence = min(0.95, base_confidence + confidence_boost)
                        # Ensure minimum confidence of 30%
                        final_confidence = max(0.3, final_confidence)
                        
                        # If we have good data but low confidence, boost it
                        if (extracted_data["supplier_name"] != "Unknown Supplier" and 
                            extracted_data["total_amount"] > 0 and 
                            final_confidence < 0.5):
                            final_confidence = 0.7  # Boost to reasonable confidence
                        
                        return {
                            "confidence": final_confidence,
                            "supplier_name": extracted_data["supplier_name"],
                            "invoice_number": extracted_data["invoice_number"],
                            "total_amount": extracted_data["total_amount"],
                            "invoice_date": extracted_data["invoice_date"],
                            "raw_text": text_content[:1000] + "..." if len(text_content) > 1000 else text_content,
                            "word_count": word_count,
                            "line_items": line_items,
                            "document_type": document_type,
                            "file_id": str(uuid.uuid4())
                        }
                else:
                    # Try OCR on PDF pages if text extraction fails
                    logger.info("📄 No text extracted from PDF, trying OCR on pages")
                    try:
                        from pdf2image import convert_from_path
                        images = convert_from_path(file_path)
                        
                        ocr_text = ""
                        for i, image in enumerate(images):
                            try:
                                import pytesseract
                                page_text = pytesseract.image_to_string(image)
                                ocr_text += f"Page {i+1}:\n{page_text}\n"
                            except Exception as ocr_error:
                                logger.error(f"❌ OCR failed on page {i+1}: {ocr_error}")
                        
                        if ocr_text.strip():
                            extracted_data = extract_invoice_data_from_text(ocr_text)
                            document_type = classify_document_type(ocr_text)
                            
                            return {
                                "confidence": 0.6,  # Medium confidence for OCR on PDF
                                "supplier_name": extracted_data["supplier_name"],
                                "invoice_number": extracted_data["invoice_number"],
                                "total_amount": extracted_data["total_amount"],
                                "invoice_date": extracted_data["invoice_date"],
                                "raw_text": ocr_text[:1000] + "..." if len(ocr_text) > 1000 else ocr_text,
                                "word_count": len(ocr_text.split()),
                                "line_items": [],
                                "document_type": document_type,
                                "file_id": str(uuid.uuid4())
                            }
                        else:
                            return {
                                "confidence": 0.3,
                                "supplier_name": "No text extracted from PDF",
                                "invoice_number": "Unknown",
                                "total_amount": 0.0,
                                "invoice_date": datetime.now().strftime("%Y-%m-%d"),
                                "raw_text": "No text could be extracted from this PDF",
                                "word_count": 0,
                                "line_items": [],
                                "document_type": "unknown",
                                "file_id": str(uuid.uuid4())
                            }
                    except Exception as pdf_ocr_error:
                        logger.error(f"❌ PDF OCR failed: {pdf_ocr_error}")
                        return {
                            "confidence": 0.3,
                            "supplier_name": "PDF processing failed",
                            "invoice_number": "Unknown",
                            "total_amount": 0.0,
                            "invoice_date": datetime.now().strftime("%Y-%m-%d"),
                            "raw_text": f"PDF processing error: {str(pdf_ocr_error)}",
                            "word_count": 0,
                            "line_items": [],
                            "document_type": "unknown",
                            "file_id": str(uuid.uuid4())
                        }
                    
            except Exception as pdf_error:
                logger.error(f"❌ Basic PDF processing failed: {pdf_error}")
                return {
                    "confidence": 0.3,
                    "supplier_name": "PDF processing failed",
                    "invoice_number": "Unknown",
                    "total_amount": 0.0,
                    "invoice_date": datetime.now().strftime("%Y-%m-%d"),
                    "raw_text": f"PDF processing error: {str(pdf_error)}",
                    "word_count": 0,
                    "line_items": [],
                    "document_type": "unknown",
                    "file_id": str(uuid.uuid4())
                }
        
        # Unknown file type
        else:
            return {
                "confidence": 0.3,
                "supplier_name": "Unsupported file type",
                "invoice_number": "Unknown",
                "total_amount": 0.0,
                "invoice_date": datetime.now().strftime("%Y-%m-%d"),
                "raw_text": f"Unsupported file type: {file_extension}",
                "word_count": 0,
                "line_items": [],
                "document_type": "unknown",
                "file_id": str(uuid.uuid4())
            }
            
    except Exception as e:
        logger.error(f"❌ Basic OCR processing failed: {e}")
        return {
            "confidence": 0.3,
            "supplier_name": "Processing failed",
            "invoice_number": "Unknown",
            "total_amount": 0.0,
            "invoice_date": datetime.now().strftime("%Y-%m-%d"),
            "raw_text": f"Processing error: {str(e)}",
            "word_count": 0,
            "line_items": [],
            "document_type": "unknown",
            "file_id": str(uuid.uuid4())
        }

def extract_invoice_data_from_text(text: str) -> Dict[str, Any]:
    """Simplified and reliable invoice data extraction"""
    import re
    from datetime import datetime
    
    # Clean the text first
    text = text.strip()
    lines = text.split('\n')
    
    # Initialize results
    supplier_name = "Unknown Supplier"
    invoice_number = "Unknown"
    total_amount = 0.0
    invoice_date = datetime.now().strftime("%Y-%m-%d")
    
    # STEP 1: SUPPLIER EXTRACTION (Simplified)
    # Look for the first line that looks like a company name
    for line in lines[:10]:  # Check first 10 lines
        line = line.strip()
        if len(line) > 5 and len(line) < 100:  # Reasonable length
            # Skip common invoice words
            if any(word in line.lower() for word in ['invoice', 'bill to', 'deliver to', 'date:', 'total:', 'qty', 'code', 'item', 'unit', 'price']):
                continue
            # Skip if it's just numbers or special characters
            if re.match(r'^[\d\s\-\.]+$', line):
                continue
            # Skip if it starts with common invoice prefixes
            if line.lower().startswith(('invoice', 'bill', 'deliver', 'date', 'total')):
                continue
            # This looks like a supplier name
            supplier_name = line
            break
    
    # STEP 2: INVOICE NUMBER EXTRACTION (Simplified)
    # Look for "Invoice #" or "Invoice Number" patterns
    invoice_patterns = [
        r'invoice\s*#?\s*:?\s*(\d+)',
        r'invoice\s*number\s*:?\s*(\d+)',
        r'#\s*(\d{3,})',  # 3+ digit numbers after #
    ]
    
    for pattern in invoice_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            invoice_number = match.group(1)
            break
    
    # STEP 3: TOTAL EXTRACTION (Simplified)
    # Look for "Total:" followed by amount
    total_patterns = [
        r'total\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)',
        r'total\s*\(inc\.?\s*vat\)\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)',
        r'total\s*due\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)',
    ]
    
    for pattern in total_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                amount_str = match.group(1).replace(',', '')
                amount = float(amount_str)
                if amount > 0 and amount < 1000000:  # Reasonable range
                    total_amount = amount
                    break
            except:
                continue
    
    # STEP 4: DATE EXTRACTION (Simplified)
    # Look for date patterns
    date_patterns = [
        r'date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'invoice\s*date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # General date pattern
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                date_str = match.group(1)
                if '/' in date_str:
                    parsed_date = datetime.strptime(date_str, "%d/%m/%Y")
                    invoice_date = parsed_date.strftime("%Y-%m-%d")
                    break
            except:
                continue
    
    return {
        "supplier_name": supplier_name,
        "invoice_number": invoice_number,
        "total_amount": total_amount,
        "invoice_date": invoice_date
    }


def clean_ocr_text(text: str) -> str:
    """Clean OCR text for better field extraction"""
    import re
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove common OCR artifacts
    text = re.sub(r'[^\w\s\-\.\,\£\$€\#\@\:\(\)]', '', text)
    
    # Fix common OCR errors
    text = text.replace('OICE', 'INVOICE')
    text = text.replace('lNVOICE', 'INVOICE')
    text = text.replace('lnvoice', 'Invoice')
    text = text.replace('lnvoice #', 'Invoice #')
    
    # Clean up currency symbols
    text = re.sub(r'[£$€]\s*', '£', text)  # Standardize to £
    
    return text.strip()

def classify_document_type(text: str) -> str:
    """Classify document type based on content"""
    text_lower = text.lower()
    
    # Check for delivery note indicators
    delivery_indicators = ['delivery note', 'delivery receipt', 'goods received', 'delivery']
    if any(indicator in text_lower for indicator in delivery_indicators):
        return "delivery_note"
    
    # Check for utility bill indicators
    utility_indicators = ['utility', 'electricity', 'gas', 'water', 'phone', 'internet', 'council tax']
    if any(indicator in text_lower for indicator in utility_indicators):
        return "utility"
    
    # Check for invoice indicators
    invoice_indicators = ['invoice', 'bill', 'statement', 'account']
    if any(indicator in text_lower for indicator in invoice_indicators):
        return "invoice"
    
    # Default to invoice if no clear classification
    return "invoice"

# Import the new unified multi-invoice detection system
try:
    from ocr.multi_invoice_detector import get_multi_invoice_detector, DetectionConfig, DetectionResult
    UNIFIED_DETECTION_AVAILABLE = True
    logger.info("✅ Unified multi-invoice detection system loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Unified multi-invoice detection not available: {e}")
    UNIFIED_DETECTION_AVAILABLE = False

# Legacy function for backward compatibility (will be deprecated)
def is_actual_multi_invoice(text: str) -> bool:
    """
    Improved multi-invoice detection that's more conservative.
    Only detects multi-invoice when there are clearly multiple distinct invoices.
    """
    text_lower = text.lower()
    
    # Count unique invoice numbers
    invoice_patterns = [
        r'invoice\s*#?\s*:?\s*([^\n\s]+)',
        r'#\s*(\d+)',
        r'invoice\s*(\d+)',
    ]
    
    unique_invoices = set()
    for pattern in invoice_patterns:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            if match.strip() and len(match.strip()) >= 3:
                unique_invoices.add(match.strip())
    
    # Count unique suppliers
    supplier_patterns = [
        r'([A-Z][A-Z\s&]+(?:BREWING|BREWERY|CO|COMPANY|LTD|LIMITED|INC|CORP|LLC))',
        r'([A-Z][A-Z\s&]+(?:CO\.|COMPANY|LTD\.|LIMITED))',
        r'([A-Z][A-Z\s&]+(?:BREWING|BREWERY))',
    ]
    
    unique_suppliers = set()
    for pattern in supplier_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if match.strip() and len(match.strip()) > 5:
                unique_suppliers.add(match.strip())
    
    # Count page separators
    page_markers = re.findall(r'(?:page|p\.?)\s*\d+', text_lower)
    
    # More conservative detection criteria
    has_multiple_invoices = len(unique_invoices) > 1
    has_page_separators = len(page_markers) > 1  # Require more than 1 page marker
    has_multiple_suppliers = len(unique_suppliers) > 1
    
    # Additional validation: require stronger evidence
    if has_multiple_invoices:
        # Make sure the invoice numbers are actually different (not just variations)
        invoice_numbers = list(unique_invoices)
        for i, inv1 in enumerate(invoice_numbers):
            for inv2 in invoice_numbers[i+1:]:
                # Check if they're similar (might be variations of the same number)
                if inv1.lower() in inv2.lower() or inv2.lower() in inv1.lower():
                    has_multiple_invoices = False
                    break
    
    # Only return True if we have strong evidence of multiple invoices
    # Require at least 2 of the 3 conditions to be true
    conditions_met = sum([has_multiple_invoices, has_page_separators, has_multiple_suppliers])
    
    return conditions_met >= 2

# Upload endpoint that frontend expects
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check file type
        allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.txt', '.md'}
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(status_code=400, detail="File type not supported. Please upload PDF, JPG, JPEG, PNG, TIFF, TXT, or MD files.")
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = Path(file.filename).suffix
        filename = f"{file_id}_{timestamp}{extension}"
        file_path = upload_dir / filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"📁 File saved: {file_path}")
        
        # Process file based on type
        if file_extension in {'.txt', '.md'}:
            # Process text files directly
            logger.info("📝 Processing as text file")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
                extracted_data = extract_invoice_data_from_text(text_content)
                ocr_data = {
                    "confidence": 85,
                    "supplier_name": extracted_data["supplier_name"],
                    "invoice_number": extracted_data["invoice_number"],
                    "total_amount": extracted_data["total_amount"],
                    "invoice_date": extracted_data["invoice_date"],
                    "raw_text": text_content[:1000] + "..." if len(text_content) > 1000 else text_content,
                    "word_count": len(text_content.split()),
                    "line_items": [],
                    "document_type": classify_document_type(text_content),
                    "file_id": file_id,
                    "engine_used": "text_processing",
                    "processing_time": 0.0
                }
                logger.info(f"✅ Text processing completed: {extracted_data['supplier_name']}, {extracted_data['total_amount']}")
            except Exception as text_error:
                logger.error(f"❌ Text processing failed: {text_error}")
                # Fallback data
                ocr_data = {
                    "confidence": 30.0,
                    "supplier_name": "Text processing failed",
                    "invoice_number": "Unknown",
                    "total_amount": 0.0,
                    "invoice_date": datetime.now().strftime("%Y-%m-%d"),
                    "raw_text": f"Text processing failed: {str(text_error)}",
                    "word_count": 0,
                    "line_items": [],
                    "document_type": "unknown",
                    "file_id": file_id,
                    "engine_used": "fallback",
                    "processing_time": 0.0
                }
        else:
            # Process image/PDF files with OCR
            try:
                ocr_data = await process_file_with_real_ocr(file_path, file.filename)
            except Exception as ocr_error:
                logger.error(f"❌ OCR processing failed: {ocr_error}")
                
                # Provide fallback data instead of crashing
                logger.info("🔄 Providing fallback data for failed OCR processing")
                ocr_data = {
                    "confidence": 30.0,
                    "supplier_name": "Processing failed",
                    "invoice_number": "Unknown",
                    "total_amount": 0.0,
                    "invoice_date": datetime.now().strftime("%Y-%m-%d"),
                    "raw_text": f"OCR processing failed: {str(ocr_error)}",
                    "word_count": 0,
                    "line_items": [],
                    "document_type": "unknown",
                    "file_id": file_id,
                    "engine_used": "fallback",
                    "processing_time": 0.0
                }
        
        # Check for multi-invoice content using unified detection system
        multi_invoice_detected = False
        detection_result = None
        
        if file_extension in {'.pdf', '.txt', '.md'}:
            try:
                # Get the raw text for analysis
                raw_text = ocr_data.get("raw_text", "")
                logger.info(f"🔍 Analyzing text for multi-invoice detection (length: {len(raw_text)} chars)")
                
                if UNIFIED_DETECTION_AVAILABLE:
                    # Use the new unified multi-invoice detection system
                    logger.info("🔄 Using unified multi-invoice detection system")
                    detector = get_multi_invoice_detector()
                    detection_result = detector.detect(raw_text)
                    multi_invoice_detected = detection_result.is_multi_invoice
                    
                    logger.info(f"🔍 Unified detection result: multi_invoice={multi_invoice_detected}, confidence={detection_result.confidence:.2f}")
                    logger.info(f"🔍 Detected invoices: {len(detection_result.detected_invoices)}")
                    logger.info(f"🔍 Page separations: {len(detection_result.page_separations)}")
                    logger.info(f"🔍 Supplier variations: {len(detection_result.supplier_variations)}")
                    
                    if detection_result.warnings:
                        logger.warning(f"⚠️ Detection warnings: {detection_result.warnings}")
                    
                    if detection_result.error_messages:
                        logger.error(f"❌ Detection errors: {detection_result.error_messages}")
                else:
                    # Fallback to legacy detection
                    logger.info("🔄 Using legacy multi-invoice detection")
                    multi_invoice_detected = is_actual_multi_invoice(raw_text)
                    
                # Additional validation: only treat as multi-invoice if we have strong evidence
                if multi_invoice_detected:
                    logger.info("🔍 Multi-invoice detected, performing additional validation...")
                    
                    # Count unique invoice numbers in the text using conservative patterns
                    invoice_patterns = [
                        r"\b(?:invoice|inv)\s*(?:no\.?|number|#)?\s*[:\-]?\s*([A-Za-z0-9\-]{3,})",
                        r"\binvoice\s*#\s*([A-Za-z0-9\-]{3,})",
                    ]
                    
                    unique_invoices = set()
                    for pattern in invoice_patterns:
                        matches = re.findall(pattern, raw_text, flags=re.IGNORECASE)
                        for match in matches:
                            cleaned = match.strip()
                            if cleaned and len(cleaned) >= 3:
                                unique_invoices.add(cleaned)
                    
                    logger.info(f"🔍 Found {len(unique_invoices)} unique invoice numbers: {unique_invoices}")
                    
                    # Only proceed if we have at least 1 distinct invoice number (changed from 2)
                    if len(unique_invoices) < 1:
                        logger.info(f"⚠️ Multi-invoice detection overridden: only {len(unique_invoices)} explicit invoice numbers found")
                        multi_invoice_detected = False
                    
                    # Additional check: if this is a single-page document, be extra conservative
                    if detection_result and detection_result.context_analysis and detection_result.context_analysis.page_count <= 1:
                        logger.info(f"⚠️ Single-page document detected ({detection_result.context_analysis.page_count} pages), forcing single-invoice mode")
                        multi_invoice_detected = False
                    
                    # Final check: if we have less than 50 words, it's probably a single invoice (changed from 100)
                    if len(raw_text.split()) < 50:
                        logger.info(f"⚠️ Document too short ({len(raw_text.split())} words), forcing single-invoice mode")
                        multi_invoice_detected = False
                    
                    # Final validation: if we still think it's multi-invoice, log the decision
                    if multi_invoice_detected:
                        logger.info("✅ Multi-invoice detection confirmed after validation")
                        
                        # Handle multi-invoice processing
                        if detection_result and detection_result.detected_invoices:
                            # Use unified detection results
                            invoices = []
                            try:
                                from db_manager import save_invoice_to_db
                            except Exception as e:
                                logger.error(f"❌ Could not import save_invoice_to_db: {e}")
                                save_invoice_to_db = None
                            for i, detected_invoice in enumerate(detection_result.detected_invoices):
                                invoice_id = str(uuid.uuid4())
                                # Extract data for this invoice
                                part_text = detected_invoice.get('context', '')
                                part_extracted = extract_invoice_data_from_text(part_text)
                                # Normalize confidence to 0-100 for UI, but store raw 0-1 in DB
                                det_conf = detection_result.confidence or 0.0
                                raw_conf_0_1 = det_conf if det_conf <= 1.0 else min(1.0, det_conf / 100.0)
                                ui_conf_0_100 = min(100.0, max(30.0, raw_conf_0_1 * 100.0))  # Minimum 30% confidence
                                # Persist to DB if possible
                                if save_invoice_to_db:
                                    try:
                                        save_invoice_to_db(
                                            invoice_id=invoice_id,
                                            supplier_name=part_extracted.get("supplier_name", "Unknown Supplier"),
                                            invoice_number=detected_invoice.get('invoice_number', f"INV-{i+1:03d}"),
                                            invoice_date=part_extracted.get("invoice_date", datetime.now().strftime("%Y-%m-%d")),
                                            total_amount=part_extracted.get("total_amount", 0.0),
                                            confidence=raw_conf_0_1,  # store 0-1 internally
                                            ocr_text=part_text,
                                            line_items=[]
                                        )
                                    except Exception as db_err:
                                        logger.error(f"❌ Failed saving sub-invoice: {db_err}")
                                invoices.append({
                                    "invoice_id": invoice_id,
                                    "supplier_name": part_extracted.get("supplier_name", "Unknown Supplier"),
                                    "invoice_number": detected_invoice.get('invoice_number', f"INV-{i+1:03d}"),
                                    "invoice_date": part_extracted.get("invoice_date", datetime.now().strftime("%Y-%m-%d")),
                                    "total_amount": part_extracted.get("total_amount", 0.0),
                                    "confidence": ui_conf_0_100,
                                    "page_range": detected_invoice.get('page_range', f"Page {i+1}"),
                                    "invoice_text": part_text,
                                    "page_numbers": detected_invoice.get('page_numbers', [i+1]),
                                    "metadata": {
                                        "supplier_name": part_extracted.get("supplier_name", "Unknown Supplier"),
                                        "invoice_number": detected_invoice.get('invoice_number', f"INV-{i+1:03d}"),
                                        "invoice_date": part_extracted.get("invoice_date", datetime.now().strftime("%Y-%m-%d")),
                                        "total_amount": part_extracted.get("total_amount", 0.0),
                                        "confidence": ui_conf_0_100
                                    },
                                    "line_items": []
                                })
                            if invoices and len(invoices) >= 1:  # Changed from 2 to 1
                                logger.info(f"✅ Returning {len(invoices)} multi-invoice results")
                                return {
                                    "message": f"Multi-invoice document processed successfully using unified detection",
                                    "data": {
                                        "saved_invoices": invoices,
                                        "total_invoices": len(invoices)
                                    },
                                    "saved_invoices": invoices,
                                    "total_invoices": len(invoices),
                                    "original_filename": file.filename,
                                    "detection_confidence": detection_result.confidence if detection_result else 0.0
                                }
                            else:
                                logger.info("⚠️ Only one valid sub-invoice extracted; treating as single invoice")
                                multi_invoice_detected = False
                        else:
                            logger.info("⚠️ Multi-invoice detection overridden by validation checks")
                
            except Exception as e:
                logger.error(f"❌ Multi-invoice detection failed: {e}")
                multi_invoice_detected = False
        
        # Save to database regardless of OCR method used
        try:
            from db_manager import save_invoice_to_db, save_uploaded_file_to_db
            
            # Save uploaded file record
            save_uploaded_file_to_db(
                file_id=file_id,
                original_filename=file.filename,
                file_path=str(file_path),
                file_type=ocr_data["document_type"],
                confidence=ocr_data["confidence"]
            )
            
            # Save invoice data if it's an invoice
            if ocr_data["document_type"] == "invoice":
                logger.info(f"💾 Upload endpoint - Saving invoice to database: {file_id}")
                save_invoice_to_db(
                    invoice_id=file_id,
                    supplier_name=ocr_data["supplier_name"],
                    invoice_number=ocr_data["invoice_number"],
                    invoice_date=ocr_data["invoice_date"],
                    total_amount=ocr_data["total_amount"],
                    confidence=ocr_data["confidence"],
                    ocr_text=ocr_data["raw_text"],
                    line_items=ocr_data["line_items"]
                )
                logger.info(f"✅ Upload endpoint - Invoice saved to database: {file_id}")
        except Exception as db_error:
            logger.error(f"❌ Upload endpoint - Database save failed: {db_error}")
        
        # Return processed invoice data with CORRECT STRUCTURE for frontend
        # Normalize confidence to 0-1 range for frontend
        confidence_raw = ocr_data.get("confidence", 0.0)
        
        # Handle different confidence formats and ensure proper normalization
        if isinstance(confidence_raw, (int, float)):
            if confidence_raw > 1.0:
                # If confidence is already a percentage, keep in 0-100 for UI layer
                confidence_normalized = min(100.0, float(confidence_raw))
            else:
                # Convert 0-1 to 0-100 for UI layer
                confidence_normalized = min(100.0, max(30.0, float(confidence_raw) * 100.0))
        else:
            # Fallback for string or invalid values
            try:
                val = float(confidence_raw)
                confidence_normalized = val if val > 1.0 else val * 100.0
            except (ValueError, TypeError):
                confidence_normalized = 30.0  # Default minimum confidence in percent
        
        # Ensure confidence is never 0% or > 100%
        confidence_normalized = max(30.0, min(95.0, confidence_normalized))
        
        logger.info(f"🔍 Confidence calculation: raw={confidence_raw}, normalized%={confidence_normalized:.1f}")
        
        # ✅ FINAL CHECK: Ensure we never return multi-invoice for single invoices
        if multi_invoice_detected:
            logger.warning("⚠️ Multi-invoice detection was triggered but validation failed - forcing single invoice mode")
            multi_invoice_detected = False
        
        logger.info(f"✅ Final result: single invoice mode, confidence={confidence_normalized:.1f}%")
        
        return {
            "success": True,
            "message": "Invoice processed successfully",
            "invoice_id": ocr_data.get("file_id", file_id),
            "filename": filename,
            "original_name": file.filename,
            "status": "processed",
            "upload_timestamp": datetime.now().isoformat(),
            "word_count": ocr_data["word_count"],
            "raw_ocr_text": ocr_data["raw_text"],
            "line_items": ocr_data["line_items"],
            "document_type": ocr_data["document_type"],
            "signature_regions": ocr_data.get("signature_regions", []),
            "field_confidence": ocr_data.get("field_confidence", {}),
            # ✅ CRITICAL: Nest data under data as frontend expects
            "data": {
                "confidence": confidence_normalized,
                "supplier_name": ocr_data["supplier_name"],
                "invoice_number": ocr_data["invoice_number"],
                "total_amount": ocr_data["total_amount"],
                "invoice_date": ocr_data["invoice_date"]
            },
            "parsed_data": {
                "confidence": confidence_normalized,
                "supplier_name": ocr_data["supplier_name"],
                "invoice_number": ocr_data["invoice_number"],
                "total_amount": ocr_data["total_amount"],
                "invoice_date": ocr_data["invoice_date"]
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# Add bulletproof ingestion endpoint
@app.post("/api/upload-bulletproof")
async def upload_file_bulletproof(file: UploadFile = File(...)):
    """
    Upload file using bulletproof ingestion v3 system
    
    This endpoint uses the comprehensive ingestion system that can handle:
    - Multiple invoices in one file
    - Split documents across multiple files
    - Out-of-order pages
    - Duplicate detection
    - Cross-file stitching
    - Document classification
    """
    if not BULLETPROOF_INGESTION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Bulletproof ingestion system not available")
    
    try:
        logger.info(f"🚀 Starting bulletproof ingestion for: {file.filename}")
        
        # Save uploaded file
        file_id = str(uuid.uuid4())
        file_path = upload_dir / f"{file_id}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
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
            from ocr.unified_ocr_engine import get_unified_ocr_engine
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
                except Exception as e:
                    logger.warning(f"Failed to extract OCR text from image {i}: {e}")
                    ocr_texts.append('')
            
            file_data['ocr_texts'] = ocr_texts
            
        except Exception as e:
            logger.error(f"Failed to process file for bulletproof ingestion: {e}")
            # Fallback to basic processing
            file_data['images'] = []
            file_data['ocr_texts'] = ['']
        
        # Process with bulletproof ingestion
        files_to_process = [file_data]
        intake_result = intake_router.process_upload(files_to_process)
        
        if not intake_result.success:
            raise HTTPException(status_code=500, detail=f"Bulletproof ingestion failed: {intake_result.errors}")
        
        # Convert canonical entities to response format
        response_data = {
            'success': True,
            'file_id': file_id,
            'filename': file.filename,
            'processing_time': intake_result.processing_time,
            'saved_invoices': [],  # UI expects this key
            'canonical_invoices': [],
            'canonical_documents': [],
            'duplicate_groups': [],
            'stitch_groups': [],
            'warnings': intake_result.warnings,
            'metadata': intake_result.metadata
        }
        
        # Convert canonical invoices
        for invoice in intake_result.canonical_invoices:
            # Create UI-compatible invoice object
            ui_invoice = {
                'id': invoice.canonical_id,
                'supplier_name': invoice.supplier_name,
                'invoice_number': invoice.invoice_number,
                'invoice_date': invoice.invoice_date,
                'currency': invoice.currency,
                'subtotal': invoice.subtotal,
                'tax': invoice.tax,
                'total_amount': invoice.total_amount,
                'confidence': invoice.confidence,
                'field_confidence': invoice.field_confidence or {},
                'warnings': invoice.warnings,
                'source_segments': invoice.source_segments,
                'source_pages': invoice.source_pages,
                # Add missing fields UI expects
                'doc_type': 'invoice',
                'page_range': invoice.source_pages or '',
                'status': 'processed',
                'addresses': {'supplier_address': '', 'delivery_address': ''},
                'signature_regions': [],
                'line_items': [],
                'verification_status': 'unreviewed'
            }
            
            response_data['canonical_invoices'].append(ui_invoice)
            response_data['saved_invoices'].append(ui_invoice)  # Add to saved_invoices for UI
        
        # Convert canonical documents
        for document in intake_result.canonical_documents:
            response_data['canonical_documents'].append({
                'id': document.canonical_id,
                'doc_type': document.doc_type,
                'supplier_name': document.supplier_name,
                'document_number': document.document_number,
                'document_date': document.document_date,
                'confidence': document.confidence,
                'source_segments': document.source_segments,
                'source_pages': document.source_pages
            })
        
        # Convert duplicate groups
        for dup_group in intake_result.duplicate_groups:
            response_data['duplicate_groups'].append({
                'id': dup_group.group_id,
                'duplicate_type': dup_group.duplicate_type,
                'primary_id': dup_group.primary_id,
                'duplicates': dup_group.duplicates,
                'confidence': dup_group.confidence,
                'reasons': dup_group.reasons
            })
        
        # Convert stitch groups
        for stitch_group in intake_result.stitch_groups:
            response_data['stitch_groups'].append({
                'id': stitch_group.group_id,
                'confidence': stitch_group.confidence,
                'doc_type': stitch_group.doc_type,
                'supplier_guess': stitch_group.supplier_guess,
                'invoice_numbers': stitch_group.invoice_numbers,
                'dates': stitch_group.dates,
                'reasons': stitch_group.reasons,
                'segment_count': len(stitch_group.segments)
            })
        
        logger.info(f"✅ Bulletproof ingestion completed: {len(response_data['canonical_invoices'])} invoices, {len(response_data['canonical_documents'])} documents")
        
        return response_data
        
    except Exception as e:
        logger.error(f"❌ Bulletproof ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Basic API endpoints for testing
@app.get("/api/invoices")
async def get_invoices():
    try:
        from db_manager import get_all_invoices
        invoices = get_all_invoices()
        return {"invoices": invoices}
    except Exception as e:
        logger.error(f"❌ Failed to get invoices: {e}")
        return {"invoices": []}

@app.get("/api/delivery-notes")
async def get_delivery_notes():
    try:
        from db_manager import get_all_delivery_notes
        delivery_notes = get_all_delivery_notes()
        return {"delivery_notes": delivery_notes}
    except Exception as e:
        logger.error(f"❌ Failed to get delivery notes: {e}")
        return {"delivery_notes": []}

@app.get("/api/files")
async def get_files():
    try:
        from db_manager import get_all_uploaded_files
        files = get_all_uploaded_files()
        return {"files": files}
    except Exception as e:
        logger.error(f"❌ Failed to get files: {e}")
        return {"files": []} 