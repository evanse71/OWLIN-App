import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter()

# Define upload directories (same as upload.py)
UPLOAD_BASE = Path("data/uploads")
INVOICE_DIR = UPLOAD_BASE / "invoices"
DELIVERY_DIR = UPLOAD_BASE / "delivery_notes"

# Allowed file types
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

def is_valid_file(filename: str) -> bool:
    """Check if file has allowed extension"""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

def parse_invoice_dummy(file: UploadFile) -> Dict[str, Any]:
    """Dummy OCR parsing function - returns mock data for now"""
    # This will be replaced with real OCR logic later
    return {
        "document_type": "invoice",
        "supplier_name": "Sample Supplier Ltd",
        "invoice_number": "INV-2024-001",
        "invoice_date": "2024-01-15",
        "due_date": "2024-02-15",
        "total_amount": 1250.00,
        "currency": "USD",
        "line_items": [
            {"description": "Product A", "quantity": 2, "unit_price": 500.00, "total": 1000.00},
            {"description": "Service B", "quantity": 1, "unit_price": 250.00, "total": 250.00}
        ],
        "confidence_score": 0.95,
        "processing_time_ms": 1500
    }

def parse_delivery_note_dummy(file: UploadFile) -> Dict[str, Any]:
    """Dummy OCR parsing function for delivery notes"""
    return {
        "document_type": "delivery_note",
        "supplier_name": "Sample Supplier Ltd",
        "delivery_note_number": "DN-2024-001",
        "delivery_date": "2024-01-15",
        "order_number": "PO-2024-001",
        "items": [
            {"description": "Product A", "quantity": 2, "received": 2},
            {"description": "Product B", "quantity": 1, "received": 1}
        ],
        "total_items": 3,
        "confidence_score": 0.92,
        "processing_time_ms": 1200
    }

@router.post("/ocr/parse")
async def parse_document(file: UploadFile = File(...)):
    """Parse uploaded document using OCR"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    if not is_valid_file(file.filename):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    try:
        # Determine document type based on filename or content
        # For now, we'll use a simple heuristic
        filename_lower = file.filename.lower()
        
        if any(keyword in filename_lower for keyword in ['invoice', 'inv', 'bill']):
            parsed_data = parse_invoice_dummy(file)
        elif any(keyword in filename_lower for keyword in ['delivery', 'dn', 'receipt']):
            parsed_data = parse_delivery_note_dummy(file)
        else:
            # Default to invoice parsing
            parsed_data = parse_invoice_dummy(file)
        
        # Add metadata
        result = {
            "success": True,
            "original_filename": file.filename,
            "file_size": file.size,
            "processed_at": datetime.now().isoformat(),
            "parsed_data": parsed_data
        }
        
        return JSONResponse(result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR parsing failed: {str(e)}")

@router.post("/ocr/parse-batch")
async def parse_documents_batch(files: List[UploadFile] = File(...)):
    """Parse multiple documents using OCR"""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    results = []
    
    for file in files:
        if not file.filename:
            continue
            
        if not is_valid_file(file.filename):
            results.append({
                "filename": file.filename,
                "success": False,
                "error": f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            })
            continue
        
        try:
            # Use the same parsing logic as single file
            filename_lower = file.filename.lower()
            
            if any(keyword in filename_lower for keyword in ['invoice', 'inv', 'bill']):
                parsed_data = parse_invoice_dummy(file)
            elif any(keyword in filename_lower for keyword in ['delivery', 'dn', 'receipt']):
                parsed_data = parse_delivery_note_dummy(file)
            else:
                parsed_data = parse_invoice_dummy(file)
            
            results.append({
                "filename": file.filename,
                "success": True,
                "file_size": file.size,
                "processed_at": datetime.now().isoformat(),
                "parsed_data": parsed_data
            })
            
        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e)
            })
    
    return JSONResponse({
        "success": True,
        "total_files": len(files),
        "processed_files": len([r for r in results if r["success"]]),
        "failed_files": len([r for r in results if not r["success"]]),
        "results": results
    })

@router.get("/ocr/status")
async def get_ocr_status():
    """Get OCR service status"""
    return {
        "status": "operational",
        "version": "1.0.0",
        "supported_formats": list(ALLOWED_EXTENSIONS),
        "timestamp": datetime.now().isoformat()
    } 