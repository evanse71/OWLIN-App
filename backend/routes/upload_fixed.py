#!/usr/bin/env python3
"""
Fixed upload route for Owlin invoice management system.
Implements robust OCR processing with fallback logic and proper error handling.
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import random
import numpy as np
import uuid
import os
import traceback
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
import shutil
import io
from PIL import Image
import fitz  # PyMuPDF for PDF processing
import re
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dev audit store (last upload)
LAST_AUDIT: Dict[str, Any] = {}

# ------------------------
# Helpers for amount parsing
# ------------------------
def _parse_money_str(s: str) -> Optional[float]:
    try:
        s = s.strip()
        s = re.sub(r"[£$€]", "", s)
        s = s.replace(",", "")
        return float(s)
    except Exception:
        return None

def _find_reasonable_total_from_text(text: str) -> Optional[float]:
    """Find a plausible total amount from raw OCR text.
    Strategy:
      - Search for lines containing 'total' then a currency value with decimals
      - Prefer the last occurrence
      - Reject absurd values (> 10,000,000)
    """
    if not text:
        return None
    candidates: list[float] = []
    for line in text.splitlines():
        low = line.lower()
        if "total" not in low:
            continue
        # currency with mandatory decimals
        for m in re.finditer(r"[£$€]\s*([0-9]{1,3}(?:,[0-9]{3})*|[0-9]+)\.[0-9]{2}", line):
            val = _parse_money_str(m.group(0))
            if val is not None and val <= 10_000_000:
                candidates.append(val)
        # currency-less but with decimals (fallback)
        for m in re.finditer(r"\b([0-9]{1,3}(?:,[0-9]{3})*|[0-9]+)\.[0-9]{2}\b", line):
            val = _parse_money_str(m.group(0))
            if val is not None and val <= 10_000_000:
                candidates.append(val)
    if candidates:
        return candidates[-1]  # choose last occurrence
    return None

# Import enhanced unified OCR engine
try:
    from ocr.unified_ocr_engine import get_unified_ocr_engine
    logger.debug("✅ Enhanced unified OCR engine imported successfully")
    ENHANCED_OCR_AVAILABLE = True
except ImportError as e:
    logger.error(f"❌ Failed to import enhanced unified OCR engine: {e}")
    ENHANCED_OCR_AVAILABLE = False

# Import legacy OCR functions as fallback
try:
    from ocr.ocr_engine import run_invoice_ocr, calculate_display_confidence
    logger.debug("✅ Legacy OCR functions imported successfully")
    # Create alias for backward compatibility
    run_paddle_ocr = run_invoice_ocr
except ImportError as e:
    logger.error(f"❌ Failed to import legacy OCR functions: {e}")
    run_paddle_ocr = None

try:
    from ocr.parse_invoice import extract_line_items
    from ocr.field_extractor import extract_invoice_metadata
    logger.debug("✅ extract_invoice_metadata and extract_line_items imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import parse_invoice functions: {e}")
    extract_invoice_metadata = None
    extract_line_items = None

try:
    from ocr.table_extractor import extract_table_data, extract_line_items_from_text
    logger.debug("✅ extract_table_data and extract_line_items_from_text imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import table_extractor functions: {e}")
    extract_table_data = None
    extract_line_items_from_text = None

# Import SmartUploadProcessor for multi-invoice PDF processing
try:
    from ocr.smart_upload_processor import SmartUploadProcessor
    logger.debug("✅ SmartUploadProcessor imported successfully")
    SMART_UPLOAD_AVAILABLE = True
except ImportError as e:
    logger.error(f"❌ Failed to import SmartUploadProcessor: {e}")
    SmartUploadProcessor = None
    SMART_UPLOAD_AVAILABLE = False

# Import Owlin Agent for intelligent analysis
try:
    from agent import run_owlin_agent, get_agent_info
    logger.debug("✅ Owlin Agent imported successfully")
    OWLIN_AGENT_AVAILABLE = True
except ImportError as e:
    logger.error(f"❌ Failed to import Owlin Agent: {e}")
    OWLIN_AGENT_AVAILABLE = False

# Check if enhanced OCR engine is available
if ENHANCED_OCR_AVAILABLE:
    logger.info("✅ Enhanced unified OCR engine available")
else:
    logger.warning("⚠️ Enhanced OCR not available - using legacy OCR as fallback")
    # Check if legacy OCR functions are available
    LEGACY_OCR_AVAILABLE = all([run_paddle_ocr, extract_invoice_metadata, extract_line_items, extract_table_data])
    if LEGACY_OCR_AVAILABLE:
        logger.info("✅ Legacy OCR pipeline available as fallback")
    else:
        logger.warning("⚠️ Some legacy OCR functions are missing")

# Define upload directories
UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Create logs directory for failed uploads
LOGS_DIR = "data/logs"
os.makedirs(LOGS_DIR, exist_ok=True)

# Allowed file types
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

# File size limits (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes

router = APIRouter()

def get_db_connection():
    """Get database connection."""
    db_path = os.path.join("data", "owlin.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return sqlite3.connect(db_path)

def is_valid_file(filename: str) -> bool:
    """Check if file has allowed extension"""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

def validate_file_size(file_size: int) -> bool:
    """Check if file size is within limits"""
    return file_size <= MAX_FILE_SIZE

def validate_file(file: UploadFile) -> None:
    """Validate file type and size"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    if not is_valid_file(file.filename):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    if file.size is None:
        raise HTTPException(status_code=400, detail="Unable to determine file size")
    
    if not validate_file_size(file.size):
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )

def save_file_with_timestamp(file: UploadFile, directory: Path) -> str:
    """Save file with timestamp and return filename"""
    logger.info(f"🔄 Starting file save process for: {file.filename}")
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_id = str(uuid.uuid4())
        extension = Path(file.filename).suffix
        filename = f"{file_id}_{timestamp}{extension}"
        file_path = directory / filename
        
        logger.info(f"📁 Saving file to: {file_path}")
        logger.info(f"📊 File size: {file.size} bytes")
        logger.info(f"📄 File type: {extension}")
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Verify file was saved correctly
        if file_path.exists():
            actual_size = file_path.stat().st_size
            logger.info(f"✅ File saved successfully. Actual size: {actual_size} bytes")
            if actual_size != file.size:
                logger.warning(f"⚠️ Size mismatch: expected {file.size}, got {actual_size}")
        else:
            raise Exception("File was not created")
        
        return filename
        
    except Exception as e:
        logger.error(f"❌ Failed to save file: {str(e)}")
        raise Exception(f"File save failed: {str(e)}")

