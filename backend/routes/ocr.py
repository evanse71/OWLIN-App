import os
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Define upload directories (same as upload.py)
UPLOAD_BASE = Path("data/uploads")
INVOICE_DIR = UPLOAD_BASE / "invoices"
DELIVERY_DIR = UPLOAD_BASE / "delivery_notes"

# Allowed file types
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

# File size limits (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes

# Batch processing limits
MAX_FILES_PER_REQUEST = 5

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

def safe_extract_text(text: str, pattern: str, default: str = "Unknown") -> str:
    """Safely extract text using regex pattern"""
    try:
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else default
    except Exception as e:
        logger.warning(f"Failed to extract text with pattern {pattern}: {e}")
        return default

def safe_parse_float(text: str, default: float = 0.0) -> float:
    """Safely parse float from text"""
    try:
        # Remove currency symbols and non-numeric characters except decimal point
        cleaned = re.sub(r'[^\d.]', '', text)
        if cleaned:
            return float(cleaned)
        return default
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to parse float from '{text}': {e}")
        return default

def safe_parse_date(text: str, default: str = "Unknown") -> str:
    """Safely parse date from text"""
    try:
        # Common date patterns
        date_patterns = [
            r"\b(\d{2}/\d{2}/\d{4})\b",  # 31/12/2023
            r"\b(\d{2}-\d{2}-\d{4})\b",  # 31-12-2023
            r"\b(\d{4}-\d{2}-\d{2})\b",  # 2023-12-31
            r"\b(\d{2} [A-Za-z]{3,9} \d{4})\b",  # 31 December 2023
            r"\b(\d{2}/\d{2}/\d{2})\b",  # 31/12/23
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return default
    except Exception as e:
        logger.warning(f"Failed to parse date from '{text}': {e}")
        return default

def extract_invoice_fields(text_lines: list[str]) -> dict:
    """Extract invoice fields with comprehensive error handling"""
    logger.info(f"Extracting invoice fields from {len(text_lines)} lines")
    logger.debug(f"Raw text lines: {text_lines[:5]}...")  # Log first 5 lines
    
    try:
        # Initialize with safe defaults
        supplier_name = "Unknown"
        invoice_number = "Unknown"
        invoice_date = "Unknown"
        total_amount = 0.0
        currency = "GBP"
        
        # Extract supplier name from first line
        if text_lines:
            try:
                supplier_name = text_lines[0].strip()
                if not supplier_name or len(supplier_name) < 2:
                    supplier_name = "Unknown"
            except Exception as e:
                logger.warning(f"Failed to extract supplier name: {e}")
                supplier_name = "Unknown"
        
        # Process each line for field extraction
        for line in text_lines:
            try:
                line_lower = line.lower().strip()
                
                # Extract invoice number
                if not invoice_number or invoice_number == "Unknown":
                    if 'invoice' in line_lower and any(char.isdigit() for char in line):
                        # Try to extract just the number part
                        numbers = re.findall(r'\d+', line)
                        if numbers:
                            invoice_number = f"INV-{numbers[0]}"
                        else:
                            invoice_number = line.strip()
                
                # Extract invoice date
                if not invoice_date or invoice_date == "Unknown":
                    if 'date' in line_lower and any(char.isdigit() for char in line):
                        parsed_date = safe_parse_date(line)
                        if parsed_date != "Unknown":
                            invoice_date = parsed_date
                
                # Extract total amount
                if total_amount == 0.0:
                    if any(word in line_lower for word in ['total', 'amount', 'balance', 'sum']):
                        # Look for currency amounts
                        amount_patterns = [
                            r'[£$€]\s*([\d,]+\.?\d*)',
                            r'([\d,]+\.?\d*)\s*[£$€]',
                            r'total[^\d]*([\d,]+\.?\d*)',
                            r'([\d,]+\.?\d*)\s*total'
                        ]
                        
                        for pattern in amount_patterns:
                            match = re.search(pattern, line, re.IGNORECASE)
                            if match:
                                amount_str = match.group(1)
                                parsed_amount = safe_parse_float(amount_str)
                                if parsed_amount > 0:
                                    total_amount = parsed_amount
                                    break
                
                # Extract currency
                if currency == "GBP":
                    if '£' in line:
                        currency = "GBP"
                    elif '$' in line:
                        currency = "USD"
                    elif '€' in line:
                        currency = "EUR"
                        
            except Exception as e:
                logger.warning(f"Error processing line '{line}': {e}")
                continue
        
        logger.info(f"Extracted invoice fields: supplier={supplier_name}, number={invoice_number}, date={invoice_date}, amount={total_amount}, currency={currency}")
        
        return {
            'supplier_name': supplier_name,
            'invoice_number': invoice_number,
            'invoice_date': invoice_date,
            'total_amount': total_amount,
            'currency': currency
        }
        
    except Exception as e:
        logger.error(f"Failed to extract invoice fields: {e}")
        return {
            'supplier_name': "Unknown",
            'invoice_number': "Unknown",
            'invoice_date': "Unknown",
            'total_amount': 0.0,
            'currency': "GBP"
        }

def extract_delivery_note_fields(text_lines: list[str]) -> dict:
    """Extract delivery note fields with comprehensive error handling"""
    logger.info(f"Extracting delivery note fields from {len(text_lines)} lines")
    logger.debug(f"Raw text lines: {text_lines[:5]}...")  # Log first 5 lines
    
    try:
        # Initialize with safe defaults
        supplier_name = "Unknown"
        delivery_note_number = "Unknown"
        delivery_date = "Unknown"
        delivered_by = "Unknown"
        signed_by = "Unknown"
        items = []
        
        # Extract supplier name from first line
        if text_lines:
            try:
                supplier_name = text_lines[0].strip()
                if not supplier_name or len(supplier_name) < 2:
                    supplier_name = "Unknown"
            except Exception as e:
                logger.warning(f"Failed to extract supplier name: {e}")
                supplier_name = "Unknown"
        
        # Process each line for field extraction
        for line in text_lines:
            try:
                line_lower = line.lower().strip()
                
                # Extract delivery note number
                if not delivery_note_number or delivery_note_number == "Unknown":
                    if ('delivery note' in line_lower or 'dn' in line_lower) and any(char.isdigit() for char in line):
                        numbers = re.findall(r'\d+', line)
                        if numbers:
                            delivery_note_number = f"DN-{numbers[0]}"
                        else:
                            delivery_note_number = line.strip()
                
                # Extract delivery date
                if not delivery_date or delivery_date == "Unknown":
                    if 'date' in line_lower and any(char.isdigit() for char in line):
                        parsed_date = safe_parse_date(line)
                        if parsed_date != "Unknown":
                            delivery_date = parsed_date
                
                # Extract delivered by
                if not delivered_by or delivered_by == "Unknown":
                    if 'delivered by' in line_lower:
                        delivered_by = line.strip()
                
                # Extract signed by
                if not signed_by or signed_by == "Unknown":
                    if 'signed by' in line_lower:
                        signed_by = line.strip()
                
                # Extract items (heuristic approach)
                if any(word in line_lower for word in ['item', 'product', 'description']) or (any(char.isdigit() for char in line) and len(line.split()) > 2):
                    items.append(line.strip())
                    
            except Exception as e:
                logger.warning(f"Error processing line '{line}': {e}")
                continue
        
        logger.info(f"Extracted delivery note fields: supplier={supplier_name}, number={delivery_note_number}, date={delivery_date}, items={len(items)}")
        
        return {
            'supplier_name': supplier_name,
            'delivery_note_number': delivery_note_number,
            'delivery_date': delivery_date,
            'delivered_by': delivered_by,
            'signed_by': signed_by,
            'items': items
        }
        
    except Exception as e:
        logger.error(f"Failed to extract delivery note fields: {e}")
        return {
            'supplier_name': "Unknown",
            'delivery_note_number': "Unknown",
            'delivery_date': "Unknown",
            'delivered_by': "Unknown",
            'signed_by': "Unknown",
            'items': []
        }

def parse_receipt_date(text: str) -> str:
    """Safely parse receipt date"""
    try:
        return safe_parse_date(text)
    except Exception as e:
        logger.warning(f"Failed to parse receipt date: {e}")
        return "Unknown"

def parse_receipt_total(text: str) -> str:
    """Safely parse receipt total"""
    try:
        # Look for lines like 'Total: £12.50' or 'TOTAL 12.50'
        total_patterns = [
            r"total[^\d]*(£|\$|€)?\s*([\d,.]+)",
            r"(£|\$|€)\s*([\d,.]+)\s*total"
        ]
        for pat in total_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m.group(0)
        return "Unknown"
    except Exception as e:
        logger.warning(f"Failed to parse receipt total: {e}")
        return "Unknown"

def parse_receipt_store(lines: list) -> str:
    """Safely parse receipt store name"""
    try:
        # Heuristic: first line with large text or all-caps
        for line in lines:
            if line.isupper() and len(line) > 3:
                return line.strip()
            if len(line) > 10 and sum(1 for c in line if c.isupper()) > 3:
                return line.strip()
        return lines[0] if lines else "Unknown"
    except Exception as e:
        logger.warning(f"Failed to parse receipt store: {e}")
        return "Unknown"

def parse_receipt_items(lines: list) -> list:
    """Safely parse receipt items"""
    try:
        # Heuristic: lines between 'items' and 'total' or lines with price at end
        items = []
        for line in lines:
            if re.search(r"\b\d+\.\d{2}\b", line):
                items.append(line.strip())
        return items
    except Exception as e:
        logger.warning(f"Failed to parse receipt items: {e}")
        return []

async def parse_with_ocr(file: UploadFile, threshold: int = 70) -> dict:
    """Parse document with OCR with enhanced error handling"""
    logger.info(f"Starting OCR processing for file: {file.filename}")
    
    try:
        contents = await file.read()
        
        # Validate file contents
        if not contents or len(contents) == 0:
            raise ValueError("Empty file")
        
        logger.info(f"File size: {len(contents)} bytes")
        
        # Save to a temp file for OpenCV
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            tmp.write(contents)
            tmp_path = tmp.name
        
        try:
            # Validate image can be opened
            pil_image = Image.open(tmp_path)
            pil_image.verify()  # Verify image integrity
            
            # Reopen for processing
            pil_image = Image.open(tmp_path)
            
            # Convert to RGB if needed
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            logger.info(f"Image dimensions: {pil_image.size}")
            
            # Preprocess image
            try:
                preprocessed = preprocess_image(tmp_path)
                
                # Validate preprocessed image
                if preprocessed is None or preprocessed.size == 0:
                    raise ValueError("Image preprocessing failed")
                
                pil_for_ocr = Image.fromarray(preprocessed)
                logger.info("Image preprocessing completed successfully")
                
            except Exception as preprocess_error:
                logger.warning(f"Preprocessing failed, using original image: {preprocess_error}")
                pil_for_ocr = pil_image
            
            # Run OCR with error handling
            try:
                logger.info("Starting OCR text extraction...")
                data = pytesseract.image_to_data(pil_for_ocr, output_type=pytesseract.Output.DICT)
                logger.info(f"OCR completed, found {len(data.get('text', []))} text elements")
            except Exception as ocr_error:
                logger.error(f"OCR processing failed: {ocr_error}")
                raise ValueError(f"OCR processing failed: {str(ocr_error)}")
            
            # Validate OCR output
            if not data or 'text' not in data or len(data['text']) == 0:
                logger.warning("No text detected in image")
                raise ValueError("No text detected in image")
            
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        
        # Process OCR results
        lines = []
        confidences = []
        current_line = ''
        last_line_num = -1
        
        logger.info("Processing OCR results...")
        
        for i in range(len(data['text'])):
            try:
                conf = int(data['conf'][i])
            except (ValueError, TypeError):
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
        
        logger.info(f"Processed {len(lines)} text lines with average confidence: {np.mean(confidences) if confidences else 0:.1f}")
        logger.debug(f"First 5 lines: {lines[:5]}")
        
        # Validate we have some content
        if not lines:
            logger.warning("No readable text found in document")
            raise ValueError("No readable text found in document")
        
        full_text = '\n'.join(lines)
        doc_type = detect_document_type(full_text)
        logger.info(f"Detected document type: {doc_type}")
        
        # Extract fields based on document type
        if doc_type == 'invoice':
            parsed_fields = extract_invoice_fields(lines)
        elif doc_type == 'delivery_note':
            parsed_fields = extract_delivery_note_fields(lines)
        else:
            parsed_fields = {}
        
        avg_conf = int(np.mean(confidences)) if confidences else 0
        
        logger.info(f"OCR processing completed successfully. Type: {doc_type}, Confidence: {avg_conf}")
        
        return {
            'parsed_data': parsed_fields,
            'raw_lines': lines,
            'document_type': doc_type,
            'confidence_score': avg_conf
        }
        
    except Exception as e:
        logger.error(f"OCR processing error for {file.filename}: {str(e)}")
        # Return a safe default response instead of raising
        return {
            'parsed_data': {
                'supplier_name': "Unknown",
                'invoice_number': "Unknown", 
                'invoice_date': "Unknown",
                'total_amount': 0.0,
                'currency': "GBP"
            },
            'raw_lines': [],
            'document_type': 'unknown',
            'confidence_score': 0
        }

async def parse_receipt(file: UploadFile, threshold: int = 70) -> dict:
    """Parse receipt with enhanced error handling"""
    logger.info(f"Starting receipt parsing for file: {file.filename}")
    
    try:
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
        
        pil_for_ocr = Image.fromarray(thresh)
        custom_config = '--psm 11'
        
        try:
            data = pytesseract.image_to_data(pil_for_ocr, output_type=pytesseract.Output.DICT, config=custom_config)
        except Exception as ocr_error:
            logger.error(f"Receipt OCR failed: {ocr_error}")
            raise ValueError(f"Receipt OCR processing failed: {str(ocr_error)}")
        
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
        
        # Extract fields with error handling
        try:
            total_amount = parse_receipt_total(full_text)
        except Exception as e:
            logger.warning(f"Failed to parse total amount: {e}")
            total_amount = "Unknown"
            
        try:
            purchase_date = parse_receipt_date(full_text)
        except Exception as e:
            logger.warning(f"Failed to parse purchase date: {e}")
            purchase_date = "Unknown"
            
        try:
            store_name = parse_receipt_store(lines)
        except Exception as e:
            logger.warning(f"Failed to parse store name: {e}")
            store_name = "Unknown"
            
        try:
            items = parse_receipt_items(lines)
        except Exception as e:
            logger.warning(f"Failed to parse items: {e}")
            items = []
        
        avg_conf = int(np.mean(confidences)) if confidences else 0
        
        logger.info(f"Receipt parsing completed. Store: {store_name}, Amount: {total_amount}, Confidence: {avg_conf}")
        
        return {
            'total_amount': total_amount,
            'purchase_date': purchase_date,
            'store_name': store_name,
            'items': items,
            'raw_text': full_text,
            'confidence_score': avg_conf
        }
        
    except Exception as e:
        logger.error(f"Receipt parsing error for {file.filename}: {str(e)}")
        # Return safe defaults
        return {
            'total_amount': "Unknown",
            'purchase_date': "Unknown",
            'store_name': "Unknown",
            'items': [],
            'raw_text': "",
            'confidence_score': 0
        }

@router.post("/ocr/parse")
async def parse_document(file: UploadFile = File(...), confidence_threshold: int = 70):
    """Parse uploaded document using OCR"""
    logger.info(f"Received OCR parse request for file: {file.filename}")
    
    # Validate file
    validate_file(file)
    
    try:
        parsed_data = await parse_with_ocr(file, threshold=confidence_threshold)
        
        # Ensure we always return a consistent response format
        result = {
            "document_type": parsed_data.get('document_type', 'unknown'),
            "parsed_data": parsed_data.get('parsed_data', {}),
            "confidence_score": parsed_data.get('confidence_score', 0),
            "raw_lines": parsed_data.get('raw_lines', []),
            "success": True,
            "original_filename": file.filename,
            "file_size": file.size,
            "processed_at": datetime.now().isoformat()
        }
        
        logger.info(f"OCR parse completed successfully for {file.filename}")
        return JSONResponse(result)
        
    except ValueError as e:
        logger.error(f"Validation error in OCR parsing: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in OCR parsing: {str(e)}")
        # Return a safe error response instead of crashing
        error_result = {
            "document_type": "unknown",
            "parsed_data": {
                "supplier_name": "Unknown",
                "invoice_number": "Unknown",
                "invoice_date": "Unknown", 
                "total_amount": 0.0,
                "currency": "GBP"
            },
            "confidence_score": 0,
            "raw_lines": [],
            "success": False,
            "error": str(e),
            "original_filename": file.filename,
            "file_size": file.size,
            "processed_at": datetime.now().isoformat()
        }
        return JSONResponse(error_result, status_code=500)

@router.post("/ocr/parse_receipt")
async def parse_receipt_document(file: UploadFile = File(...), confidence_threshold: int = 70):
    """Parse uploaded receipt using OCR"""
    logger.info(f"Received receipt parse request for file: {file.filename}")
    
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
            "total_amount": parsed_data.get('total_amount', "Unknown"),
            "purchase_date": parsed_data.get('purchase_date', "Unknown"),
            "store_name": parsed_data.get('store_name', "Unknown"),
            "items": parsed_data.get('items', []),
            "raw_text": parsed_data.get('raw_text', ""),
            "confidence_score": parsed_data.get('confidence_score', 0),
            "success": True,
            "original_filename": file.filename,
            "file_size": file.size,
            "processed_at": datetime.now().isoformat()
        }
        
        logger.info(f"Receipt parse completed successfully for {file.filename}")
        return JSONResponse(result)
        
    except Exception as e:
        logger.error(f"Receipt parsing failed: {str(e)}")
        # Return safe error response
        error_result = {
            "total_amount": "Unknown",
            "purchase_date": "Unknown", 
            "store_name": "Unknown",
            "items": [],
            "raw_text": "",
            "confidence_score": 0,
            "success": False,
            "error": str(e),
            "original_filename": file.filename,
            "file_size": file.size,
            "processed_at": datetime.now().isoformat()
        }
        return JSONResponse(error_result, status_code=500)

