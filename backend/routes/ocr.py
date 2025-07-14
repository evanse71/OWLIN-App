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
    """Safely extract text using regex pattern with enhanced error handling"""
    try:
        if not text or not isinstance(text, str):
            logger.debug(f"Invalid text input for pattern extraction: {type(text)}")
            return default
        
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            extracted = match.group(1).strip()
            logger.debug(f"Successfully extracted text with pattern '{pattern}': '{extracted}'")
            return extracted
        else:
            logger.debug(f"No match found for pattern '{pattern}' in text: '{text[:100]}...'")
            return default
    except re.error as e:
        logger.warning(f"Invalid regex pattern '{pattern}': {e}")
        return default
    except Exception as e:
        logger.warning(f"Failed to extract text with pattern '{pattern}' from '{text[:50]}...': {e}")
        return default

def safe_parse_float(text: str, default: float = 0.0) -> float:
    """Safely parse float from text with comprehensive error handling"""
    try:
        if not text or not isinstance(text, str):
            logger.debug(f"Invalid text input for float parsing: {type(text)}")
            return default
        
        # Log the original text for debugging
        logger.debug(f"Attempting to parse float from: '{text}'")
        
        # Remove currency symbols and non-numeric characters except decimal point and comma
        cleaned = re.sub(r'[^\d.,]', '', text)
        logger.debug(f"Cleaned text: '{cleaned}'")
        
        # Handle comma as thousand separator
        if ',' in cleaned and '.' in cleaned:
            # Format like "1,234.56"
            cleaned = cleaned.replace(',', '')
            logger.debug(f"Handled thousand separator: '{cleaned}'")
        elif ',' in cleaned and '.' not in cleaned:
            # Format like "1,234" or "1,234,56"
            parts = cleaned.split(',')
            if len(parts) > 2:
                # Multiple commas, treat as thousand separators
                cleaned = ''.join(parts[:-1]) + '.' + parts[-1]
                logger.debug(f"Handled multiple commas as thousand separators: '{cleaned}'")
            else:
                # Single comma, could be decimal separator
                cleaned = cleaned.replace(',', '.')
                logger.debug(f"Handled single comma as decimal separator: '{cleaned}'")
        
        if cleaned:
            result = float(cleaned)
            if result >= 0:
                logger.debug(f"Successfully parsed float: {result}")
                return result
            else:
                logger.warning(f"Negative amount detected: {result}, using default")
                return default
        else:
            logger.debug("No numeric content found after cleaning")
            return default
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to parse float from '{text}': {e}")
        return default
    except Exception as e:
        logger.error(f"Unexpected error parsing float from '{text}': {e}")
        return default