async def process_upload_with_timeout(filepath: str, filename: str, timeout_seconds: int = 60):
    """Process upload with timeout to prevent hanging using enhanced unified OCR engine."""
    logger.debug(f"🔄 Starting enhanced OCR processing for {filename} with {timeout_seconds}s timeout")
    logger.debug(f"📁 File path: {filepath}")
    
    try:
        # Check if enhanced OCR engine is available
        if not ENHANCED_OCR_AVAILABLE:
            logger.warning("⚠️ Enhanced OCR not available, falling back to legacy OCR")
            if run_paddle_ocr is None:
                logger.error("❌ No OCR engine available")
                raise Exception("OCR engine not available")
            
            # Use legacy OCR as fallback
            logger.debug("🔄 Using legacy OCR engine...")
            ocr_result = await asyncio.wait_for(
                asyncio.to_thread(run_paddle_ocr, filepath),
                timeout=timeout_seconds
            )
        else:
            # Use enhanced unified OCR engine
            logger.debug("🔄 Using enhanced unified OCR engine...")
            
            # Check if file exists
            if not os.path.exists(filepath):
                logger.error(f"❌ File not found: {filepath}")
                raise Exception(f"File not found: {filepath}")
            
            logger.debug(f"📊 File size: {os.path.getsize(filepath)} bytes")
            
            # Get enhanced unified OCR engine
            unified_engine = get_unified_ocr_engine()
            logger.debug("✅ Got unified OCR engine")
            
            # Process document with enhanced OCR
            logger.debug("🔄 Calling enhanced unified OCR engine...")
            result = await asyncio.wait_for(
                asyncio.to_thread(unified_engine.process_document, filepath),
                timeout=timeout_seconds
            )
            
            logger.debug(f"📝 OCR result: success={result.success}, confidence={result.overall_confidence}, supplier={result.supplier}, total={result.total_amount}")
            
            # Convert enhanced result to legacy format for compatibility
            if result.success:
                ocr_result = {
                    "confidence": result.overall_confidence,
                    "supplier_name": result.supplier,
                    "invoice_number": result.invoice_number,
                    "total_amount": result.total_amount,
                    "invoice_date": result.date,
                    "raw_text": result.raw_text,
                    "word_count": result.word_count,
                    "line_items": result.line_items,
                    "document_type": result.document_type,
                    "engine_used": result.engine_used,
                    "processing_time": result.processing_time,
                    # Back-compat aliases expected by downstream logic
                    "overall_confidence": result.overall_confidence,
                    "total_words": result.word_count,
                    "raw_ocr_text": result.raw_text,
                    "pages": [{
                        "page": 1,
                        "avg_confidence": float(result.overall_confidence) * 100.0 if isinstance(result.overall_confidence, (int, float)) else 0.0,
                        "word_count": int(result.word_count) if isinstance(result.word_count, (int, float)) else 0,
                        "psm_used": "unified"
                    }]
                }
                logger.debug(f"✅ Enhanced OCR completed for {filename}")
                logger.debug(f"📝 Enhanced OCR result: confidence={result.overall_confidence:.2f}, supplier={result.supplier}, total={result.total_amount}")
            else:
                logger.error(f"❌ Enhanced OCR failed: {result.error_message}")
                raise Exception(f"Enhanced OCR failed: {result.error_message}")
        
        logger.debug(f"📝 OCR result keys: {list(ocr_result.keys()) if isinstance(ocr_result, dict) else 'Not a dict'}")
        
        return ocr_result
        
    except asyncio.TimeoutError:
        logger.error(f"❌ OCR processing timed out after {timeout_seconds}s for {filename}")
        logger.error(f"📋 Timeout details: File may be too large or PaddleOCR may be slow on this system")
        logger.error(f"📋 System info: Intel Mac detected - PaddleOCR may need more time")
        raise HTTPException(
            status_code=408, 
            detail=f"OCR processing timed out after {timeout_seconds} seconds. This may be due to large file size or system performance. Try uploading a smaller file or image instead of PDF."
        )
    except Exception as e:
        logger.exception(f"❌ OCR processing failed for {filename}")
        logger.error(f"📋 Error details: {str(e)}")
        logger.error(f"📋 Error type: {type(e).__name__}")
        
        # Provide more helpful error messages
        if "PaddleOCR" in str(e):
            error_msg = f"OCR processing failed: PaddleOCR not available or failed to initialize. Please install PaddleOCR or try a different file format."
        elif "timeout" in str(e).lower():
            error_msg = f"OCR processing timed out. Try uploading a smaller file or image instead of PDF."
        else:
            error_msg = f"OCR processing failed: {str(e)}"
        
        raise HTTPException(status_code=500, detail=error_msg)
def get_timeout_for_file(file_path: str) -> int:
    """Get appropriate timeout based on file type and size"""
    file_size = os.path.getsize(file_path)
    file_ext = Path(file_path).suffix.lower()
    
    if file_ext == ".pdf":
        return 60  # PDFs take longer
    elif file_ext in [".jpg", ".jpeg", ".png"]:
        return 30  # Images are faster
    else:
        return 45  # Default

