import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from .pairing import match_documents
from .ocr import parse_with_ocr

router = APIRouter()

# Define upload directories
UPLOAD_BASE = Path("data/uploads")
INVOICE_DIR = UPLOAD_BASE / "invoices"
DELIVERY_DIR = UPLOAD_BASE / "delivery_notes"

# Create directories if they don't exist
INVOICE_DIR.mkdir(parents=True, exist_ok=True)
DELIVERY_DIR.mkdir(parents=True, exist_ok=True)

# Allowed file types
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

# In-memory store for parsed metadata (for demo; use DB in production)
doc_store = {
    'invoices': [],  # list of dicts: {filename, parsed_data, status}
    'delivery_notes': []
}

def is_valid_file(filename: str) -> bool:
    """Check if file has allowed extension"""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

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
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    if not is_valid_file(file.filename):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    try:
        filename = save_file_with_timestamp(file, INVOICE_DIR)
        # Rewind file for parsing
        file.file.seek(0)
        parsed = await parse_with_ocr(file)
        invoice_data = parsed['parsed_data']
        status = 'unmatched'
        matched_delivery = None
        # Try to match with existing delivery notes
        for d in doc_store['delivery_notes']:
            if match_documents(invoice_data, d['parsed_data']):
                status = 'matched'
                matched_delivery = d['filename']
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
            "matched_delivery": matched_delivery
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/upload/delivery")
async def upload_delivery(file: UploadFile = File(...)):
    """Upload delivery note file, parse, and try to match with invoices"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    if not is_valid_file(file.filename):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    try:
        filename = save_file_with_timestamp(file, DELIVERY_DIR)
        # Rewind file for parsing
        file.file.seek(0)
        parsed = await parse_with_ocr(file)
        delivery_data = parsed['parsed_data']
        status = 'unmatched'
        matched_invoice = None
        # Try to match with existing invoices
        for inv in doc_store['invoices']:
            if match_documents(inv['parsed_data'], delivery_data):
                status = 'matched'
                matched_invoice = inv['filename']
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
            "matched_invoice": matched_invoice
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