def safe_parse_date(text: str, default: str = "Unknown") -> str:
    """Safely parse date from text using datetime.strptime with multiple formats"""
    try:
        if not text or not isinstance(text, str):
            logger.debug(f"Invalid text input for date parsing: {type(text)}")
            return default
        
        # Log the original text for debugging
        logger.debug(f"Attempting to parse date from: '{text}'")
        
        # Clean the text - remove extra whitespace and common prefixes
        cleaned_text = re.sub(r'\s+', ' ', text.strip())
        logger.debug(f"Cleaned text: '{cleaned_text}'")
        
        # Common date patterns with their corresponding formats
        date_formats = [
            ("%d/%m/%Y", r"\b(\d{1,2}/\d{1,2}/\d{4})\b"),  # 31/12/2023
            ("%d-%m-%Y", r"\b(\d{1,2}-\d{1,2}-\d{4})\b"),  # 31-12-2023
            ("%Y-%m-%d", r"\b(\d{4}-\d{1,2}-\d{1,2})\b"),  # 2023-12-31
            ("%d/%m/%y", r"\b(\d{1,2}/\d{1,2}/\d{2})\b"),  # 31/12/23
            ("%d-%m-%y", r"\b(\d{1,2}-\d{1,2}-\d{2})\b"),  # 31-12-23
            ("%d %B %Y", r"\b(\d{1,2} [A-Za-z]{3,9} \d{4})\b"),  # 31 December 2023
            ("%d %b %Y", r"\b(\d{1,2} [A-Za-z]{3} \d{4})\b"),  # 31 Dec 2023
        ]
        
        for date_format, pattern in date_formats:
            try:
                match = re.search(pattern, cleaned_text, re.IGNORECASE)
                if match:
                    date_str = match.group(1)
                    logger.debug(f"Found date string '{date_str}' with pattern '{pattern}'")
                    
                    # Try to parse with datetime.strptime
                    parsed_date = datetime.strptime(date_str, date_format)
                    formatted_date = parsed_date.strftime("%Y-%m-%d")
                    logger.debug(f"Successfully parsed date: {formatted_date}")
                    return formatted_date
            except re.error as e:
                logger.debug(f"Invalid regex pattern '{pattern}': {e}")
                continue
            except (ValueError, TypeError) as e:
                logger.debug(f"Failed to parse date '{date_str}' with format '{date_format}': {e}")
                continue
            except Exception as e:
                logger.debug(f"Unexpected error parsing date '{date_str}' with format '{date_format}': {e}")
                continue
        
        logger.debug(f"No valid date pattern found in text: '{cleaned_text}'")
        return default
    except Exception as e:
        logger.warning(f"Failed to parse date from '{text}': {e}")
        return default

def safe_extract_supplier_name(text_lines: List[str], default: str = "Unknown Supplier") -> str:
    """Safely extract supplier name with fallback handling"""
    try:
        if not text_lines:
            logger.debug("No text lines provided for supplier name extraction")
            return default
        
        logger.debug(f"Extracting supplier name from {len(text_lines)} lines")
        
        # Try first line as supplier name
        first_line = text_lines[0].strip()
        if first_line and len(first_line) >= 2:
            logger.debug(f"Processing first line as supplier name: '{first_line}'")
            
            # Clean up common prefixes/suffixes
            try:
                cleaned = re.sub(r'^(invoice|delivery|receipt|document)\s*[:#]?\s*', '', first_line, flags=re.IGNORECASE)
                cleaned = re.sub(r'\s+(ltd|limited|inc|corp|company|co)\s*$', '', cleaned, flags=re.IGNORECASE)
                
                if cleaned and len(cleaned) >= 2:
                    logger.debug(f"Extracted supplier name from first line: '{cleaned}'")
                    return cleaned
                else:
                    logger.debug(f"Cleaned first line too short: '{cleaned}'")
            except re.error as e:
                logger.warning(f"Regex error cleaning supplier name from '{first_line}': {e}")
                # Fallback to original line if regex fails
                if first_line and len(first_line) >= 2:
                    return first_line
        
        # Look for company name patterns in other lines
        for i, line in enumerate(text_lines[1:5]):  # Check first few lines
            try:
                line_clean = line.strip()
                logger.debug(f"Checking line {i+2} for company name: '{line_clean}'")
                
                # Look for lines that might be company names (all caps, reasonable length)
                if (len(line_clean) >= 3 and len(line_clean) <= 50 and 
                    line_clean.isupper() and 
                    not any(word in line_clean.lower() for word in ['invoice', 'total', 'date', 'amount'])):
                    logger.debug(f"Found company name in line {i+2}: '{line_clean}'")
                    return line_clean
            except Exception as e:
                logger.warning(f"Error processing line {i+2} for supplier name: {e}")
                continue
        
        logger.debug("No suitable supplier name found, using default")
        return default
    except Exception as e:
        logger.warning(f"Failed to extract supplier name: {e}")
        return default

