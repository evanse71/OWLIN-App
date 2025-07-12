import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import pytesseract
from PIL import Image
import io
from .ocr_utils import detect_document_type

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

def extract_invoice_fields(text_lines: list[str]) -> dict:
    # Basic keyword-driven heuristics
    supplier_name = text_lines[0] if text_lines else ''
    invoice_number = ''
    invoice_date = ''
    total_amount = ''
    currency = ''

    for line in text_lines:
        l = line.lower()
        if 'invoice' in l and any(char.isdigit() for char in l) and not invoice_number:
            invoice_number = line
        if 'date' in l and any(char.isdigit() for char in l) and not invoice_date:
            invoice_date = line
        if any(s in l for s in ['total', 'amount', 'balance']) and any(char.isdigit() for char in l) and not total_amount:
            total_amount = line
        if any(sym in l for sym in ['£', '$', '€']):
            currency = sym = next((s for s in ['£', '$', '€'] if s in l), '')

    return {
        'supplier_name': supplier_name.strip(),
        'invoice_number': invoice_number.strip(),
        'invoice_date': invoice_date.strip(),
        'total_amount': total_amount.strip(),
        'currency': currency.strip()
    }

async def parse_invoice_with_ocr(file: UploadFile, threshold: int = 70) -> dict:
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    lines = []
    current_line = ''
    last_line_num = -1

    for i in range(len(data['text'])):
        try:
            conf = int(data['conf'][i])
        except Exception:
            conf = 0
        word = data['text'][i].strip()
        line_num = data['line_num'][i]

        if conf < threshold or not word:
            continue

        if line_num != last_line_num and current_line:
            lines.append(current_line.strip())
            current_line = word
            last_line_num = line_num
        else:
            current_line += ' ' + word

    if current_line:
        lines.append(current_line.strip())

    parsed_fields = extract_invoice_fields(lines)
    # Join all lines for document type detection
    full_text = '\n'.join(lines)
    doc_type = detect_document_type(full_text)
    return {
        'parsed_data': parsed_fields,
        'raw_lines': lines,
        'document_type': doc_type
    }

@router.post("/ocr/parse")
async def parse_document(file: UploadFile = File(...), confidence_threshold: int = 70):
    """Parse uploaded document using OCR"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    if not is_valid_file(file.filename):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    try:
        filename_lower = file.filename.lower()
        # Always run OCR and detect type
        parsed_data = await parse_invoice_with_ocr(file, threshold=confidence_threshold)
        result = {
            "success": True,
            "original_filename": file.filename,
            "file_size": file.size,
            "processed_at": datetime.now().isoformat(),
            "parsed_data": parsed_data['parsed_data'],
            "raw_lines": parsed_data['raw_lines'],
            "document_type": parsed_data['document_type']
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
                parsed_data = await parse_invoice_with_ocr(file) # No threshold parameter for batch
            else:
                parsed_data = {'parsed_data': {}, 'raw_lines': []}
            
            results.append({
                "filename": file.filename,
                "success": True,
                "file_size": file.size,
                "processed_at": datetime.now().isoformat(),
                "parsed_data": parsed_data['parsed_data'],
                "raw_lines": parsed_data['raw_lines']
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