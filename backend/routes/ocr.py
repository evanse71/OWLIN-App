import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import pytesseract
from PIL import Image
import io
import numpy as np
import cv2
from .ocr_utils import detect_document_type, preprocess_image
import tempfile
import re

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

def extract_delivery_note_fields(text_lines: list[str]) -> dict:
    supplier_name = text_lines[0] if text_lines else ''
    delivery_note_number = ''
    delivery_date = ''
    delivered_by = ''
    signed_by = ''
    items = []
    for line in text_lines:
        l = line.lower()
        if ('delivery note' in l or 'dn' in l) and any(char.isdigit() for char in l) and not delivery_note_number:
            delivery_note_number = line
        if 'date' in l and any(char.isdigit() for char in l) and not delivery_date:
            delivery_date = line
        if 'delivered by' in l and not delivered_by:
            delivered_by = line
        if 'signed by' in l and not signed_by:
            signed_by = line
        # Heuristic: lines with quantities and items
        if any(word in l for word in ['item', 'product', 'description']) or (any(char.isdigit() for char in l) and len(l.split()) > 2):
            items.append(line)
    return {
        'supplier_name': supplier_name.strip(),
        'delivery_note_number': delivery_note_number.strip(),
        'delivery_date': delivery_date.strip(),
        'delivered_by': delivered_by.strip(),
        'signed_by': signed_by.strip(),
        'items': items
    }

def parse_receipt_date(text: str) -> str:
    # Try to find a date in common formats
    date_patterns = [
        r"\b\d{2}/\d{2}/\d{4}\b",  # 31/12/2023
        r"\b\d{2}-\d{2}-\d{4}\b",  # 31-12-2023
        r"\b\d{4}-\d{2}-\d{2}\b",  # 2023-12-31
        r"\b\d{2} [A-Za-z]{3,9} \d{4}\b",  # 31 December 2023
        r"\b\d{2}/\d{2}/\d{2}\b",  # 31/12/23
    ]
    for pat in date_patterns:
        m = re.search(pat, text)
        if m:
            return m.group(0)
    return ""

def parse_receipt_total(text: str) -> str:
    # Look for lines like 'Total: £12.50' or 'TOTAL 12.50'
    total_patterns = [
        r"total[^\d]*(£|\$|€)?\s*([\d,.]+)",
        r"(£|\$|€)\s*([\d,.]+)\s*total"
    ]
    for pat in total_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(0)
    return ""

def parse_receipt_store(lines: list) -> str:
    # Heuristic: first line with large text or all-caps
    for line in lines:
        if line.isupper() and len(line) > 3:
            return line.strip()
        if len(line) > 10 and sum(1 for c in line if c.isupper()) > 3:
            return line.strip()
    return lines[0] if lines else ""

def parse_receipt_items(lines: list) -> list:
    # Heuristic: lines between 'items' and 'total' or lines with price at end
    items = []
    for line in lines:
        if re.search(r"\b\d+\.\d{2}\b", line):
            items.append(line.strip())
    return items

async def parse_with_ocr(file: UploadFile, threshold: int = 70) -> dict:
    contents = await file.read()
    # Save to a temp file for OpenCV
    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
        tmp.write(contents)
        tmp_path = tmp.name
    try:
        preprocessed = preprocess_image(tmp_path)
        pil_for_ocr = Image.fromarray(preprocessed)
        data = pytesseract.image_to_data(pil_for_ocr, output_type=pytesseract.Output.DICT)
    finally:
        os.remove(tmp_path)
    lines = []
    confidences = []
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
        confidences.append(conf)
        if line_num != last_line_num and current_line:
            lines.append(current_line.strip())
            current_line = word
            last_line_num = line_num
        else:
            current_line += ' ' + word
    if current_line:
        lines.append(current_line.strip())
    full_text = '\n'.join(lines)
    doc_type = detect_document_type(full_text)
    if doc_type == 'invoice':
        parsed_fields = extract_invoice_fields(lines)
    elif doc_type == 'delivery_note':
        parsed_fields = extract_delivery_note_fields(lines)
    else:
        parsed_fields = {}
    avg_conf = int(np.mean(confidences)) if confidences else 0
    return {
        'parsed_data': parsed_fields,
        'raw_lines': lines,
        'document_type': doc_type,
        'confidence_score': avg_conf
    }

async def parse_receipt(file: UploadFile, threshold: int = 70) -> dict:
    import cv2
    import numpy as np
    import pytesseract
    from PIL import Image
    import io
    contents = await file.read()
    pil_image = Image.open(io.BytesIO(contents)).convert("RGB")
    cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    # Preprocessing: grayscale, blur, threshold
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Optionally deskew (not implemented here)
    pil_for_ocr = Image.fromarray(thresh)
    custom_config = '--psm 11'
    data = pytesseract.image_to_data(pil_for_ocr, output_type=pytesseract.Output.DICT, config=custom_config)
    lines = []
    confidences = []
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
        confidences.append(conf)
        if line_num != last_line_num and current_line:
            lines.append(current_line.strip())
            current_line = word
            last_line_num = line_num
        else:
            current_line += ' ' + word
    if current_line:
        lines.append(current_line.strip())
    full_text = '\n'.join(lines)
    total_amount = parse_receipt_total(full_text)
    purchase_date = parse_receipt_date(full_text)
    store_name = parse_receipt_store(lines)
    items = parse_receipt_items(lines)
    avg_conf = int(np.mean(confidences)) if confidences else 0
    return {
        'total_amount': total_amount,
        'purchase_date': purchase_date,
        'store_name': store_name,
        'items': items,
        'raw_text': full_text,
        'confidence_score': avg_conf
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
        parsed_data = await parse_with_ocr(file, threshold=confidence_threshold)
        result = {
            "document_type": parsed_data['document_type'],
            "parsed_data": parsed_data['parsed_data'],
            "confidence_score": parsed_data['confidence_score'],
            "raw_lines": parsed_data['raw_lines'],
            "success": True,
            "original_filename": file.filename,
            "file_size": file.size,
            "processed_at": datetime.now().isoformat()
        }
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR parsing failed: {str(e)}")

@router.post("/ocr/parse_receipt")
async def parse_receipt_document(file: UploadFile = File(...), confidence_threshold: int = 70):
    """Parse uploaded receipt using OCR"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    if not is_valid_file(file.filename):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    try:
        parsed_data = await parse_receipt(file, threshold=confidence_threshold)
        result = {
            "total_amount": parsed_data['total_amount'],
            "purchase_date": parsed_data['purchase_date'],
            "store_name": parsed_data['store_name'],
            "items": parsed_data['items'],
            "raw_text": parsed_data['raw_text'],
            "confidence_score": parsed_data['confidence_score'],
            "success": True,
            "original_filename": file.filename,
            "file_size": file.size,
            "processed_at": datetime.now().isoformat()
        }
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Receipt parsing failed: {str(e)}")

@router.get("/ocr/status")
async def get_ocr_status():
    """Get OCR service status"""
    return {
        "status": "operational",
        "version": "1.0.0",
        "supported_formats": list(ALLOWED_EXTENSIONS),
        "timestamp": datetime.now().isoformat()
    } 