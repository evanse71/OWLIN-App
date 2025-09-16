#!/usr/bin/env python3
"""
Fixed upload route for Owlin invoice management system.
Implements async-safe OCR processing with background tasks.
"""

import sqlite3
import uuid
import os
import traceback
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import shutil
import re
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dev audit store (last upload)
LAST_AUDIT: Dict[str, Any] = {}

# Configuration
UPLOAD_DIR = "data/uploads"
LOGS_DIR = "data/logs"

# Ensure directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

router = APIRouter()

def validate_file(file: UploadFile):
    """Validate uploaded file."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Check file extension
    allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif'}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_ext}")
    
    # Check file size (10MB limit)
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

def get_timeout_for_file(filepath: str) -> int:
    """Get OCR timeout based on file characteristics."""
    try:
        if filepath.lower().endswith('.pdf'):
            # PDFs might take longer
            return 60
        else:
            # Images are usually faster
            return 30
    except:
        return 30

@router.post("/upload-async")
async def upload_invoice(file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    """Upload and process invoice with async-safe background processing."""
    logger.info(f"🚀 Starting invoice upload process for: {file.filename}")
    
    # Diagnostics tracing
    run_id = str(uuid.uuid4())
    temp_filepath = None
    temp_doc_id = None
    
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
        temp_doc_id = temp_filename
        
        # Save file
        logger.debug(f"📁 Saving to: {temp_filepath}")
        with open(temp_filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"✅ File saved as: {temp_filename}")
        
        # Step 3: Create database stub
        logger.info("🔄 Step 3: Creating database stub...")
        doc_id = create_document_stub(temp_filepath, file.filename, temp_doc_id)
        logger.info(f"✅ Database stub created with ID: {doc_id}")
        
        # Step 4: Queue OCR processing
        logger.info("🔄 Step 4: Queuing OCR processing...")
        timeout_seconds = get_timeout_for_file(temp_filepath)
        background_tasks.add_task(process_document_background, doc_id, temp_filepath, file.filename, timeout_seconds, run_id)
        logger.info("✅ OCR processing queued for background execution")
        
        # Return immediately with document ID
        return {
            "document_id": doc_id,
            "status": "queued",
            "message": "Document uploaded and queued for processing",
            "filename": file.filename
        }
        
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
        return fallback
    finally:
        # Clean up temporary file
        if temp_filepath and os.path.exists(temp_filepath):
            try:
                os.remove(temp_filepath)
                logger.debug(f"✅ Temporary file cleaned up: {temp_filepath}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to clean up temporary file: {e}")

def create_document_stub(filepath: str, filename: str, temp_doc_id: str) -> str:
    """Create a database stub for the document and return the document ID."""
    doc_id = str(uuid.uuid4())
    
    try:
        con = sqlite3.connect("data/owlin.db")
        cur = con.cursor()
        
        # Insert document record
        cur.execute("""
            INSERT INTO documents (id, filename, file_path, type, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """, (doc_id, filename, filepath, 'invoice', 'queued'))
        
        # Insert invoice record
        invoice_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO invoices (id, document_id, supplier, invoice_date, total_value, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """, (invoice_id, doc_id, 'Unknown', None, 0.0, 'queued'))
        
        con.commit()
        con.close()
        
        logger.info(f"✅ Database stub created: doc_id={doc_id}, invoice_id={invoice_id}")
        return doc_id
        
    except Exception as e:
        logger.error(f"❌ Failed to create database stub: {e}")
        raise

def process_document_background(doc_id: str, filepath: str, filename: str, timeout_seconds: int, run_id: str):
    """Background task to process document OCR and parsing."""
    logger.info(f"🔄 Background processing started for document {doc_id}")
    
    try:
        # Process OCR synchronously (no event loop issues in background thread)
        ocr_result = process_upload_with_timeout_sync(filepath, filename, timeout_seconds)
        
        # Extract metadata and line items
        raw_text = ocr_result.get('raw_ocr_text') or ocr_result.get('raw_text', '')
        metadata = extract_metadata_from_text(raw_text)
        line_items = extract_line_items_from_text(raw_text)
        
        # Update database with results
        update_document_with_results(doc_id, ocr_result, metadata, line_items)
        
        logger.info(f"✅ Background processing completed for document {doc_id}")
        
    except Exception as e:
        logger.error(f"❌ Background processing failed for document {doc_id}: {e}")
        # Update document status to failed
        update_document_status(doc_id, 'failed', str(e))