def safe_extract_invoice_number(text_lines: List[str], default: str = "Unknown") -> str:
    """Safely extract invoice number with fallback handling"""
    try:
        logger.debug(f"Extracting invoice number from {len(text_lines)} lines")
        
        invoice_patterns = [
            r'invoice\s*(?:number|no|#)?\s*[:#]?\s*([A-Z0-9\-_/]+)',
            r'inv\s*(?:number|no|#)?\s*[:#]?\s*([A-Z0-9\-_/]+)',
            r'([A-Z]{2,4}[-_/]?\d{4,8})',  # Generic pattern like INV-12345
            r'(\d{4,8})',  # Just numbers
        ]
        
        for line_num, line in enumerate(text_lines):
            try:
                line_lower = line.lower()
                if 'invoice' in line_lower or 'inv' in line_lower:
                    logger.debug(f"Found invoice keyword in line {line_num+1}: '{line}'")
                    
                    for pattern_num, pattern in enumerate(invoice_patterns):
                        try:
                            match = re.search(pattern, line, re.IGNORECASE)
                            if match:
                                invoice_num = match.group(1).strip()
                                logger.debug(f"Found invoice number with pattern {pattern_num+1}: '{invoice_num}'")
                                
                                if invoice_num and len(invoice_num) >= 3:
                                    result = f"INV-{invoice_num}" if not invoice_num.startswith('INV') else invoice_num
                                    logger.debug(f"Returning invoice number: '{result}'")
                                    return result
                        except re.error as e:
                            logger.debug(f"Invalid regex pattern {pattern_num+1} '{pattern}': {e}")
                            continue
                        except Exception as e:
                            logger.debug(f"Error with pattern {pattern_num+1} on line {line_num+1}: {e}")
                            continue
            except Exception as e:
                logger.warning(f"Error processing line {line_num+1} for invoice number: {e}")
                continue
        
        logger.debug("No invoice number found, using default")
        return default
    except Exception as e:
        logger.warning(f"Failed to extract invoice number: {e}")
        return default

