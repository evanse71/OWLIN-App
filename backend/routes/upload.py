import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from .pairing import match_documents
from .ocr import parse_with_ocr
# from matching import match_documents as score_match  # Commented out to fix import issue
import sqlite3

def score_match(invoice_data, delivery_data):
    """Placeholder function for matching - returns basic match result"""
    return {
        'matched': False,
        'confidence': 0.0,
        'reason': 'Matching temporarily disabled'
    }

router = APIRouter()

# Define upload directories
UPLOAD_BASE = Path("data/uploads")
INVOICE_DIR = UPLOAD_BASE / "invoices"
DELIVERY_DIR = UPLOAD_BASE / "delivery_notes"
RECEIPT_DIR = UPLOAD_BASE / "receipts"
DOCUMENTS_DIR = UPLOAD_BASE / "documents"  # General documents directory

# Create directories if they don't exist
INVOICE_DIR.mkdir(parents=True, exist_ok=True)
DELIVERY_DIR.mkdir(parents=True, exist_ok=True)
RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

# Allowed file types
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

# File size limits (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes

# In-memory store for parsed metadata (for demo; use DB in production)
doc_store = {
    'invoices': [
        {
            'filename': 'sample_invoice_1.pdf',
            'parsed_data': {
                'supplier_name': 'ABC Corporation',
                'invoice_number': 'INV-2024-001',
                'total_amount': '1500.00',
                'invoice_date': '2024-01-15',
                'currency': 'GBP'
            },
            'status': 'unmatched',
            'uploaded_at': '2024-01-15T10:00:00'
        },
        {
            'filename': 'sample_invoice_2.pdf',
            'parsed_data': {
                'supplier_name': 'XYZ Company',
                'invoice_number': 'INV-2024-002',
                'total_amount': '2500.00',
                'invoice_date': '2024-01-16',
                'currency': 'GBP'
            },
            'status': 'unmatched',
            'uploaded_at': '2024-01-16T10:00:00'
        }
    ],
    'delivery_notes': [
        {
            'filename': 'sample_delivery_1.pdf',
            'parsed_data': {
                'supplier_name': 'ABC Corporation',
                'delivery_note_number': 'DN-2024-001',
                'delivery_date': '2024-01-15',
                'total_items': '3 items'
            },
            'status': 'unmatched',
            'uploaded_at': '2024-01-15T09:00:00'
        }
    ]
}

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
    """Save file with timestamp prefix to avoid conflicts"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    file_path = directory / filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return filename

@router.post("/upload/invoice")
async def upload_invoice(file: UploadFile = File(...)):
    """Upload invoice file, parse, and try to match with delivery notes"""
    # Validate file
    validate_file(file)

    try:
        filename = save_file_with_timestamp(file, INVOICE_DIR)
        # Rewind file for parsing
        file.file.seek(0)
        parsed = await parse_with_ocr(file)
        invoice_data = parsed['parsed_data']
        document_type = parsed.get('document_type')
        confidence_score = parsed.get('confidence_score')
        status = 'unmatched'
        matched_delivery = None
        matched_delivery_data = None
        match_result = None
        # Try to match with existing delivery notes
        for d in doc_store['delivery_notes']:
            match_result = score_match(invoice_data, d['parsed_data'])
            if match_result['matched']:
                status = 'matched'
                matched_delivery = d['filename']
                matched_delivery_data = d['parsed_data']
                d['status'] = 'matched'
                d['matched_invoice'] = filename
                break
        doc_store['invoices'].append({
            'filename': filename,
            'parsed_data': invoice_data,
            'status': status,
            'matched_delivery': matched_delivery
        })
        return JSONResponse({
            "success": True,
            "filename": filename,
            "original_name": file.filename,
            "uploaded_at": datetime.now().isoformat(),
            "file_size": file.size,
            "status": status,
            "document_type": document_type,
            "confidence_score": confidence_score,
            "parsed_data": invoice_data,
            "matched_delivery": {
                "filename": matched_delivery,
                "parsed_data": matched_delivery_data
            } if matched_delivery else None,
            "match_score": match_result['match_score'] if match_result else None,
            "match_breakdown": match_result['breakdown'] if match_result else None
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/upload/delivery")
async def upload_delivery(file: UploadFile = File(...)):
    """Upload delivery note file, parse, and try to match with invoices"""
    # Validate file
    validate_file(file)

    try:
        filename = save_file_with_timestamp(file, DELIVERY_DIR)
        # Rewind file for parsing
        file.file.seek(0)
        parsed = await parse_with_ocr(file)
        delivery_data = parsed['parsed_data']
        document_type = parsed.get('document_type')
        confidence_score = parsed.get('confidence_score')
        status = 'unmatched'
        matched_invoice = None
        matched_invoice_data = None
        match_result = None
        # Try to match with existing invoices
        for inv in doc_store['invoices']:
            match_result = score_match(inv['parsed_data'], delivery_data)
            if match_result['matched']:
                status = 'matched'
                matched_invoice = inv['filename']
                matched_invoice_data = inv['parsed_data']
                inv['status'] = 'matched'
                inv['matched_delivery'] = filename
                break
        doc_store['delivery_notes'].append({
            'filename': filename,
            'parsed_data': delivery_data,
            'status': status,
            'matched_invoice': matched_invoice
        })
        return JSONResponse({
            "success": True,
            "filename": filename,
            "original_name": file.filename,
            "uploaded_at": datetime.now().isoformat(),
            "file_size": file.size,
            "status": status,
            "document_type": document_type,
            "confidence_score": confidence_score,
            "parsed_data": delivery_data,
            "matched_invoice": {
                "filename": matched_invoice,
                "parsed_data": matched_invoice_data
            } if matched_invoice else None,
            "match_score": match_result['match_score'] if match_result else None,
            "match_breakdown": match_result['breakdown'] if match_result else None
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/upload/receipt")
async def upload_receipt(file: UploadFile = File(...)):
    """Upload receipt file"""
    # Validate file
    validate_file(file)

    try:
        filename = save_file_with_timestamp(file, RECEIPT_DIR)
        return JSONResponse({
            "success": True,
            "filename": filename,
            "uploaded_at": datetime.now().isoformat()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/upload/document")
async def upload_document(file: UploadFile = File(...)):
    """Upload any document file (classification will be done separately)"""
    # Validate file
    validate_file(file)
    
    try:
        filename = save_file_with_timestamp(file, DOCUMENTS_DIR)
        return JSONResponse({
            "success": True,
            "filename": filename,
            "original_name": file.filename,
            "uploaded_at": datetime.now().isoformat(),
            "file_size": file.size
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/files/invoices")
async def list_invoice_files():
    """List all uploaded invoice files"""
    files = []
    for file_path in INVOICE_DIR.glob("*"):
        if file_path.is_file():
            files.append({
                "filename": file_path.name,
                "size": file_path.stat().st_size,
                "uploaded_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            })
    return {"files": files}

@router.get("/files/delivery")
async def list_delivery_files():
    """List all uploaded delivery note files"""
    files = []
    for file_path in DELIVERY_DIR.glob("*"):
        if file_path.is_file():
            files.append({
                "filename": file_path.name,
                "size": file_path.stat().st_size,
                "uploaded_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            })
    return {"files": files} 

DB_PATH = "data/owlin.db"
UPLOADS_DIR = "data/uploads/"

@router.get("/files/{document_id}/preview")
def preview_file(document_id: str):
    # Look up the file path in the uploaded_files table
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM uploaded_files WHERE id = ?", (document_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    file_path = row[0]
    # Only allow certain extensions
    allowed_exts = {".pdf", ".jpg", ".jpeg", ".png"}
    import os
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail="File type not supported for preview")
    abs_path = os.path.join(UPLOADS_DIR, os.path.basename(file_path))
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(abs_path, media_type=None, filename=os.path.basename(file_path)) 