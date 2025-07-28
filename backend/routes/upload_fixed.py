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

# Import working OCR functions with detailed error handling
try:
    from backend.ocr.ocr_engine import run_ocr
    logger.debug("✅ run_ocr imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import run_ocr: {e}")
    run_ocr = None

try:
    from backend.ocr.parse_invoice import extract_invoice_metadata, extract_line_items
    logger.debug("✅ extract_invoice_metadata and extract_line_items imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import parse_invoice functions: {e}")
    extract_invoice_metadata = None
    extract_line_items = None

try:
    from backend.ocr.table_extractor import extract_table_data, extract_line_items_from_text
    logger.debug("✅ extract_table_data and extract_line_items_from_text imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import table_extractor functions: {e}")
    extract_table_data = None
    extract_line_items_from_text = None

# Check if all required functions are available
ENHANCED_OCR_AVAILABLE = all([run_ocr, extract_invoice_metadata, extract_line_items, extract_table_data])
if ENHANCED_OCR_AVAILABLE:
    logger.info("✅ Enhanced OCR pipeline available")
else:
    logger.warning("⚠️ Some OCR functions are missing - using fallback mode")

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

async def process_upload_with_timeout(filepath: str, filename: str, timeout_seconds: int = 30):
    """Process upload with timeout to prevent hanging."""
    logger.debug(f"🔄 Starting OCR processing for {filename} with {timeout_seconds}s timeout")
    logger.debug(f"📁 File path: {filepath}")
    
    try:
        # Check if run_ocr function is available
        if run_ocr is None:
            logger.error("❌ run_ocr function is not available")
            raise Exception("OCR engine not available")
        
        # Check if file exists
        if not os.path.exists(filepath):
            logger.error(f"❌ File not found: {filepath}")
            raise Exception(f"File not found: {filepath}")
        
        logger.debug(f"📊 File size: {os.path.getsize(filepath)} bytes")
        
        # Run OCR with timeout
        logger.debug("🔄 Calling run_ocr function...")
        ocr_result = await asyncio.wait_for(
            asyncio.to_thread(run_ocr, filepath),
            timeout=timeout_seconds
        )
        
        logger.debug(f"✅ OCR completed for {filename}")
        logger.debug(f"📝 OCR result keys: {list(ocr_result.keys()) if isinstance(ocr_result, dict) else 'Not a dict'}")
        
        return ocr_result
        
    except asyncio.TimeoutError:
        logger.error(f"❌ OCR processing timed out after {timeout_seconds}s for {filename}")
        raise HTTPException(status_code=408, detail=f"OCR processing timed out after {timeout_seconds} seconds")
    except Exception as e:
        logger.exception(f"❌ OCR processing failed for {filename}")
        logger.error(f"📋 Error details: {str(e)}")
        logger.error(f"📋 Error type: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")

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
        
        # Step 3: Run OCR with timeout
        logger.info("🔄 Step 3: Running OCR processing...")
        try:
            ocr_result = await process_upload_with_timeout(temp_filepath, file.filename)
            logger.info("✅ OCR processing completed")
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
        raw_text = ocr_result.get('raw_ocr_text', '')
        
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
            if extract_invoice_metadata and raw_text:
                metadata = extract_invoice_metadata(raw_text)
                logger.info(f"✅ Metadata extracted: {metadata}")
            else:
                metadata = create_fallback_metadata()
                logger.warning("⚠️ Using fallback metadata")
        except Exception as metadata_error:
            logger.warning(f"⚠️ Metadata extraction failed: {metadata_error}")
            metadata = create_fallback_metadata()
        
        # ✅ Enhanced line item extraction
        line_items = []
        try:
            if extract_line_items and table_data:
                line_items = extract_line_items(table_data)
                logger.info(f"✅ Line items extracted from table: {len(line_items)} items")
            elif extract_line_items_from_text and raw_text:
                # Fallback to text-based extraction
                line_items = extract_line_items_from_text(raw_text)
                logger.info(f"✅ Line items extracted from text: {len(line_items)} items")
        except Exception as line_items_error:
            logger.warning(f"⚠️ Line items extraction failed: {line_items_error}")
            line_items = []
        
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
        
        # Step 6: Calculate confidence and manual review flag
        logger.info("🔄 Step 6: Calculating confidence...")
        
        # ✅ Fix confidence calculation - ensure it's 0-100 scale
        overall_confidence = ocr_result.get('overall_confidence', 0.0)
        if overall_confidence > 1.0:
            # If confidence is already a percentage, cap at 100
            confidence = min(100.0, overall_confidence)
        else:
            # Convert decimal to percentage
            confidence = min(100.0, overall_confidence * 100)
        
        # ✅ Enhanced manual review logic
        manual_review = (
            confidence < 60.0 or 
            not line_items or 
            metadata.get('supplier_name') == 'Unknown' or
            metadata.get('total_amount', 0) == 0.0
        )
        
        logger.info(f"✅ Confidence calculated: {confidence:.1f}%, Manual review: {manual_review}")
        
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
        
        # Step 8: Prepare response
        logger.info("🔄 Step 8: Preparing response...")
        
        parsed_data = {
            "invoice_id": invoice_id,
            "supplier_name": metadata.get('supplier_name', 'Unknown'),
            "invoice_date": metadata.get('invoice_date', datetime.now().strftime("%Y-%m-%d")),
            "total_amount": metadata.get('total_amount', 0.0),
            "subtotal": metadata.get('subtotal', 0.0),
            "vat": metadata.get('vat', 0.0),
            "vat_rate": metadata.get('vat_rate', 20.0),
            "total_incl_vat": metadata.get('total_incl_vat', 0.0),
            "confidence": confidence,
            "manual_review": manual_review,
            "line_items": line_items
        }
        
        response = {
            "message": "Processing completed successfully" if not manual_review else "Processing completed with issues",
            "invoice_id": invoice_id,
            "filename": file.filename,
            "parsed_data": parsed_data,
            "raw_ocr_text": raw_text,
            "confidence": confidence,
            "manual_review": manual_review,
            "table_detected": len(table_data) > 0,
            "pages": ocr_result.get('pages', []),
            "overall_confidence": confidence
        }
        
        logger.info("✅ Upload process completed successfully")
        return response
        
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
        return create_fallback_response(file.filename, str(e))
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

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"} 