def extract_invoice_fields(text_lines: list[str]) -> dict:
    """Extract invoice fields with bulletproof error handling"""
    logger.info(f"Extracting invoice fields from {len(text_lines)} lines")
    logger.debug(f"Raw text lines: {text_lines[:5]}...")  # Log first 5 lines
    
    try:
        # Initialize with safe defaults
        supplier_name = "Unknown Supplier"
        invoice_number = "Unknown"
        invoice_date = "Unknown"
        total_amount = 0.0
        currency = "GBP"
        
        # Extract supplier name with bulletproof fallback
        try:
            supplier_name = safe_extract_supplier_name(text_lines, "Unknown Supplier")
        except Exception as e:
            logger.error(f"❌ Failed to extract supplier name from: {text_lines[:3]} — {e}")
            supplier_name = "Unknown Supplier"
        
        # Extract invoice number with bulletproof fallback
        try:
            invoice_number = safe_extract_invoice_number(text_lines, "Unknown")
        except Exception as e:
            logger.error(f"❌ Failed to extract invoice number from: {text_lines[:3]} — {e}")
            invoice_number = "Unknown"
        
        # Extract invoice date with bulletproof fallback
        for line_num, line in enumerate(text_lines):
            try:
                line_lower = line.lower()
                if 'date' in line_lower and any(char.isdigit() for char in line):
                    logger.debug(f"Found date keyword in line {line_num+1}: '{line}'")
                    try:
                        parsed_date = safe_parse_date(line, "Unknown")
                        if parsed_date != "Unknown":
                            invoice_date = parsed_date
                            logger.debug(f"Extracted invoice date: '{invoice_date}'")
                            break
                    except Exception as e:
                        logger.error(f"❌ Failed to parse invoice date from: {line} — {e}")
                        continue
            except Exception as e:
                logger.error(f"❌ Failed to process date line {line_num+1} '{line}': {e}")
                continue
        
        # Extract total amount with bulletproof fallback
        for line_num, line in enumerate(text_lines):
            try:
                line_lower = line.lower()
                if any(word in line_lower for word in ['total', 'amount', 'balance', 'sum', 'due']):
                    logger.debug(f"Found amount keyword in line {line_num+1}: '{line}'")
                    
                    # Look for currency amounts with multiple patterns
                    amount_patterns = [
                        r'[£$€]\s*([\d,]+\.?\d*)',
                        r'([\d,]+\.?\d*)\s*[£$€]',
                        r'total[^\d]*([\d,]+\.?\d*)',
                        r'([\d,]+\.?\d*)\s*total',
                        r'amount[^\d]*([\d,]+\.?\d*)',
                        r'([\d,]+\.?\d*)\s*amount',
                    ]
                    
                    for pattern_num, pattern in enumerate(amount_patterns):
                        try:
                            match = re.search(pattern, line, re.IGNORECASE)
                            if match:
                                amount_str = match.group(1)
                                logger.debug(f"Found amount with pattern {pattern_num+1}: '{amount_str}'")
                                try:
                                    parsed_amount = safe_parse_float(amount_str, 0.0)
                                    if parsed_amount > 0:
                                        total_amount = parsed_amount
                                        logger.debug(f"Extracted total amount: {total_amount}")
                                        break
                                except Exception as e:
                                    logger.error(f"❌ Failed to parse total amount from: {amount_str} — {e}")
                                    continue
                        except re.error as e:
                            logger.error(f"❌ Invalid amount regex pattern {pattern_num+1} '{pattern}': {e}")
                            continue
                        except Exception as e:
                            logger.error(f"❌ Error with amount pattern {pattern_num+1} on line {line_num+1}: {e}")
                            continue
                    
                    if total_amount > 0:
                        break
            except Exception as e:
                logger.error(f"❌ Failed to process amount line {line_num+1} '{line}': {e}")
                continue
        
        # Extract currency with bulletproof fallback
        for line_num, line in enumerate(text_lines):
            try:
                if '£' in line:
                    currency = "GBP"
                    logger.debug(f"Found GBP currency in line {line_num+1}")
                    break
                elif '$' in line:
                    currency = "USD"
                    logger.debug(f"Found USD currency in line {line_num+1}")
                    break
                elif '€' in line:
                    currency = "EUR"
                    logger.debug(f"Found EUR currency in line {line_num+1}")
                    break
            except Exception as e:
                logger.error(f"❌ Failed to process currency line {line_num+1} '{line}': {e}")
                continue
        
        logger.info(f"Extracted invoice fields: supplier={supplier_name}, number={invoice_number}, date={invoice_date}, amount={total_amount}, currency={currency}")
        
        # Ensure we always return all required fields
        return {
            'supplier_name': supplier_name,
            'invoice_number': invoice_number,
            'invoice_date': invoice_date,
            'total_amount': total_amount,
            'currency': currency
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to extract invoice fields: {e}")
        return {
            'supplier_name': "Unknown Supplier",
            'invoice_number': "Unknown",
            'invoice_date': "Unknown",
            'total_amount': 0.0,
            'currency': "GBP"
        }

def extract_delivery_note_fields(text_lines: list[str]) -> dict:
    """Extract delivery note fields with bulletproof error handling"""
    logger.info(f"Extracting delivery note fields from {len(text_lines)} lines")
    logger.debug(f"Raw text lines: {text_lines[:5]}...")  # Log first 5 lines
    
    try:
        # Initialize with safe defaults
        supplier_name = "Unknown Supplier"
        delivery_note_number = "Unknown"
        delivery_date = "Unknown"
        delivered_by = "Unknown"
        signed_by = "Unknown"
        items = []
        
        # Extract supplier name with bulletproof fallback
        try:
            supplier_name = safe_extract_supplier_name(text_lines, "Unknown Supplier")
        except Exception as e:
            logger.error(f"❌ Failed to extract delivery note supplier name from: {text_lines[:3]} — {e}")
            supplier_name = "Unknown Supplier"
        
        # Extract delivery note number with bulletproof fallback
        for line_num, line in enumerate(text_lines):
            try:
                line_lower = line.lower()
                if ('delivery note' in line_lower or 'dn' in line_lower) and any(char.isdigit() for char in line):
                    logger.debug(f"Found delivery note keyword in line {line_num+1}: '{line}'")
                    
                    # Look for delivery note number patterns
                    dn_patterns = [
                        r'delivery\s*note\s*(?:number|no|#)?\s*[:#]?\s*([A-Z0-9\-_/]+)',
                        r'dn\s*(?:number|no|#)?\s*[:#]?\s*([A-Z0-9\-_/]+)',
                        r'([A-Z]{2,4}[-_/]?\d{4,8})',  # Generic pattern
                        r'(\d{4,8})',  # Just numbers
                    ]
                    
                    for pattern_num, pattern in enumerate(dn_patterns):
                        try:
                            match = re.search(pattern, line, re.IGNORECASE)
                            if match:
                                dn_num = match.group(1).strip()
                                logger.debug(f"Found delivery note number with pattern {pattern_num+1}: '{dn_num}'")
                                
                                if dn_num and len(dn_num) >= 3:
                                    delivery_note_number = f"DN-{dn_num}" if not dn_num.startswith('DN') else dn_num
                                    logger.debug(f"Extracted delivery note number: '{delivery_note_number}'")
                                    break
                        except re.error as e:
                            logger.error(f"❌ Invalid delivery note regex pattern {pattern_num+1} '{pattern}': {e}")
                            continue
                        except Exception as e:
                            logger.error(f"❌ Error with delivery note pattern {pattern_num+1} on line {line_num+1}: {e}")
                            continue
                    
                    if delivery_note_number != "Unknown":
                        break
            except Exception as e:
                logger.error(f"❌ Failed to process delivery note number line {line_num+1} '{line}': {e}")
                continue
        
        # Extract delivery date with bulletproof fallback
        for line_num, line in enumerate(text_lines):
            try:
                line_lower = line.lower()
                if 'date' in line_lower and any(char.isdigit() for char in line):
                    logger.debug(f"Found date keyword in line {line_num+1}: '{line}'")
                    try:
                        parsed_date = safe_parse_date(line, "Unknown")
                        if parsed_date != "Unknown":
                            delivery_date = parsed_date
                            logger.debug(f"Extracted delivery date: '{delivery_date}'")
                            break
                    except Exception as e:
                        logger.error(f"❌ Failed to parse delivery date from: {line} — {e}")
                        continue
            except Exception as e:
                logger.error(f"❌ Failed to process delivery date line {line_num+1} '{line}': {e}")
                continue
        
        # Extract delivered by with bulletproof fallback
        for line_num, line in enumerate(text_lines):
            try:
                line_lower = line.lower()
                if 'delivered by' in line_lower or 'delivered' in line_lower:
                    delivered_by = line.strip()
                    logger.debug(f"Found delivered by in line {line_num+1}: '{delivered_by}'")
                    break
            except Exception as e:
                logger.error(f"❌ Failed to process delivered by line {line_num+1} '{line}': {e}")
                continue
        
        # Extract signed by with bulletproof fallback
        for line_num, line in enumerate(text_lines):
            try:
                line_lower = line.lower()
                if 'signed by' in line_lower or 'received by' in line_lower:
                    signed_by = line.strip()
                    logger.debug(f"Found signed by in line {line_num+1}: '{signed_by}'")
                    break
            except Exception as e:
                logger.error(f"❌ Failed to process signed by line {line_num+1} '{line}': {e}")
                continue
        
        # Extract items with bulletproof fallback
        for line_num, line in enumerate(text_lines):
            try:
                line_lower = line.lower()
                if (any(word in line_lower for word in ['item', 'product', 'description', 'quantity']) or 
                    (any(char.isdigit() for char in line) and len(line.split()) > 2)):
                    items.append(line.strip())
                    logger.debug(f"Added item from line {line_num+1}: '{line.strip()}'")
            except Exception as e:
                logger.error(f"❌ Failed to process item line {line_num+1} '{line}': {e}")
                continue
        
        logger.info(f"Extracted delivery note fields: supplier={supplier_name}, number={delivery_note_number}, date={delivery_date}, items={len(items)}")
        
        # Ensure we always return all required fields
        return {
            'supplier_name': supplier_name,
            'delivery_note_number': delivery_note_number,
            'delivery_date': delivery_date,
            'delivered_by': delivered_by,
            'signed_by': signed_by,
            'items': items
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to extract delivery note fields: {e}")
        return {
            'supplier_name': "Unknown Supplier",
            'delivery_note_number': "Unknown",
            'delivery_date': "Unknown",
            'delivered_by': "Unknown",
            'signed_by': "Unknown",
            'items': []
        }

def parse_receipt_date(text: str) -> str:
    """Safely parse receipt date using datetime.strptime"""
    try:
        logger.debug(f"Parsing receipt date from: '{text}'")
        result = safe_parse_date(text, "Unknown")
        logger.debug(f"Receipt date result: '{result}'")
        return result
    except Exception as e:
        logger.warning(f"Failed to parse receipt date: {e}")
        return "Unknown"

def parse_receipt_total(text: str) -> str:
    """Safely parse receipt total with fallback"""
    try:
        logger.debug(f"Parsing receipt total from: '{text}'")
        
        # Look for lines like 'Total: £12.50' or 'TOTAL 12.50'
        total_patterns = [
            r"total[^\d]*(£|\$|€)?\s*([\d,.]+)",
            r"(£|\$|€)\s*([\d,.]+)\s*total",
            r"amount[^\d]*(£|\$|€)?\s*([\d,.]+)",
            r"(£|\$|€)\s*([\d,.]+)\s*amount",
        ]
        
        for pattern_num, pat in enumerate(total_patterns):
            try:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    result = m.group(0)
                    logger.debug(f"Found receipt total with pattern {pattern_num+1}: '{result}'")
                    return result
            except re.error as e:
                logger.debug(f"Invalid receipt total regex pattern {pattern_num+1} '{pat}': {e}")
                continue
            except Exception as e:
                logger.debug(f"Error with receipt total pattern {pattern_num+1}: {e}")
                continue
        
        logger.debug("No receipt total found")
        return "Unknown"
    except Exception as e:
        logger.warning(f"Failed to parse receipt total: {e}")
        return "Unknown"

def parse_receipt_store(lines: list) -> str:
    """Safely parse receipt store name with fallback"""
    try:
        logger.debug(f"Parsing receipt store from {len(lines)} lines")
        
        # Heuristic: first line with large text or all-caps
        for line_num, line in enumerate(lines):
            try:
                if line.isupper() and len(line) > 3:
                    result = line.strip()
                    logger.debug(f"Found store name (all caps) in line {line_num+1}: '{result}'")
                    return result
                if len(line) > 10 and sum(1 for c in line if c.isupper()) > 3:
                    result = line.strip()
                    logger.debug(f"Found store name (mixed case) in line {line_num+1}: '{result}'")
                    return result
            except Exception as e:
                logger.debug(f"Error processing line {line_num+1} for store name: {e}")
                continue
        
        result = lines[0] if lines else "Unknown"
        logger.debug(f"Using first line as store name: '{result}'")
        return result
    except Exception as e:
        logger.warning(f"Failed to parse receipt store: {e}")
        return "Unknown"

def parse_receipt_items(lines: list) -> list:
    """Safely parse receipt items with fallback"""
    try:
        logger.debug(f"Parsing receipt items from {len(lines)} lines")
        
        # Heuristic: lines between 'items' and 'total' or lines with price at end
        items = []
        for line_num, line in enumerate(lines):
            try:
                if re.search(r"\b\d+\.\d{2}\b", line):
                    item = line.strip()
                    items.append(item)
                    logger.debug(f"Added item from line {line_num+1}: '{item}'")
            except re.error as e:
                logger.debug(f"Invalid regex in line {line_num+1}: {e}")
                continue
            except Exception as e:
                logger.debug(f"Error processing line {line_num+1} for items: {e}")
                continue
        
        logger.debug(f"Found {len(items)} receipt items")
        return items
    except Exception as e:
        logger.warning(f"Failed to parse receipt items: {e}")
        return []

async def parse_with_ocr(file: UploadFile, threshold: int = 70) -> dict:
    """Parse document with OCR with bulletproof error handling"""
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
        
        # Process OCR results with bulletproof error handling
        lines = []
        confidences = []
        current_line = ''
        last_line_num = -1
        
        logger.info("Processing OCR results...")
        
        for i in range(len(data['text'])):
            try:
                # Bulletproof confidence parsing
                try:
                    conf = int(data['conf'][i])
                except (ValueError, TypeError, IndexError) as e:
                    logger.warning(f"❌ Failed to parse confidence value at index {i}: {e}")
                    conf = 0
                
                # Bulletproof word extraction
                try:
                    word = data['text'][i].strip()
                except (IndexError, AttributeError) as e:
                    logger.warning(f"❌ Failed to extract word at index {i}: {e}")
                    word = ""
                
                # Bulletproof line number extraction
                try:
                    line_num = data['line_num'][i]
                except (IndexError, KeyError) as e:
                    logger.warning(f"❌ Failed to extract line number at index {i}: {e}")
                    line_num = last_line_num + 1
                
                if conf < threshold or not word:
                    continue
                    
                confidences.append(conf)
                
                if line_num != last_line_num and current_line:
                    lines.append(current_line.strip())
                    current_line = word
                    last_line_num = line_num
                else:
                    current_line += ' ' + word
                    
            except Exception as e:
                logger.error(f"❌ Failed to process OCR element at index {i}: {e}")
                continue
        
        if current_line:
            lines.append(current_line.strip())
        
        logger.info(f"Processed {len(lines)} text lines with average confidence: {np.mean(confidences) if confidences else 0:.1f}")
        logger.debug(f"First 5 lines: {lines[:5]}")
        
        # Log full OCR text for debugging
        full_text = '\n'.join(lines)
        logger.info(f"📄 OCR Text for {file.filename}:\n{full_text}")
        
        # Validate we have some content
        if not lines:
            logger.warning("No readable text found in document")
            logger.info("OCR output:")
            logger.info(full_text)
            raise ValueError("No readable text found in document")
        
        # Bulletproof document type detection
        try:
            doc_type = detect_document_type(full_text)
            logger.info(f"Detected document type: {doc_type}")
        except Exception as e:
            logger.error(f"❌ Failed to detect document type: {e}")
            doc_type = 'unknown'
        
        # Extract fields based on document type with bulletproof error handling
        try:
            if doc_type == 'invoice':
                parsed_fields = extract_invoice_fields(lines)
            elif doc_type == 'delivery_note':
                parsed_fields = extract_delivery_note_fields(lines)
            else:
                parsed_fields = {}
        except Exception as field_error:
            logger.error(f"❌ Field extraction failed: {field_error}")
            logger.info("OCR output:")
            logger.info(full_text)
            # Return safe defaults instead of crashing
            parsed_fields = {
                'supplier_name': "Unknown Supplier",
                'invoice_number': "Unknown",
                'invoice_date': "Unknown",
                'total_amount': 0.0,
                'currency': "GBP"
            }
        
        # Bulletproof confidence calculation
        try:
            avg_conf = int(np.mean(confidences)) if confidences else 0
        except Exception as e:
            logger.error(f"❌ Failed to calculate average confidence: {e}")
            avg_conf = 0
        
        logger.info(f"OCR processing completed successfully. Type: {doc_type}, Confidence: {avg_conf}")
        
        # Ensure we always return all required fields
        return {
            'parsed_data': {
                'supplier_name': parsed_fields.get('supplier_name', "Unknown Supplier"),
                'invoice_number': parsed_fields.get('invoice_number', "Unknown"),
                'invoice_date': parsed_fields.get('invoice_date', "Unknown"),
                'total_amount': parsed_fields.get('total_amount', 0.0),
                'currency': parsed_fields.get('currency', "GBP")
            },
            'raw_lines': lines,
            'document_type': doc_type,
            'confidence_score': avg_conf
        }
        
    except Exception as e:
        logger.error(f"❌ OCR processing error for {file.filename}: {str(e)}")
        
        # Log the full OCR text if available for debugging
        try:
            if 'lines' in locals() and lines:
                full_text = '\n'.join(lines)
                logger.info("OCR output:")
                logger.info(full_text)
        except Exception as log_error:
            logger.warning(f"Could not log OCR text: {log_error}")
        
        # Return a safe default response instead of raising
        return {
            'parsed_data': {
                'supplier_name': "Unknown Supplier",
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
    """Parse receipt with bulletproof error handling"""
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
            logger.error(f"❌ Receipt OCR failed: {ocr_error}")
            raise ValueError(f"Receipt OCR processing failed: {str(ocr_error)}")
        
        lines = []
        confidences = []
        current_line = ''
        last_line_num = -1
        
        # Bulletproof OCR result processing
        for i in range(len(data['text'])):
            try:
                # Bulletproof confidence parsing
                try:
                    conf = int(data['conf'][i])
                except (ValueError, TypeError, IndexError) as e:
                    logger.warning(f"❌ Failed to parse receipt confidence value at index {i}: {e}")
                    conf = 0
                
                # Bulletproof word extraction
                try:
                    word = data['text'][i].strip()
                except (IndexError, AttributeError) as e:
                    logger.warning(f"❌ Failed to extract receipt word at index {i}: {e}")
                    word = ""
                
                # Bulletproof line number extraction
                try:
                    line_num = data['line_num'][i]
                except (IndexError, KeyError) as e:
                    logger.warning(f"❌ Failed to extract receipt line number at index {i}: {e}")
                    line_num = last_line_num + 1
                
                if conf < threshold or not word:
                    continue
                confidences.append(conf)
                if line_num != last_line_num and current_line:
                    lines.append(current_line.strip())
                    current_line = word
                    last_line_num = line_num
                else:
                    current_line += ' ' + word
            except Exception as e:
                logger.error(f"❌ Failed to process receipt OCR element at index {i}: {e}")
                continue
                
        if current_line:
            lines.append(current_line.strip())
        
        full_text = '\n'.join(lines)
        
        # Log full OCR text for debugging
        logger.info(f"📄 Receipt OCR Text for {file.filename}:\n{full_text}")
        
        # Extract fields with bulletproof error handling
        try:
            total_amount = parse_receipt_total(full_text)
        except Exception as e:
            logger.error(f"❌ Failed to parse total amount from: {full_text} — {e}")
            total_amount = "Unknown"
            
        try:
            purchase_date = parse_receipt_date(full_text)
        except Exception as e:
            logger.error(f"❌ Failed to parse purchase date from: {full_text} — {e}")
            purchase_date = "Unknown"
            
        try:
            store_name = parse_receipt_store(lines)
        except Exception as e:
            logger.error(f"❌ Failed to parse store name from: {lines} — {e}")
            store_name = "Unknown"
            
        try:
            items = parse_receipt_items(lines)
        except Exception as e:
            logger.error(f"❌ Failed to parse items from: {lines} — {e}")
            items = []
        
        # Bulletproof confidence calculation
        try:
            avg_conf = int(np.mean(confidences)) if confidences else 0
        except Exception as e:
            logger.error(f"❌ Failed to calculate receipt average confidence: {e}")
            avg_conf = 0
        
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
        logger.error(f"❌ Receipt parsing error for {file.filename}: {str(e)}")
        
        # Log the full OCR text if available for debugging
        try:
            if 'full_text' in locals():
                logger.info("Receipt OCR output:")
                logger.info(full_text)
        except Exception as log_error:
            logger.warning(f"Could not log receipt OCR text: {log_error}")
        
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
                "supplier_name": "Unknown Supplier",
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
                "supplier_name": "Unknown Supplier",
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