@router.post("/upload")
async def upload_invoice(file: UploadFile = File(...)):
    """Upload and process invoice with robust error handling and fallback logic."""
    logger.debug(f"Upload received: {file.filename if file else 'No file'}")
    logger.info(f"🚀 Starting invoice upload process for: {file.filename}")
    logger.debug(f"📊 File size: {file.size} bytes")
    logger.debug(f"📋 Content type: {file.content_type}")
    
    # ✅ Enhanced input validation
    if not file:
        logger.error("❌ No file uploaded")
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    if not file.filename:
        logger.error("❌ No filename provided")
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Temporary file path for processing
    temp_filepath = None
    
    try:
        # Step 1: Validate file
        logger.info("🔄 Step 1: Validating file...")
        validate_file(file)
        logger.info("✅ File validation passed")
        
        # Step 2: Save file temporarily
        logger.info("🔄 Step 2: Saving file temporarily...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_id = str(uuid.uuid4())
        extension = Path(file.filename).suffix
        temp_filename = f"{file_id}_{timestamp}{extension}"
        temp_filepath = os.path.join(UPLOAD_DIR, temp_filename)
        
        # Save file
        logger.debug(f"📁 Saving to: {temp_filepath}")
        with open(temp_filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"✅ File saved as: {temp_filename}")
        
        # Step 2.5: Check for multi-invoice PDF with enhanced detection
        logger.info("🔄 Step 2.5: Checking for multi-invoice PDF...")
        multi_invoice_result = None
        if file.filename.lower().endswith((".pdf", ".txt")):
            try:
                # Use enhanced OCR engine for better detection
                if ENHANCED_OCR_AVAILABLE:
                    logger.info("🔄 Using enhanced OCR engine for multi-invoice detection...")
                    unified_engine = get_unified_ocr_engine()
                    
                    # Process the PDF with enhanced OCR
                    result = unified_engine.process_document(temp_filepath)
                    
                    if result.success and result.raw_text:
                        # Simple but effective multi-invoice detection
                        import re
                        
                        # Look for multiple invoice numbers or repeated patterns
                        invoice_patterns = [
                            r'\b(?:invoice|inv)[\s#:]*([A-Za-z0-9\-]+)',
                            r'\b(INV[0-9\-]+)\b',
                            r'\b([A-Z]{2,3}[0-9]{3,8})\b',
                            r'(?:page|p)\s+\d+\s+of\s+\d+',  # Page numbering
                            r'(?:continued|cont\.)',  # Continuation indicators
                        ]
                        
                        found_invoices = []
                        for pattern in invoice_patterns:
                            matches = re.findall(pattern, result.raw_text, re.IGNORECASE)
                            found_invoices.extend(matches)
                        
                        # Also check for repeated supplier names
                        supplier_patterns = [
                            r'(?:WILD HORSE BREWING CO LTD|RED DRAGON DISPENSE LIMITED|SNOWDONIA HOSPITALITY)',
                            r'([A-Za-z\s&\.]+)\s*(?:Ltd|Limited|Inc|Corp)',
                        ]
                        
                        found_suppliers = []
                        for pattern in supplier_patterns:
                            matches = re.findall(pattern, result.raw_text, re.IGNORECASE)
                            found_suppliers.extend(matches)
                        
                        unique_invoices = set(found_invoices)
                        unique_suppliers = set(found_suppliers)
                        
                        # If we find multiple different invoice numbers OR multiple suppliers, it's likely multiple invoices
                        is_multi_invoice = len(unique_invoices) > 1 or len(unique_suppliers) > 1
                        
                        if is_multi_invoice:
                            logger.info(f"✅ Enhanced OCR detected multiple invoices!")
                            logger.info(f"  Invoice numbers: {unique_invoices}")
                            logger.info(f"  Suppliers: {unique_suppliers}")
                            
                            # Create separate documents for each detected invoice
                            suggested_docs = []
                            
                            # Split text by potential invoice boundaries
                            text_parts = result.raw_text.split("--- PAGE")
                            if len(text_parts) > 1:
                                # Multi-page PDF with page separators
                                for i, part in enumerate(text_parts[1:], 1):  # Skip first empty part
                                    if part.strip():
                                        suggested_docs.append({
                                            "type": "invoice",
                                            "ocr_text": part.strip(),
                                            "pages": [i],
                                            "confidence": result.overall_confidence,
                                            "metadata": {
                                                "invoice_number": f"INV-{i:03d}",
                                                "supplier_name": "Unknown Supplier",
                                                "total_amount": 0.0
                                            }
                                        })
                            else:
                                # Single text, create multiple invoices based on detected patterns
                                for i, invoice_num in enumerate(unique_invoices, 1):
                                    suggested_docs.append({
                                        "type": "invoice",
                                        "ocr_text": result.raw_text,  # Use full text for each
                                        "pages": [i],
                                        "confidence": result.overall_confidence,
                                        "metadata": {
                                            "invoice_number": invoice_num,
                                            "supplier_name": "Unknown Supplier",
                                            "total_amount": 0.0
                                        }
                                    })
                            
                            if suggested_docs:
                                multi_invoice_result = {
                                    "suggested_documents": suggested_docs,
                                    "total_pages": len(suggested_docs),
                                    "processing_summary": {
                                        "pages_processed": len(suggested_docs),
                                        "invoices_found": len(suggested_docs),
                                        "skipped_pages": 0
                                    }
                                }
                        else:
                            logger.info("ℹ️ Enhanced OCR detected single invoice")
                            multi_invoice_result = None
                    else:
                        logger.info("ℹ️ Enhanced OCR processing failed, trying SmartUploadProcessor")
                        # Fallback to SmartUploadProcessor
                        processor = SmartUploadProcessor()
                        multi_invoice_result = processor.process_multi_invoice_pdf(temp_filepath)
                else:
                    # Use SmartUploadProcessor as fallback
                    processor = SmartUploadProcessor()
                    multi_invoice_result = processor.process_multi_invoice_pdf(temp_filepath)
                
                if multi_invoice_result and "suggested_documents" in multi_invoice_result:
                    suggested_docs = multi_invoice_result["suggested_documents"]
                    if len(suggested_docs) > 1:
                        logger.info(f"✅ Multi-invoice PDF detected! Found {len(suggested_docs)} invoices")
                        
                        # Process each invoice separately using enhanced OCR engine
                        invoices = []
                        for doc in suggested_docs:
                            if doc.get("type") == "invoice":
                                invoice_text = doc.get("ocr_text", "")
                                page_numbers = doc.get("pages", [])
                                
                                # Use enhanced OCR engine for better field extraction
                                supplier_name = "Unknown Supplier"
                                invoice_number = "Unknown"
                                total_amount = 0.0
                                invoice_date = datetime.now().strftime("%Y-%m-%d")
                                confidence = 0.5  # Default confidence
                                
                                if invoice_text and ENHANCED_OCR_AVAILABLE:
                                    try:
                                        # Use enhanced OCR engine to extract fields from text
                                        unified_engine = get_unified_ocr_engine()
                                        
                                        # Process the extracted text directly using enhanced field extraction
                                        from ocr.ocr_engine import OCRResult
                                        # Create a mock OCR result from the text with correct fields
                                        mock_ocr_results = [OCRResult(
                                            text=invoice_text,
                                            confidence=0.8,
                                            bounding_box=[[0,0],[100,0],[100,100],[0,100]],
                                            page_number=1
                                        )]
                                        
                                        # Use the enhanced field extraction directly
                                        extracted_data = unified_engine._enhanced_field_extraction(invoice_text, mock_ocr_results)
                                        
                                        supplier_name = extracted_data.get("supplier", "Unknown Supplier")
                                        invoice_number = extracted_data.get("invoice_number", "Unknown")
                                        total_amount = extracted_data.get("total_amount", 0.0)
                                        invoice_date = extracted_data.get("date", datetime.now().strftime("%Y-%m-%d"))
                                        confidence = extracted_data.get("confidence", 0.5)
                                        
                                        # Extract line items using enhanced extractor
                                        try:
                                            line_items = unified_engine._extract_line_items_enhanced(mock_ocr_results)
                                        except Exception:
                                            line_items = []
                                        
                                    except Exception as e:
                                        logger.warning(f"⚠️ Enhanced OCR processing failed for invoice: {e}")
                                        # Fallback to basic extraction
                                        if invoice_text:
                                            try:
                                                temp_metadata = extract_invoice_metadata(invoice_text)
                                                supplier_name = temp_metadata.get("supplier_name", "Unknown Supplier")
                                            except:
                                                pass
                                else:
                                    # Fallback to legacy processing
                                    legacy_conf = calculate_display_confidence(doc.get("confidence", 0.0))
                                    confidence = legacy_conf / 100.0  # Normalize to 0-1 range
                                    if invoice_text:
                                        try:
                                            temp_metadata = extract_invoice_metadata(invoice_text)
                                            supplier_name = temp_metadata.get("supplier_name", "Unknown Supplier")
                                        except:
                                            pass
                                
                                invoice_id = str(uuid.uuid4())
                                page_range = f"{min(page_numbers)}–{max(page_numbers)}" if page_numbers else "Unknown"
                                
                                # Save to database with enhanced OCR results
                                conn = get_db_connection()
                                cursor = conn.cursor()
                                cursor.execute("""
                                    INSERT INTO invoices (
                                        id, invoice_number, invoice_date, supplier_name, total_amount,
                                        status, confidence, upload_timestamp, ocr_text, parent_pdf_filename,
                                        subtotal, vat, vat_rate, total_incl_vat, page_range
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    invoice_id,
                                    invoice_number,  # Use enhanced OCR result
                                    invoice_date,    # Use enhanced OCR result
                                    supplier_name,   # Use enhanced OCR result
                                    total_amount,    # Use enhanced OCR result
                                    'scanned',
                                    confidence,      # Use enhanced OCR result
                                    datetime.now().isoformat(),
                                    invoice_text,
                                    file.filename,
                                    0.0,  # subtotal - could be enhanced later
                                    0.0,  # vat - could be enhanced later
                                    20.0, # vat_rate
                                    total_amount,    # Use enhanced total as total_incl_vat
                                    page_range
                                ))
                                conn.commit()
                                conn.close()
                                
                                invoices.append({
                                    "invoice_id": invoice_id,
                                    "supplier_name": supplier_name,
                                    "invoice_number": invoice_number,
                                    "invoice_date": invoice_date,
                                    "total_amount": total_amount,
                                    "confidence": confidence,
                                    "page_range": f"Pages {page_range}",
                                    "invoice_text": invoice_text,
                                    "page_numbers": page_numbers,
                                    "metadata": {
                                        "supplier_name": supplier_name,
                                        "invoice_number": invoice_number,
                                        "invoice_date": invoice_date,
                                        "total_amount": total_amount,
                                        "confidence": confidence
                                    },
                                    "line_items": line_items or doc.get("line_items", [])
                                })
                        
                        if invoices:
                            logger.info(f"✅ Successfully processed {len(invoices)} invoices from multi-invoice PDF")
                            return {
                                "message": f"Multi-invoice PDF processed successfully",
                                "data": {
                                    "saved_invoices": invoices,
                                    "total_invoices": len(invoices)
                                },
                                "saved_invoices": invoices,
                                "total_invoices": len(invoices),
                                "original_filename": file.filename
                            }
                    else:
                        logger.info("ℹ️ Single invoice PDF detected - proceeding with normal processing")
                else:
                    logger.info("ℹ️ No multi-invoice structure detected - proceeding with normal processing")
            except Exception as multi_error:
                logger.warning(f"⚠️ Multi-invoice detection failed: {multi_error}")
                logger.info("ℹ️ Proceeding with normal single-invoice processing")
        
        # Fallback: per-page processing if no multi-invoice structure and multi-page PDF
        if (multi_invoice_result is None or not multi_invoice_result.get("suggested_documents")) and file.filename.lower().endswith(".pdf"):
            try:
                import fitz
                doc = fitz.open(temp_filepath)
                if len(doc) > 1:
                    logger.info(f"🔧 Per-page fallback: processing {len(doc)} pages as separate invoices")
                    invoices = []
                    for i in range(len(doc)):
                        page = doc.load_page(i)
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                        from PIL import Image
                        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

                        unified_engine = get_unified_ocr_engine()
                        # Process single page image through unified engine
                        import time
                        start_t = time.time()
                        single_result = unified_engine._process_single_page(img, start_t, temp_filepath, optimize_for_speed=True)

                        supplier_name = single_result.supplier or "Unknown Supplier"
                        invoice_number = single_result.invoice_number or f"INV-{i+1:03d}"
                        total_amount = single_result.total_amount or 0.0
                        invoice_date = single_result.date or datetime.now().strftime("%Y-%m-%d")
                        confidence = float(single_result.overall_confidence or 0.5)
                        line_items = single_result.line_items or []

                        invoice_id = str(uuid.uuid4())
                        page_range = f"{i+1}–{i+1}"

                        # Save to DB
                        conn = get_db_connection(); cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO invoices (
                                id, invoice_number, invoice_date, supplier_name, total_amount,
                                status, confidence, upload_timestamp, ocr_text, parent_pdf_filename,
                                subtotal, vat, vat_rate, total_incl_vat, page_range
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            invoice_id, invoice_number, invoice_date, supplier_name, total_amount,
                            'scanned', confidence, datetime.now().isoformat(),
                            single_result.raw_text or "", file.filename,
                            0.0, 0.0, 20.0, total_amount, page_range
                        ))
                        conn.commit(); conn.close()

                        invoices.append({
                            "invoice_id": invoice_id,
                            "supplier_name": supplier_name,
                            "invoice_number": invoice_number,
                            "invoice_date": invoice_date,
                            "total_amount": total_amount,
                            "confidence": confidence,
                            "page_range": f"Pages {page_range}",
                            "invoice_text": single_result.raw_text or "",
                            "page_numbers": [i+1],
                            "metadata": {
                                "supplier_name": supplier_name,
                                "invoice_number": invoice_number,
                                "invoice_date": invoice_date,
                                "total_amount": total_amount,
                                "confidence": confidence
                            },
                            "line_items": line_items
                        })

                    doc.close()
                    if invoices:
                        return {
                            "message": "Per-page fallback processed successfully",
                            "data": {
                                "saved_invoices": invoices,
                                "total_invoices": len(invoices)
                            },
                            "saved_invoices": invoices,
                            "total_invoices": len(invoices),
                            "original_filename": file.filename
                        }
            except Exception as e:
                logger.warning(f"⚠️ Per-page fallback failed: {e}")
        
        # Step 3: Run OCR with timeout
        logger.info("🔄 Step 3: Running OCR processing...")
        try:
            # Get timeout from environment variable or use default
            timeout_seconds = get_timeout_for_file(temp_filepath)
            logger.info(f"⏱️ Using OCR timeout: {timeout_seconds} seconds")
            
            ocr_result = await process_upload_with_timeout(temp_filepath, file.filename, timeout_seconds=timeout_seconds)
            logger.info("✅ OCR processing completed")
            
            # Check if OCR needs retry
            raw_overall_conf = float(ocr_result.get('overall_confidence', 0.0) or 0.0)
            # Normalize to percentage for thresholds/logging
            overall_confidence = raw_overall_conf * 100.0 if raw_overall_conf <= 1.0 else raw_overall_conf
            total_words = int(ocr_result.get('total_words', 0) or 0)
            was_retried = ocr_result.get('was_retried', False)
            
            logger.info(f"📊 OCR Results: {overall_confidence:.1f}% confidence, {total_words} words, retried: {was_retried}")
            
            # If confidence is very low and we haven't retried yet, try again
            if overall_confidence < 15 and not was_retried:
                logger.warning(f"⚠️ Very low confidence ({overall_confidence:.1f}%), attempting retry...")
                try:
                    # Retry with different settings
                    retry_result = await process_upload_with_timeout(temp_filepath, file.filename, timeout_seconds=timeout_seconds)
                    rr = float(retry_result.get('overall_confidence', 0.0) or 0.0)
                    retry_confidence = rr * 100.0 if rr <= 1.0 else rr
                    retry_words = int(retry_result.get('total_words', 0) or 0)
                    
                    logger.info(f"📊 Retry Results: {retry_confidence:.1f}% confidence, {retry_words} words")
                    
                    # Use retry result if it's better
                    if retry_confidence > overall_confidence or retry_words > total_words:
                        ocr_result = retry_result
                        logger.info("✅ Retry improved OCR results")
                    else:
                        logger.info("ℹ️ Retry did not improve results, using original")
                        
                except Exception as retry_error:
                    logger.warning(f"⚠️ OCR retry failed: {retry_error}")
                    # Continue with original result
                    
        except Exception as ocr_error:
            logger.exception("❌ OCR processing failed - using fallback")
            # Save failed PDF for debugging
            failed_file_path = os.path.join(LOGS_DIR, f"failed_{temp_filename}")
            try:
                shutil.copy2(temp_filepath, failed_file_path)
                logger.info(f"📁 Failed PDF saved for debugging: {failed_file_path}")
            except Exception as copy_error:
                logger.warning(f"⚠️ Could not save failed PDF: {copy_error}")
            
            # Return fallback response
            return create_fallback_response(file.filename, str(ocr_error))
        
        # Step 4: Extract table data
        logger.info("🔄 Step 4: Extracting table data...")
        table_data = []
        try:
            if extract_table_data and ocr_result.get('pages'):
                for page in ocr_result['pages']:
                    if page.get('word_boxes'):
                        page_table_data = extract_table_data(page['word_boxes'])
                        table_data.extend(page_table_data)
            logger.info(f"✅ Table extraction completed. Found {len(table_data)} table rows")
        except Exception as table_error:
            logger.warning(f"⚠️ Table extraction failed: {table_error}")
            table_data = []
        
        # Step 5: Extract metadata and line items
        logger.info("🔄 Step 5: Extracting metadata and line items...")
        raw_text = ocr_result.get('raw_ocr_text') or ocr_result.get('raw_text', '')
        # Ensure line_items is defined
        line_items: List[Dict[str, Any]] = []
        
        # Log per-page OCR details for debugging
        if ocr_result.get('pages'):
            logger.info("📄 Per-page OCR details:")
            for page in ocr_result['pages']:
                page_num = page.get('page', 'Unknown')
                confidence = page.get('avg_confidence', 0.0)
                word_count = page.get('word_count', 0)
                psm_used = page.get('psm_used', 'Unknown')
                logger.info(f"   Page {page_num}: {confidence:.1f}% confidence, {word_count} words, PSM {psm_used}")
        
        # Check if OCR text is mostly noise
        if raw_text:
            # Count meaningful characters vs noise
            meaningful_chars = sum(1 for c in raw_text if c.isalnum() or c.isspace())
            total_chars = len(raw_text)
            meaningful_ratio = meaningful_chars / total_chars if total_chars > 0 else 0
            
            logger.info(f"📊 OCR quality check: {meaningful_chars}/{total_chars} meaningful chars ({meaningful_ratio:.2%})")
            
            if meaningful_ratio < 0.3:  # Less than 30% meaningful characters
                logger.warning("⚠️ OCR text appears to be mostly noise - document may be low quality or corrupted")
                raw_text = ""  # Treat as no text extracted
        
        # ✅ Enhanced metadata extraction with fallback
        try:
            if raw_text:
                # Parse using text-based invoice parser for robust extraction
                try:
                    from ocr.parse_invoice import parse_invoice
                    parsed = parse_invoice(raw_text)
                    metadata = {
                        'supplier_name': parsed.supplier or 'Unknown',
                        'invoice_number': parsed.invoice_number or 'Unknown',
                        'invoice_date': parsed.date or 'Unknown',
                        'total_amount': float(parsed.gross_total or 0.0),
                        'subtotal': float(parsed.net_total or 0.0),
                        'vat': float(parsed.vat_total or 0.0),
                        'vat_rate': float(parsed.vat_rate) if parsed.vat_rate is not None else 20.0,
                        'total_incl_vat': float(parsed.gross_total or 0.0),
                    }
                    # If parser returned line items, map them
                    if getattr(parsed, 'line_items', None):
                        line_items = [{
                            'description': getattr(li, 'description', ''),
                            'quantity': float(getattr(li, 'quantity', 0.0) or 0.0),
                            'unit_price': float(getattr(li, 'unit_price', 0.0) or 0.0),
                            'line_total': float(getattr(li, 'total_price', 0.0) or 0.0),
                            'confidence': float(getattr(li, 'confidence', 0.7) or 0.7),
                        } for li in parsed.line_items]
                    logger.info(f"✅ Metadata extracted via parse_invoice: supplier={metadata['supplier_name']}, total={metadata['total_amount']}")
                except Exception as pe:
                    logger.warning(f"⚠️ Text parser failed: {pe}")
                    # Fall back to field extractor if available and OCR results exist
                    if extract_invoice_metadata and ocr_result.get('pages'):
                        try:
                            # Build minimal OCR result blocks for field extractor
                            blocks = []
                            for pg in ocr_result.get('pages', []):
                                for wb in pg.get('word_boxes', []) or []:
                                    text_val = wb.get('text') or ''
                                    conf_val = float(wb.get('confidence', 0.0) or 0.0) * 100.0
                                    bbox = wb.get('bbox') or [0,0,0,0]
                                    page_num = int(pg.get('page', 1) or 1)
                                    blocks.append({ 'text': text_val, 'confidence': conf_val, 'bbox': bbox, 'page_num': page_num })
                            metadata = extract_invoice_metadata(blocks)
                            logger.info(f"✅ Metadata extracted via field_extractor")
                        except Exception as fe:
                            logger.warning(f"⚠️ Field extractor failed: {fe}")
                            metadata = create_fallback_metadata()
                    else:
                        metadata = create_fallback_metadata()
            else:
                metadata = create_fallback_metadata()
            # ✅ Ensure supplier fallback from filename
            if metadata.get('supplier_name') in (None, '', 'Unknown'):
                metadata['supplier_name'] = os.path.splitext(file.filename)[0]
                logger.info(f"✅ Using filename as supplier name: {metadata['supplier_name']}")

            # ✅ Plausibility and fallback totals
            total_from_items = None
            if line_items:
                try:
                    total_from_items = sum(float(it.get('line_total') or it.get('total_price') or 0.0) for it in line_items)
                except Exception:
                    total_from_items = None

            # If total is missing or absurd, try derive better
            total_val = float(metadata.get('total_amount') or 0.0)
            if total_val <= 0.0 or total_val > 10_000_000:
                # Try to find plausible total directly in text
                from_text = _find_reasonable_total_from_text(raw_text)
                if from_text is not None:
                    metadata['total_amount'] = from_text
                    metadata['total_incl_vat'] = from_text
                    logger.info(f"✅ Total derived from text: £{from_text:.2f}")
                elif total_from_items is not None and total_from_items > 0:
                    metadata['total_amount'] = total_from_items
                    metadata['total_incl_vat'] = total_from_items
                    logger.info(f"✅ Total derived from line items: £{total_from_items:.2f}")
                else:
                    logger.warning("⚠️ Total amount not detected after derivation attempts")
        except Exception as metadata_error:
            logger.warning(f"⚠️ Metadata extraction failed: {metadata_error}")
            metadata = create_fallback_metadata()
            # ✅ Ensure fallback metadata has supplier name
            if metadata.get('supplier_name') in (None, '', 'Unknown'):
                metadata['supplier_name'] = os.path.splitext(file.filename)[0]
        
        # ✅ Enhanced line item extraction
        line_items = line_items if isinstance(line_items, list) and line_items else []
        try:
            if extract_line_items and table_data and len(table_data) > 0:
                line_items = extract_line_items(table_data)
                logger.info(f"✅ Line items extracted from table: {len(line_items)} items")
            # If parse_invoice already populated line_items above, keep them
            else:
                if not raw_text and not line_items:
                    logger.warning("⚠️ No text available for line item extraction")
        except Exception as line_items_error:
            logger.warning(f"⚠️ Line items extraction failed: {line_items_error}")
            line_items = []
        
        # ✅ Compute simple field confidence signals for UI (0..1 scale)
        try:
            field_confidence = {
                "supplier_name": 0.8 if (metadata.get('supplier_name') and metadata.get('supplier_name') != 'Unknown') else 0.4,
                "invoice_number": 0.75 if (metadata.get('invoice_number') and metadata.get('invoice_number') != 'Unknown') else 0.4,
                "invoice_date": 0.7 if (metadata.get('invoice_date') and metadata.get('invoice_date') != 'Unknown') else 0.4,
                "total_amount": 0.8 if float(metadata.get('total_amount') or 0) > 0 else 0.4,
                "line_items": 0.7 if line_items else 0.5,
            }
        except Exception:
            field_confidence = {}

        # ✅ Calculate totals from line items if missing
        if line_items and (metadata.get('total_amount', 0) == 0 or metadata.get('subtotal', 0) == 0):
            calculated_subtotal = sum(item.get('line_total_excl_vat', item.get('total_price', 0)) for item in line_items)
            calculated_vat = calculated_subtotal * (metadata.get('vat_rate', 20.0) / 100)
            calculated_total = calculated_subtotal + calculated_vat
            
            if metadata.get('subtotal', 0) == 0:
                metadata['subtotal'] = calculated_subtotal
            if metadata.get('vat', 0) == 0:
                metadata['vat'] = calculated_vat
            if metadata.get('total_amount', 0) == 0:
                metadata['total_amount'] = calculated_total
            if metadata.get('total_incl_vat', 0) == 0:
                metadata['total_incl_vat'] = calculated_total
            
            logger.info(f"✅ Calculated totals from line items: subtotal={metadata['subtotal']}, vat={metadata['vat']}, total={metadata['total_amount']}")
        
        # Log detailed information for debugging
        logger.debug(f"Parsed metadata: {metadata}")
        logger.debug(f"Line items: {line_items}")
        logger.debug(f"Raw OCR text length: {len(raw_text) if raw_text else 0}")
        
        # Log any fallback being used
        if not line_items:
            logger.warning("⚠️ No line items found - using fallback")
        if metadata.get('supplier_name') == 'Unknown':
            logger.warning("⚠️ Supplier name not detected - using fallback")
        if metadata.get('total_amount', 0) == 0:
            logger.warning("⚠️ Total amount not detected - using fallback")
        
        # Step 6: Calculate confidence and manual review flag
        logger.info("🔄 Step 6: Calculating confidence...")
        # Use standardized display confidence calculation
        raw_overall_conf = float(ocr_result.get('overall_confidence', 0.0) or 0.0)
        # Normalize to 0..1 for display calc
        raw_for_display = raw_overall_conf if raw_overall_conf <= 1.0 else (raw_overall_conf / 100.0)
        display_confidence = calculate_display_confidence(raw_for_display)
        confidence = display_confidence
        # Enhanced manual review logic
        manual_review = (
            display_confidence < 60.0 or 
            not line_items or 
            metadata.get('supplier_name') == 'Unknown' or
            metadata.get('total_amount', 0) == 0.0
        )
        overall_confidence = raw_for_display * 100.0
        logger.debug(f"OCR confidence: {overall_confidence}")
        logger.debug(f"Display confidence (0-100%): {display_confidence}%")
        logger.debug(f"Manual review required: {manual_review}")
        logger.info(f"✅ Confidence calculated: {display_confidence}%, Manual review: {manual_review}")
        
        # ✅ Determine document status based on OCR quality
        total_words = int(ocr_result.get('total_words', 0) or 0)
        
        # Set status based on OCR quality
        if overall_confidence < 10 or total_words == 0:
            document_status = 'manual_review'
            logger.warning(f"⚠️ Low OCR quality - confidence: {overall_confidence:.1f}%, words: {total_words} - marking for manual review")
        elif overall_confidence < 50:
            document_status = 'processed'  # Processed but low confidence
            logger.info(f"ℹ️ Moderate OCR quality - confidence: {overall_confidence:.1f}%")
        else:
            document_status = 'processed'  # Good quality
            logger.info(f"✅ Good OCR quality - confidence: {overall_confidence:.1f}%")
        
        # Step 6.5: Run Owlin Agent analysis
        logger.info("🔄 Step 6.5: Running Owlin Agent analysis...")
        agent_analysis = None
        if OWLIN_AGENT_AVAILABLE:
            try:
                # Prepare invoice data for agent analysis
                invoice_data = {
                    "metadata": metadata,
                    "line_items": line_items,
                    "delivery_note_attached": False,  # Will be updated when delivery notes are matched
                    "confidence": confidence
                }
                
                # Run agent analysis (no historical prices for now)
                agent_analysis = run_owlin_agent(invoice_data, historical_prices={})
                
                logger.info(f"✅ Agent analysis completed:")
                logger.info(f"   Confidence Score: {agent_analysis.get('confidence_score', 0):.1f}%")
                logger.info(f"   Manual Review Required: {agent_analysis.get('manual_review_required', True)}")
                logger.info(f"   Flags Found: {len(agent_analysis.get('flags', []))}")
                logger.info(f"   Summary Messages: {len(agent_analysis.get('summary', []))}")
                
                # Update manual review flag based on agent analysis
                if agent_analysis.get('manual_review_required', True):
                    manual_review = True
                    logger.info("🔄 Manual review flag updated by agent analysis")
                
            except Exception as agent_error:
                logger.warning(f"⚠️ Owlin Agent analysis failed: {agent_error}")
                agent_analysis = None
        else:
            logger.info("ℹ️ Owlin Agent not available - skipping intelligent analysis")
        
        # Step 7: Save to database
        logger.info("🔄 Step 7: Saving to database...")
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Create invoice record
            invoice_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO invoices (
                    id, invoice_number, invoice_date, supplier_name, total_amount,
                    status, confidence, upload_timestamp, ocr_text, parent_pdf_filename,
                    subtotal, vat, vat_rate, total_incl_vat
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                invoice_id,
                metadata.get('invoice_number', 'Unknown'),
                metadata.get('invoice_date', datetime.now().strftime("%Y-%m-%d")),
                metadata.get('supplier_name', 'Unknown'),
                metadata.get('total_amount', 0.0),
                'scanned',
                confidence,
                datetime.now().isoformat(),
                raw_text,
                file.filename,
                metadata.get('subtotal', 0.0),
                metadata.get('vat', 0.0),
                metadata.get('vat_rate', 20.0),
                metadata.get('total_incl_vat', 0.0)
            ))
            
            conn.commit()
            conn.close()
            logger.info("✅ Database record created")
        except Exception as db_error:
            logger.warning(f"⚠️ Database save failed: {db_error}")
            invoice_id = str(uuid.uuid4())  # Generate ID anyway
        
        # ✅ Enhanced response with status and quality metrics
        response_data = {
            "message": "Invoice processed successfully",
            "invoice_id": invoice_id,
            "supplier_name": metadata.get('supplier_name', 'Unknown'),
            "invoice_number": metadata.get('invoice_number', 'Unknown'),
            "invoice_date": metadata.get('invoice_date', datetime.now().strftime("%Y-%m-%d")),
            "total_amount": metadata.get('total_amount', 0.0),
            "subtotal": metadata.get('subtotal', 0.0),
            "vat": metadata.get('vat', 0.0),
            "vat_rate": metadata.get('vat_rate', 20.0),
            "total_incl_vat": metadata.get('total_incl_vat', 0.0),
            "confidence": display_confidence,
            "word_count": total_words,
            "status": document_status,
            "was_retried": ocr_result.get('was_retried', False),
            "psm_used": ocr_result.get('pages', [{}])[0].get('psm_used') if ocr_result.get('pages') else None,
            "data": metadata,  # Frontend expects 'data' not 'parsed_data'
            "parsed_data": metadata,  # Keep for backward compatibility
            "line_items": line_items,
            "table_data": table_data,
            "field_confidence": field_confidence,
            "original_filename": file.filename,
            # ✅ Add OCR debug data
            "raw_ocr_text": raw_text,
            "pages": ocr_result.get('pages', []),
            "overall_confidence": display_confidence,
            "total_words": total_words
        }
        # Update audit store
        try:
            LAST_AUDIT.update({
                "timestamp": datetime.now().isoformat(),
                "filename": file.filename,
                "engine": ocr_result.get('engine_used', 'unified'),
                "word_count": total_words,
                "confidence_pct": display_confidence,
                "supplier": response_data["supplier_name"],
                "invoice_number": response_data["invoice_number"],
                "invoice_date": response_data["invoice_date"],
                "total_amount": response_data["total_amount"],
                "line_items": len(line_items or []),
                "raw_text_preview": (raw_text or "")[:800],
                "field_confidence": field_confidence,
                "warnings": warnings if 'warnings' in locals() else [],
            })
        except Exception:
            pass
        
        logger.info("✅ Upload process completed successfully")
        return response_data
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.exception(f"❌ Upload processing failed: {e}")
        logger.error(f"📋 Full traceback: {traceback.format_exc()}")
        
        # Save failed file for debugging
        if temp_filepath and os.path.exists(temp_filepath):
            try:
                failed_file_path = os.path.join(LOGS_DIR, f"failed_{os.path.basename(temp_filepath)}")
                shutil.copy2(temp_filepath, failed_file_path)
                logger.info(f"📁 Failed file saved for debugging: {failed_file_path}")
            except Exception as copy_error:
                logger.warning(f"⚠️ Could not save failed file: {copy_error}")
        
        # Return comprehensive fallback response
        fallback = create_fallback_response(file.filename, str(e))
        # Update audit on fallback
        try:
            LAST_AUDIT.update({
                "timestamp": datetime.now().isoformat(),
                "filename": file.filename if 'file' in locals() else 'unknown',
                "engine": ocr_result.get('engine_used', 'unified') if 'ocr_result' in locals() and isinstance(ocr_result, dict) else 'unknown',
                "error": str(e),
                "raw_text_preview": (raw_text if 'raw_text' in locals() else '')[:800],
            })
        except Exception:
            pass
        return fallback
    finally:
        # Clean up temporary file
        if temp_filepath and os.path.exists(temp_filepath):
            try:
                os.remove(temp_filepath)
                logger.debug(f"✅ Temporary file cleaned up: {temp_filepath}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to clean up temporary file: {e}")

def create_fallback_response(filename: str, error_message: str) -> dict:
    """Create a fallback response when processing fails."""
    logger.info(f"🔄 Creating fallback response for {filename}")
    
    return {
        "message": "OCR fallback - processing failed",
        "error": error_message,
        "invoice_id": str(uuid.uuid4()),
        "filename": filename,
        "data": {
            "invoice_id": str(uuid.uuid4()),
            "supplier_name": "OCR Failed",
            "invoice_date": datetime.now().strftime("%Y-%m-%d"),
            "total_amount": 0.0,
            "subtotal": 0.0,
            "vat": 0.0,
            "vat_rate": 0.2,
            "total_incl_vat": 0.0,
            "confidence": 0.0,
            "manual_review": True,
            "line_items": []
        },
        "parsed_data": {
            "invoice_id": str(uuid.uuid4()),
            "supplier_name": "OCR Failed",
            "invoice_date": datetime.now().strftime("%Y-%m-%d"),
            "total_amount": 0.0,
            "subtotal": 0.0,
            "vat": 0.0,
            "vat_rate": 0.2,
            "total_incl_vat": 0.0,
            "confidence": 0.0,
            "manual_review": True,
            "line_items": []
        },
        "raw_ocr_text": "",
        "confidence": 0.0,
        "manual_review": True,
        "table_detected": False,
        "pages": [],
        "overall_confidence": 0.0
    }

def create_fallback_metadata() -> Dict[str, Any]:
    """Create a fallback metadata dictionary."""
    logger.warning("⚠️ Using fallback metadata due to OCR engine issues.")
    return {
        'supplier_name': 'Unknown',
        'invoice_number': 'Unknown',
        'invoice_date': datetime.now().strftime("%Y-%m-%d"),
        'total_amount': 0.0,
        'subtotal': 0.0,
        'vat': 0.0,
        'vat_rate': 20.0,
        'total_incl_vat': 0.0
    }

@router.get("/files")
def list_uploaded_files():
    """List all uploaded files with their metadata."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all invoices with their file information
        cursor.execute("""
            SELECT id, parent_pdf_filename, upload_timestamp, invoice_number, 
                   supplier_name, total_amount, status, confidence
            FROM invoices 
            ORDER BY upload_timestamp DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        files = []
        for row in rows:
            invoice_id, filename, upload_timestamp, invoice_number, supplier_name, total_amount, status, confidence = row
            
            files.append({
                "id": invoice_id,
                "filename": filename,
                "upload_timestamp": upload_timestamp,
                "invoice_number": invoice_number,
                "supplier_name": supplier_name,
                "total_amount": total_amount,
                "status": status,
                "confidence": confidence,
                "preview_url": f"/api/files/{invoice_id}/preview"
            })
        
        return {"files": files}
        
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/files/{document_id}/preview")
def preview_file(document_id: str):
    """Preview a specific uploaded file by document ID."""
    try:
        # Look up the file path in the invoices table
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT parent_pdf_filename FROM invoices WHERE id = ?", (document_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Document not found")
        
        filename = row[0]
        
        if not filename:
            raise HTTPException(status_code=404, detail="No file associated with this document")
        
        # Only allow certain extensions for preview
        allowed_exts = {".pdf", ".jpg", ".jpeg", ".png"}
        ext = Path(filename).suffix.lower()
        
        if ext not in allowed_exts:
            raise HTTPException(status_code=400, detail="File type not supported for preview")
        
        # Construct absolute path to the file
        abs_path = Path(UPLOAD_DIR) / filename
        
        if not abs_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        # Return the file as a response
        return FileResponse(
            str(abs_path), 
            media_type=None, 
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing file {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"} 

@router.get("/audit/last")
async def get_last_audit():
    """Development-only endpoint to inspect last upload audit."""
    try:
        return {
            "success": True,
            "audit": LAST_AUDIT,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/test-ocr")
async def test_ocr():
    """Test OCR engine directly"""
    try:
        from ocr.unified_ocr_engine import UnifiedOCREngine
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a simple test image
        img = Image.new('RGB', (400, 200), color='white')
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()
        draw.text((50, 50), "INVOICE", fill='black', font=font)
        draw.text((50, 80), "Supplier: Test Company", fill='black', font=font)
        draw.text((50, 110), "Total: $100.00", fill='black', font=font)
        
        # Save to temp file
        temp_path = "/tmp/test_ocr.png"
        img.save(temp_path)
        
        # Test OCR engine
        engine = UnifiedOCREngine()
        result = engine.process_document(temp_path)
        
        # Clean up
        os.remove(temp_path)
        
        return {
            "success": result.success,
            "supplier": result.supplier,
            "invoice_number": result.invoice_number,
            "total_amount": result.total_amount,
            "confidence": result.overall_confidence,
            "raw_text": result.raw_text,
            "word_count": result.word_count,
            "engine_used": result.engine_used
        }
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()} 