def process_upload_with_timeout_sync(filepath: str, filename: str, timeout_seconds: int):
    """Synchronous version of OCR processing for background tasks."""
    try:
        # Simple OCR simulation for now - in production this would use real OCR
        logger.info(f"🔄 Processing OCR for {filename}")
        
        # Simulate OCR processing
        import time
        time.sleep(2)  # Simulate processing time
        
        # Return mock OCR result
        return {
            "overall_confidence": 0.85,
            "raw_text": f"Mock OCR text for {filename}\nInvoice Number: INV-001\nSupplier: Test Supplier\nDate: 2024-01-15\nTotal: £123.45",
            "pages": [{"text": f"Mock page text for {filename}", "confidence": 0.85}]
        }
        
    except Exception as e:
        logger.error(f"❌ Sync OCR processing failed: {e}")
        return {"error": str(e), "overall_confidence": 0.0, "raw_text": ""}

def extract_metadata_from_text(text: str) -> dict:
    """Extract metadata from OCR text."""
    metadata = {
        "supplier": "Unknown",
        "invoice_date": None,
        "total_value": 0.0,
        "invoice_number": "Unknown"
    }
    
    try:
        # Extract supplier (look for common patterns)
        supplier_patterns = [
            r'(?:WILD HORSE BREWING CO LTD|RED DRAGON DISPENSE LIMITED|SNOWDONIA HOSPITALITY)',
            r'([A-Za-z\s&\.]+)\s*(?:Ltd|Limited|Inc|Corp)',
        ]
        
        for pattern in supplier_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata["supplier"] = match.group(1).strip()
                break
        
        # Extract date
        date_patterns = [
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    date_str = match.group(1)
                    # Try to parse the date
                    for fmt in ['%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                        try:
                            metadata["invoice_date"] = datetime.strptime(date_str, fmt).date().isoformat()
                            break
                        except ValueError:
                            continue
                except:
                    pass
        
        # Extract total
        total_patterns = [
            r'total[:\s]*[£$€]?([\d,]+\.?\d*)',
            r'amount[:\s]*[£$€]?([\d,]+\.?\d*)',
        ]
        
        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    total_str = match.group(1).replace(',', '')
                    metadata["total_value"] = float(total_str)
                    break
                except:
                    pass
        
        # Extract invoice number
        inv_patterns = [
            r'invoice[:\s#]*([A-Za-z0-9\-]+)',
            r'inv[:\s#]*([A-Za-z0-9\-]+)',
        ]
        
        for pattern in inv_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata["invoice_number"] = match.group(1).strip()
                break
                
    except Exception as e:
        logger.warning(f"⚠️ Metadata extraction failed: {e}")
    
    return metadata

def extract_line_items_from_text(text: str) -> list:
    """Extract line items from OCR text."""
    line_items = []
    
    try:
        # Simple line item extraction - look for patterns like "item qty price total"
        lines = text.split('\n')
        for line in lines:
            # Look for lines with numbers that might be line items
            if re.search(r'\d+\.?\d*', line) and len(line.strip()) > 10:
                # Basic parsing - in a real implementation this would be more sophisticated
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        # Try to extract quantity, price, total
                        qty = 1.0
                        price = 0.0
                        total = 0.0
                        
                        # Look for numbers in the line
                        numbers = re.findall(r'\d+\.?\d*', line)
                        if len(numbers) >= 2:
                            price = float(numbers[-2])  # Second to last number
                            total = float(numbers[-1])  # Last number
                            qty = total / price if price > 0 else 1.0
                        
                        line_items.append({
                            "description": line.strip(),
                            "quantity": qty,
                            "unit_price": price,
                            "total": total,
                            "confidence": 0.8
                        })
                    except:
                        pass
    except Exception as e:
        logger.warning(f"⚠️ Line items extraction failed: {e}")
    
    return line_items

def update_document_with_results(doc_id: str, ocr_result: dict, metadata: dict, line_items: list):
    """Update document and invoice records with OCR results."""
    try:
        con = sqlite3.connect("data/owlin.db")
        cur = con.cursor()
        
        # Update document record
        confidence = float(ocr_result.get('overall_confidence', 0.0) or 0.0)
        raw_text = ocr_result.get('raw_ocr_text') or ocr_result.get('raw_text', '')
        
        cur.execute("""
            UPDATE documents 
            SET status = ?, ocr_confidence = ?, raw_text = ?, updated_at = datetime('now')
            WHERE id = ?
        """, ('processed', confidence, raw_text, doc_id))
        
        # Update invoice record
        cur.execute("""
            UPDATE invoices 
            SET supplier = ?, invoice_date = ?, total_value = ?, status = ?, updated_at = datetime('now')
            WHERE document_id = ?
        """, (metadata['supplier'], metadata['invoice_date'], metadata['total_value'], 'scanned', doc_id))
        
        # Insert line items
        invoice_id = cur.execute("SELECT id FROM invoices WHERE document_id = ?", (doc_id,)).fetchone()[0]
        
        for item in line_items:
            item_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO invoice_line_items (id, invoice_id, description, quantity, unit_price, total, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (item_id, invoice_id, item['description'], item['quantity'], item['unit_price'], item['total'], item['confidence']))
        
        con.commit()
        con.close()
        
        logger.info(f"✅ Database updated with results for document {doc_id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to update database with results: {e}")
        update_document_status(doc_id, 'failed', str(e))

def update_document_status(doc_id: str, status: str, error_message: str = None):
    """Update document status."""
    try:
        con = sqlite3.connect("data/owlin.db")
        cur = con.cursor()
        
        cur.execute("""
            UPDATE documents 
            SET status = ?, updated_at = datetime('now')
            WHERE id = ?
        """, (status, doc_id))
        
        cur.execute("""
            UPDATE invoices 
            SET status = ?, updated_at = datetime('now')
            WHERE document_id = ?
        """, (status, doc_id))
        
        con.commit()
        con.close()
        
        logger.info(f"✅ Document {doc_id} status updated to {status}")
        
    except Exception as e:
        logger.error(f"❌ Failed to update document status: {e}")

def create_fallback_response(filename: str, error_message: str) -> dict:
    """Create a fallback response when processing fails."""
    logger.info(f"🔄 Creating fallback response for {filename}")
    
    return {
        "document_id": str(uuid.uuid4()),
        "status": "failed",
        "message": f"Processing failed: {error_message}",
        "filename": filename,
        "error": error_message
    }

@router.get("/files")
def list_uploaded_files():
    """List all uploaded files with their metadata."""
    try:
        con = sqlite3.connect("data/owlin.db")
        cur = con.cursor()
        
        # Get all documents with their invoice data
        cur.execute("""
            SELECT d.id, d.filename, d.status, d.created_at, d.ocr_confidence,
                   i.supplier, i.invoice_date, i.total_value, i.status as invoice_status
            FROM documents d
            LEFT JOIN invoices i ON d.id = i.document_id
            ORDER BY d.created_at DESC
        """)
        
        files = []
        for row in cur.fetchall():
            files.append({
                "document_id": row[0],
                "filename": row[1],
                "status": row[2],
                "created_at": row[3],
                "ocr_confidence": row[4],
                "supplier": row[5],
                "invoice_date": row[6],
                "total_value": row[7],
                "invoice_status": row[8]
            })
        
        con.close()
        return {"files": files}
        
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Upload service is running"}

@router.get("/audit/last")
async def get_last_audit():
    """Development-only endpoint to inspect last upload audit."""
    return LAST_AUDIT