@router.post("/ocr/parse-receipt")
async def parse_receipt_document_alias(file: UploadFile = File(...), confidence_threshold: int = 70):
    """Parse uploaded receipt using OCR (alias endpoint)"""
    return await parse_receipt_document(file, confidence_threshold)

@router.post("/ocr/classify")
async def classify_document(file: UploadFile = File(...), confidence_threshold: int = 70):
    """
    Classify document type and extract data using OCR.
    Returns document type (invoice, delivery_note, unknown) with confidence score.
    """
    logger.info(f"Received document classification request for file: {file.filename}")
    
    # Validate file
    validate_file(file)
    
    try:
        # Parse document with OCR
        result = await parse_with_ocr(file, confidence_threshold)
        
        # Determine document type and confidence
        doc_type = result.get('document_type', 'unknown')
        confidence = result.get('confidence_score', 0)
        
        # Classification confidence logic
        classification_confidence = confidence
        
        # Boost confidence if we have good field extraction
        parsed_data = result.get('parsed_data', {})
        if doc_type == 'invoice':
            # Check if we extracted key invoice fields
            key_fields = ['supplier_name', 'invoice_number', 'total_amount']
            extracted_fields = sum(1 for field in key_fields if parsed_data.get(field) and parsed_data.get(field) != "Unknown")
            if extracted_fields >= 2:
                classification_confidence = min(100, confidence + 20)
        elif doc_type == 'delivery_note':
            # Check if we extracted key delivery note fields
            key_fields = ['supplier_name', 'delivery_note_number']
            extracted_fields = sum(1 for field in key_fields if parsed_data.get(field) and parsed_data.get(field) != "Unknown")
            if extracted_fields >= 1:
                classification_confidence = min(100, confidence + 15)
        
        # If confidence is too low, mark as unknown
        if classification_confidence < 30:
            doc_type = 'unknown'
        
        logger.info(f"Document classification completed: {doc_type} with confidence {classification_confidence}")
        
        return {
            "type": doc_type,
            "confidence": classification_confidence,
            "parsed_data": parsed_data,
            "raw_text": result.get('raw_lines', []),
            "ocr_confidence": confidence
        }
        
    except ValueError as e:
        logger.error(f"Validation error in classification: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in classification: {str(e)}")
        # Return safe error response
        return {
            "type": "unknown",
            "confidence": 0,
            "parsed_data": {
                "supplier_name": "Unknown",
                "invoice_number": "Unknown",
                "invoice_date": "Unknown",
                "total_amount": 0.0,
                "currency": "GBP"
            },
            "raw_text": [],
            "ocr_confidence": 0,
            "error": str(e)
        }

@router.get("/ocr/status")
async def get_ocr_status():
    """Get OCR service status"""
    return {
        "status": "operational",
        "version": "1.0.0",
        "supported_formats": list(ALLOWED_EXTENSIONS),
        "timestamp": datetime.now().isoformat()
    } 