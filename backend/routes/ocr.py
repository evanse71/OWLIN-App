"""
OCR Processing Module for Document Analysis

This module provides comprehensive OCR functionality for processing invoices, delivery notes,
and other business documents. It includes:

- PDF and image file support
- Fuzzy keyword matching for improved field extraction
- Document type classification (invoice vs delivery note)
- Debug mode for troubleshooting
- Bulletproof error handling
- Enhanced OCR pipeline with improved preprocessing

Key Functions:
- parse_with_ocr: Main OCR processing function
- classify_document_type: Document type classification
- extract_invoice_fields: Invoice field extraction with fuzzy matching
- extract_delivery_note_fields: Delivery note field extraction
- process_pdf_with_ocr: PDF-specific processing
- process_image_with_ocr: Image-specific processing
- Enhanced OCR pipeline with structured output

Author: OCR Team
Version: 2.1.0
"""

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
# Optional pdf2image import for PDF processing
try:
    from pdf2image import convert_from_bytes, convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    convert_from_bytes = None  # type: ignore
    convert_from_path = None  # type: ignore
    logger = logging.getLogger(__name__)
    logger.warning("pdf2image not available - PDF processing will be limited")
from difflib import get_close_matches
import traceback  # Add this import for detailed error logging
import fitz  # PyMuPDF

# Import the enhanced OCR pipeline
try:
    from ocr_pipeline import parse_document as enhanced_parse_document
    ENHANCED_OCR_AVAILABLE = True
except ImportError:
    ENHANCED_OCR_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Enhanced OCR pipeline not available - using standard OCR")

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

def save_debug_data(ocr_data: dict, full_text: str, filename: str, debug: bool = False) -> None:
    """Save OCR debug data to files if debug mode is enabled"""
    if not debug:
        return
    
    try:
        # Create debug directory
        debug_dir = Path("data/ocr_debug")
        debug_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate safe filename
        safe_filename = re.sub(r'[^\w\-_.]', '_', filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save OCR data as JSON
        ocr_file = debug_dir / f"ocr_data_{safe_filename}_{timestamp}.json"
        import json
        with open(ocr_file, 'w') as f:
            json.dump(ocr_data, f, indent=2, default=str)
        logger.info(f"💾 Saved OCR debug data to: {ocr_file}")
        
        # Save full text
        text_file = debug_dir / f"ocr_text_{safe_filename}_{timestamp}.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(f"Filename: {filename}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Text length: {len(full_text)} characters\n")
            f.write("-" * 80 + "\n")
            f.write(full_text)
        logger.info(f"💾 Saved OCR text to: {text_file}")
        
    except Exception as e:
        logger.error(f"❌ Failed to save debug data: {e}")

def create_safe_response(filename: str, file_size: int, success: bool = True, error: Optional[str] = None, **kwargs) -> dict:
    """Create a standardized API response with safe defaults"""
    response = {
        "success": success,
        "original_filename": filename,
        "file_size": file_size,
        "processed_at": datetime.now().isoformat()
    }
    
    if not success and error:
        response["error"] = error
    
    # Add any additional fields
    response.update(kwargs)
    
    return response

def extract_amount_from_line(line: str) -> Optional[float]:
    """Extract amount from a text line using multiple patterns"""
    try:
        amount_patterns = [
            r'[£$€]\s*([\d,]+\.?\d*)',
            r'([\d,]+\.?\d*)\s*[£$€]',
            r'total[^\d]*([\d,]+\.?\d*)',
            r'([\d,]+\.?\d*)\s*total',
            r'amount[^\d]*([\d,]+\.?\d*)',
            r'([\d,]+\.?\d*)\s*amount',
        ]
        
        for pattern in amount_patterns:
            try:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    amount_str = match.group(1)
                    parsed_amount = safe_parse_float(amount_str, 0.0)
                    if parsed_amount > 0:
                        return parsed_amount
            except Exception as e:
                logger.debug(f"Pattern {pattern} failed on line '{line}': {e}")
                continue
        
        return None
    except Exception as e:
        logger.warning(f"Amount extraction failed for line '{line}': {e}")
        return None

def convert_pdf_to_images(file_content: bytes, filename: str) -> List[Image.Image]:
    """Convert PDF file to list of PIL Images for OCR processing"""
    try:
        logger.info(f"Converting PDF to images: {filename}")
        
        # Validate PDF content
        if not file_content or len(file_content) == 0:
            raise ValueError("PDF file is empty")
        
        # Check if content looks like a PDF (starts with %PDF)
        if not file_content.startswith(b'%PDF'):
            raise ValueError("File does not appear to be a valid PDF")
        
        # Convert PDF bytes to images
        if not PDF2IMAGE_AVAILABLE or convert_from_bytes is None:
            raise HTTPException(status_code=500, detail="PDF processing requires pdf2image module. Please install it: pip install pdf2image")
        images = convert_from_bytes(file_content, dpi=300)
        
        # Validate conversion results
        if not images or len(images) == 0:
            raise ValueError("PDF conversion produced no images")
        
        logger.info(f"✅ Successfully converted PDF to {len(images)} images")
        
        return images
    except Exception as e:
        logger.error(f"❌ Failed to convert PDF to images: {e}")
        logger.error(f"❌ PDF conversion traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"Failed to process PDF: {str(e)}")

def is_pdf_file(filename: str) -> bool:
    """Check if file is a PDF based on extension"""
    return Path(filename).suffix.lower() == '.pdf'

def preprocess_numpy_image(image_array: np.ndarray) -> np.ndarray:
    """Preprocess numpy array image for OCR"""
    try:
        # Convert to grayscale if needed
        if len(image_array.shape) == 3:
            gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = image_array
        
        # Denoise
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # Adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10
        )
        
        # Optional: Invert if background is dark
        mean_intensity = np.mean(thresh)
        if mean_intensity < 127:
            thresh = cv2.bitwise_not(thresh)
        
        # Optional: Contrast boost
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        final = clahe.apply(thresh)
        
        return final
    except Exception as e:
        logger.warning(f"Image preprocessing failed: {e}")
        return image_array

def find_fuzzy_keyword(text: str, keywords: List[str], threshold: float = 0.7) -> Optional[str]:
    """Find the best matching keyword using fuzzy matching"""
    try:
        if not text or not keywords:
            return None
        
        # Clean the text
        cleaned_text = text.lower().strip()
        
        # Get close matches
        matches = get_close_matches(cleaned_text, [k.lower() for k in keywords], n=1, cutoff=threshold)
        
        if matches:
            matched_keyword = matches[0]
            logger.debug(f"🔍 Fuzzy match found: '{text}' -> '{matched_keyword}' (threshold: {threshold})")
            return matched_keyword
        
        return None
    except Exception as e:
        logger.warning(f"⚠️ Fuzzy keyword matching failed for '{text}': {e}")
        return None

def scan_for_fuzzy_keywords(text_lines: List[str], keyword_mapping: Dict[str, List[str]], threshold: float = 0.7) -> Dict[str, List[Dict[str, Any]]]:
    """Scan text lines for fuzzy keyword matches and return categorized lines"""
    try:
        results = {category: [] for category in keyword_mapping.keys()}
        
        for line_num, line in enumerate(text_lines):
            try:
                line_lower = line.lower().strip()
                
                # Check each category of keywords
                for category, keywords in keyword_mapping.items():
                    if find_fuzzy_keyword(line_lower, keywords, threshold):
                        results[category].append({
                            'line': line,
                            'line_number': line_num + 1,
                            'category': category
                        })
                        logger.debug(f"🔍 Found {category} keyword in line {line_num + 1}: '{line}'")
                        break  # Only match first category found
                        
            except Exception as e:
                logger.warning(f"⚠️ Failed to process line {line_num + 1} for fuzzy keywords: {e}")
                continue
        
        return results
    except Exception as e:
        logger.error(f"❌ Fuzzy keyword scanning failed: {e}")
        return {category: [] for category in keyword_mapping.keys()}

def classify_document_type(text: str) -> str:
    """Classify document type using a robust scoring system with enhanced keyword lists and fuzzy matching"""
    try:
        # Handle empty or invalid input
        if not text or not isinstance(text, str):
            logger.warning("⚠️ Invalid text provided for document classification")
            return 'unknown'
        
        # Clean and normalize text
        text_cleaned = re.sub(r'\s+', ' ', text.strip())
        if len(text_cleaned) < 10:
            logger.warning(f"⚠️ Text too short for classification ({len(text_cleaned)} chars): '{text_cleaned}'")
            return 'unknown'
        
        text_lower = text_cleaned.lower()
        text_words = set(text_lower.split())
        
        # Enhanced keyword lists with variations and common misspellings
        invoice_keywords = [
            "invoice", "inv", "bill", "billing", "vat", "tax", "subtotal", "total", "net amount", 
            "supplier", "vendor", "company", "business", "from", "issued by", "invoice number", 
            "invoice no", "invoice #", "inv number", "inv no", "inv #", "bill number", "bill no",
            "amount due", "balance due", "total due", "grand total", "final amount", "payment",
            "terms", "due date", "billing date", "issue date", "created date", "invoice date",
            "tax invoice", "commercial invoice", "pro forma invoice"
        ]
        
        delivery_note_keywords = [
            "delivery", "delivered", "delivery note", "delivery slip", "goods received", 
            "received", "receipt", "qty", "quantity", "items", "signature", "signed", 
            "goods", "products", "materials", "date of delivery", "delivery date",
            "packing list", "packing slip", "shipping", "shipped", "carrier", "driver",
            "delivery to", "delivered to", "received by", "signed by", "authorized by",
            "dn", "packing", "dispatch note", "goods receipt"
        ]
        
        # Count keyword matches for each type with fuzzy matching
        invoice_matches = []
        delivery_matches = []
        
        # Check for exact invoice keyword matches
        for keyword in invoice_keywords:
            if keyword in text_lower:
                invoice_matches.append(keyword)
                logger.debug(f"🔍 Found invoice keyword: '{keyword}'")
        
        # Check for exact delivery note keyword matches
        for keyword in delivery_note_keywords:
            if keyword in text_lower:
                delivery_matches.append(keyword)
                logger.debug(f"🔍 Found delivery keyword: '{keyword}'")
        
        # Additional scoring based on word presence (fallback checks)
        invoice_word_score = 0
        delivery_word_score = 0
        
        # Check for word-level matches (more flexible)
        for word in text_words:
            if any(inv_word in word for inv_word in ["inv", "bill", "vat", "tax", "total", "supplier", "vendor"]):
                invoice_word_score += 1
            if any(del_word in word for del_word in ["deliv", "receiv", "goods", "qty", "sign", "pack", "dispatch"]):
                delivery_word_score += 1
        
        # Calculate normalized scores (0-1 scale)
        invoice_score = len(invoice_matches) / len(invoice_keywords) if invoice_keywords else 0
        delivery_score = len(delivery_matches) / len(delivery_note_keywords) if delivery_note_keywords else 0
        
        # Add word-level scoring
        invoice_score += (invoice_word_score / max(len(text_words), 1)) * 0.3
        delivery_score += (delivery_word_score / max(len(text_words), 1)) * 0.3
        
        # Cap scores at 1.0
        invoice_score = min(invoice_score, 1.0)
        delivery_score = min(delivery_score, 1.0)
        
        logger.info(f"📊 Document classification scores:")
        logger.info(f"   Invoice: {invoice_score:.3f} ({len(invoice_matches)}/{len(invoice_keywords)} keywords + {invoice_word_score} word matches)")
        logger.info(f"   Delivery: {delivery_score:.3f} ({len(delivery_matches)}/{len(delivery_note_keywords)} keywords + {delivery_word_score} word matches)")
        logger.info(f"   Invoice matches: {invoice_matches}")
        logger.info(f"   Delivery matches: {delivery_matches}")
        
        # Determine document type based on scores with confidence threshold
        confidence_threshold = 0.05  # Very low threshold to be inclusive
        
        # If either type has any keywords, prefer that type over unknown
        if invoice_score == 0 and delivery_score == 0:
            logger.warning("⚠️ No keywords found - document cannot be classified")
            return 'unknown'
        elif invoice_score > delivery_score and invoice_score >= confidence_threshold:
            confidence_percent = int(invoice_score * 100)
            logger.info(f"✅ Classified as INVOICE (score: {invoice_score:.3f}, confidence: {confidence_percent}%)")
            return 'invoice'
        elif delivery_score > invoice_score and delivery_score >= confidence_threshold:
            confidence_percent = int(delivery_score * 100)
            logger.info(f"✅ Classified as DELIVERY NOTE (score: {delivery_score:.3f}, confidence: {confidence_percent}%)")
            return 'delivery_note'
        elif invoice_score == delivery_score and invoice_score >= confidence_threshold:
            logger.warning(f"⚠️ Equal scores - ambiguous classification (invoice: {invoice_score:.3f}, delivery: {delivery_score:.3f})")
            # Default to invoice if scores are equal and above threshold
            return 'invoice'
        else:
            logger.warning(f"⚠️ Scores below threshold - cannot classify (invoice: {invoice_score:.3f}, delivery: {delivery_score:.3f})")
            return 'unknown'
            
    except Exception as e:
        logger.error(f"❌ Document classification failed: {str(e)}")
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        return 'unknown'

def classify_utility_invoice(supplier_name: str, text: str) -> bool:
    """
    Classify if an invoice is a utility/service invoice that doesn't require delivery notes.
    
    Args:
        supplier_name: The supplier name extracted from the invoice
        text: The full OCR text from the invoice
        
    Returns:
        bool: True if this is a utility/service invoice, False otherwise
    """
    try:
        if not supplier_name or not text:
            return False
            
        supplier_lower = supplier_name.lower()
        text_lower = text.lower()
        
        # Utility and service provider keywords
        utility_keywords = [
            "electricity", "gas", "water", "energy", "power", "utility", "utilities",
            "british gas", "edf energy", "e.on", "eon", "npower", "n power", "scottish power",
            "sse", "southern electric", "thames water", "severn trent", "united utilities",
            "yorkshire water", "wessex water", "anglia water", "northumbrian water",
            "telecom", "telephone", "phone", "broadband", "internet", "bt", "sky", "virgin",
            "insurance", "insurer", "policy", "premium", "subscription", "membership",
            "rent", "lease", "licensing", "software", "saas", "cloud", "hosting",
            "cleaning", "maintenance", "security", "alarm", "cctv", "waste", "recycling"
        ]
        
        # Check supplier name for utility keywords
        for keyword in utility_keywords:
            if keyword in supplier_lower:
                logger.info(f"🔍 Utility invoice detected: supplier '{supplier_name}' contains keyword '{keyword}'")
                return True
        
        # Check full text for utility/service indicators
        service_indicators = [
            "service charge", "utility bill", "energy bill", "gas bill", "electricity bill",
            "water bill", "telephone bill", "phone bill", "internet bill", "broadband bill",
            "insurance premium", "subscription fee", "membership fee", "rental fee",
            "licensing fee", "software license", "maintenance fee", "cleaning service",
            "security service", "waste collection", "recycling service"
        ]
        
        for indicator in service_indicators:
            if indicator in text_lower:
                logger.info(f"🔍 Service invoice detected: text contains indicator '{indicator}'")
                return True
        
        # Check for absence of delivery-related terms (additional heuristic)
        delivery_terms = ["delivery", "goods", "products", "items", "quantity", "qty", "received", "signature"]
        delivery_terms_found = sum(1 for term in delivery_terms if term in text_lower)
        
        if delivery_terms_found <= 1:  # Very few delivery-related terms
            logger.info(f"🔍 Potential service invoice: only {delivery_terms_found} delivery-related terms found")
            # Additional check for billing/service terms
            billing_terms = ["bill", "billing", "charge", "fee", "amount due", "payment", "account"]
            billing_terms_found = sum(1 for term in billing_terms if term in text_lower)
            
            if billing_terms_found >= 3:  # Multiple billing terms suggest service invoice
                logger.info(f"🔍 Service invoice confirmed: {billing_terms_found} billing terms found")
                return True
        
        logger.info(f"🔍 Standard invoice: supplier '{supplier_name}' requires delivery note")
        return False
        
    except Exception as e:
        logger.error(f"❌ Utility invoice classification failed: {str(e)}")
        return False

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
    
    if file.size == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    
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
    """Extract invoice fields with bulletproof error handling and fuzzy keyword matching"""
    logger.info(f"Extracting invoice fields from {len(text_lines)} lines")
    logger.debug(f"Raw text lines: {text_lines[:5]}...")  # Log first 5 lines
    
    # Initialize with safe defaults
    supplier_name = "Unknown Supplier"
    invoice_number = "Unknown"
    invoice_date = "Unknown"
    total_amount = 0.0
    currency = "GBP"
    
    try:
        # Define keyword mappings for fuzzy matching
        keyword_mapping = {
            'invoice_number': ['invoice number', 'invoice no', 'invoice #', 'inv number', 'inv no', 'inv #', 'bill number', 'bill no'],
            'invoice_date': ['invoice date', 'date', 'billing date', 'issue date', 'created date'],
            'total_amount': ['total', 'amount', 'balance', 'sum', 'due', 'grand total', 'final amount', 'total due'],
            'supplier': ['supplier', 'vendor', 'company', 'business', 'from', 'issued by'],
            'currency': ['currency', 'gbp', 'usd', 'eur', 'pound', 'dollar', 'euro']
        }
        
        # Scan for fuzzy keyword matches
        fuzzy_results = scan_for_fuzzy_keywords(text_lines, keyword_mapping, threshold=0.7)
        logger.debug(f"🔍 Fuzzy keyword scan results: {fuzzy_results}")
        
        # Extract supplier name with bulletproof fallback
        try:
            supplier_name = safe_extract_supplier_name(text_lines, "Unknown Supplier")
            logger.debug(f"✅ Extracted supplier name: {supplier_name}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to extract supplier name: {e}")
            supplier_name = "Unknown Supplier"
        
        # Extract invoice number with bulletproof fallback
        try:
            invoice_number = safe_extract_invoice_number(text_lines, "Unknown")
            logger.debug(f"✅ Extracted invoice number: {invoice_number}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to extract invoice number: {e}")
            invoice_number = "Unknown"
        
        # Extract invoice date with fuzzy keyword support
        date_lines = fuzzy_results.get('invoice_date', [])
        for date_match in date_lines:
            try:
                line = date_match['line']
                logger.debug(f"🔍 Processing date line {date_match['line_number']}: '{line}'")
                parsed_date = safe_parse_date(line, "Unknown")
                if parsed_date != "Unknown":
                    invoice_date = parsed_date
                    logger.debug(f"✅ Extracted invoice date: '{invoice_date}'")
                    break
            except Exception as e:
                logger.warning(f"⚠️ Failed to parse date from fuzzy match: {e}")
                continue
        
        # Fallback to original date extraction if fuzzy matching didn't work
        if invoice_date == "Unknown":
            for line_num, line in enumerate(text_lines):
                try:
                    line_lower = line.lower()
                    if 'date' in line_lower and any(char.isdigit() for char in line):
                        logger.debug(f"🔍 Found date keyword in line {line_num+1}: '{line}'")
                        try:
                            parsed_date = safe_parse_date(line, "Unknown")
                            if parsed_date != "Unknown":
                                invoice_date = parsed_date
                                logger.debug(f"✅ Extracted invoice date: '{invoice_date}'")
                                break
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to parse invoice date from line {line_num+1}: {e}")
                            continue
                except Exception as e:
                    logger.warning(f"⚠️ Failed to process date line {line_num+1}: {e}")
                    continue
        
        # Extract total amount with fuzzy keyword support
        amount_lines = fuzzy_results.get('total_amount', [])
        for amount_match in amount_lines:
            try:
                line = amount_match['line']
                logger.debug(f"🔍 Processing amount line {amount_match['line_number']}: '{line}'")
                
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
                            logger.debug(f"🔍 Found amount with pattern {pattern_num+1}: '{amount_str}'")
                            try:
                                parsed_amount = safe_parse_float(amount_str, 0.0)
                                if parsed_amount > 0:
                                    total_amount = parsed_amount
                                    logger.debug(f"✅ Extracted total amount: {total_amount}")
                                    break
                            except Exception as e:
                                logger.warning(f"⚠️ Failed to parse total amount from '{amount_str}': {e}")
                                continue
                    except re.error as e:
                        logger.warning(f"⚠️ Invalid amount regex pattern {pattern_num+1}: {e}")
                        continue
                    except Exception as e:
                        logger.warning(f"⚠️ Error with amount pattern {pattern_num+1}: {e}")
                        continue
                
                if total_amount > 0:
                    break
            except Exception as e:
                logger.warning(f"⚠️ Failed to process amount from fuzzy match: {e}")
                continue
        
        # Fallback to original amount extraction if fuzzy matching didn't work
        if total_amount == 0.0:
            for line_num, line in enumerate(text_lines):
                try:
                    line_lower = line.lower()
                    if any(word in line_lower for word in ['total', 'amount', 'balance', 'sum', 'due']):
                        logger.debug(f"🔍 Found amount keyword in line {line_num+1}: '{line}'")
                        
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
                                    logger.debug(f"🔍 Found amount with pattern {pattern_num+1}: '{amount_str}'")
                                    try:
                                        parsed_amount = safe_parse_float(amount_str, 0.0)
                                        if parsed_amount > 0:
                                            total_amount = parsed_amount
                                            logger.debug(f"✅ Extracted total amount: {total_amount}")
                                            break
                                    except Exception as e:
                                        logger.warning(f"⚠️ Failed to parse total amount from '{amount_str}': {e}")
                                        continue
                            except re.error as e:
                                logger.warning(f"⚠️ Invalid amount regex pattern {pattern_num+1}: {e}")
                                continue
                            except Exception as e:
                                logger.warning(f"⚠️ Error with amount pattern {pattern_num+1} on line {line_num+1}: {e}")
                                continue
                        
                        if total_amount > 0:
                            break
                except Exception as e:
                    logger.warning(f"⚠️ Failed to process amount line {line_num+1}: {e}")
                    continue
        
        # Extract currency with bulletproof fallback
        for line_num, line in enumerate(text_lines):
            try:
                if '£' in line:
                    currency = "GBP"
                    logger.debug(f"✅ Found GBP currency in line {line_num+1}")
                    break
                elif '$' in line:
                    currency = "USD"
                    logger.debug(f"✅ Found USD currency in line {line_num+1}")
                    break
                elif '€' in line:
                    currency = "EUR"
                    logger.debug(f"✅ Found EUR currency in line {line_num+1}")
                    break
            except Exception as e:
                logger.warning(f"⚠️ Failed to process currency line {line_num+1}: {e}")
                continue
        
        logger.info(f"✅ Successfully extracted invoice fields: supplier={supplier_name}, number={invoice_number}, date={invoice_date}, amount={total_amount}, currency={currency}")
        
    except Exception as e:
        logger.error(f"❌ Critical error in extract_invoice_fields: {e}")
        logger.error(f"❌ Text lines that caused error: {text_lines[:3]}...")
    
    # Ensure we always return all required fields
    return {
        'supplier_name': supplier_name,
        'invoice_number': invoice_number,
        'invoice_date': invoice_date,
        'total_amount': total_amount,
        'currency': currency
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

async def parse_with_ocr(file: UploadFile, threshold: int = 70, debug: bool = False) -> dict:
    """Parse document with OCR with bulletproof error handling and PDF support"""
    logger.info(f"Starting OCR processing for file: {file.filename}")
    
    try:
        # Read file contents and validate
        contents = await file.read()
        
        # Validate file contents
        if not contents or len(contents) == 0:
            logger.error(f"❌ Empty file received: {file.filename}")
            raise ValueError("Empty file - no content to process")
        
        logger.info(f"File size: {len(contents)} bytes")
        
        # Reset file stream for potential reuse
        try:
            await file.seek(0)
        except Exception as seek_error:
            logger.warning(f"⚠️ Could not reset file stream: {seek_error}")
            # Continue anyway, we have the contents
        
        # Check if file is PDF
        if file.filename and is_pdf_file(file.filename):
            logger.info(f"Processing PDF file: {file.filename}")
            return await process_pdf_with_ocr(contents, file.filename, threshold, debug)
        else:
            logger.info(f"Processing image file: {file.filename}")
            return await process_image_with_ocr(contents, file.filename or "unknown", threshold, debug)
        
    except ValueError as e:
        # Handle validation errors (empty file, corrupt file, etc.)
        logger.error(f"❌ Validation error for {file.filename}: {str(e)}")
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"File validation failed: {str(e)}")
    except Exception as e:
        # Handle all other errors
        logger.error(f"❌ OCR processing error for {file.filename}: {str(e)}")
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")

async def process_pdf_with_ocr(file_content: bytes, filename: str, threshold: int = 70, debug: bool = False) -> dict:
    """Process PDF file by converting to images and running OCR on each page"""
    try:
        # Convert PDF to images
        images = convert_pdf_to_images(file_content, filename)
        
        all_lines = []
        all_confidences = []
        page_results = []
        
        # Process each page
        for page_num, image in enumerate(images):
            logger.info(f"Processing PDF page {page_num + 1}/{len(images)}")
            
            try:
                # Convert PIL image to numpy array for preprocessing
                img_array = np.array(image)
                
                # Validate image array
                if img_array.size == 0:
                    logger.warning(f"Page {page_num + 1} has empty image array")
                    continue
                
                # Preprocess image
                try:
                    preprocessed = preprocess_numpy_image(img_array)
                    pil_for_ocr = Image.fromarray(preprocessed)
                    logger.debug(f"Page {page_num + 1} preprocessing completed")
                except Exception as preprocess_error:
                    logger.warning(f"Page {page_num + 1} preprocessing failed, using original: {preprocess_error}")
                    pil_for_ocr = image
                
                # Run OCR on this page
                try:
                    data = pytesseract.image_to_data(pil_for_ocr, output_type=pytesseract.Output.DICT)
                    logger.debug(f"Page {page_num + 1} OCR completed, found {len(data.get('text', []))} text elements")
                except Exception as ocr_error:
                    logger.error(f"Page {page_num + 1} OCR failed: {ocr_error}")
                    continue
                
                # Process OCR results for this page
                page_lines, page_confidences = process_ocr_data(data, threshold)
                
                if page_lines:
                    all_lines.extend(page_lines)
                    all_confidences.extend(page_confidences)
                    page_results.append({
                        'page': page_num + 1,
                        'lines': page_lines,
                        'confidence': np.mean(page_confidences) if page_confidences else 0
                    })
                    logger.info(f"Page {page_num + 1}: {len(page_lines)} lines, avg confidence: {np.mean(page_confidences) if page_confidences else 0:.1f}")
                
            except Exception as page_error:
                logger.error(f"❌ Failed to process PDF page {page_num + 1}: {page_error}")
                continue
        
        if not all_lines:
            logger.warning(f"⚠️ No readable text found in PDF: {filename}")
            logger.warning("⚠️ This could be an image-based PDF or scanned document")
            
            # Instead of failing, return a basic result with default values
            return {
                'parsed_data': {
                    'supplier_name': "Document requires manual review",
                    'invoice_number': "Unknown",
                    'invoice_date': "Unknown", 
                    'total_amount': 0.0,
                    'currency': "GBP"
                },
                'raw_lines': [],
                'document_type': 'unknown',
                'confidence_score': 0,
                'pdf_pages': len(images),
                'page_results': [],
                'success': True,
                'error': None
            }
        
        # Combine all pages and process
        full_text = '\n'.join(all_lines)
        logger.info(f"📄 Combined OCR Text from {len(images)} pages:\n{full_text}")
        
        # Save debug data if enabled
        if debug:
            # Get OCR data from the first page for debugging
            first_page_data = pytesseract.image_to_data(images[0], output_type=pytesseract.Output.DICT) if images else {}
            save_debug_data(first_page_data, full_text, filename, debug=True)
        
        # Detect document type
        try:
            doc_type = classify_document_type(full_text)
            logger.info(f"Detected document type: {doc_type}")
        except Exception as e:
            logger.error(f"❌ Failed to detect document type: {e}")
            doc_type = 'unknown'
        
        # Check for multiple invoices in the PDF
        multiple_invoices = []
        if len(page_results) > 1 and doc_type == 'invoice':
            multiple_invoices = detect_multiple_invoices(page_results)
            logger.info(f"🔍 Multiple invoice detection: found {len(multiple_invoices)} separate invoices")
        
        # Extract fields
        try:
            if doc_type == 'invoice':
                parsed_fields = extract_invoice_fields(all_lines)
                
                # Classify if this is a utility/service invoice
                supplier_name = parsed_fields.get('supplier_name', 'Unknown Supplier')
                is_utility_invoice = classify_utility_invoice(supplier_name, full_text)
                parsed_fields['delivery_note_required'] = not is_utility_invoice
                
                if is_utility_invoice:
                    logger.info(f"🔍 Utility invoice detected: {supplier_name} - no delivery note required")
                else:
                    logger.info(f"🔍 Standard invoice detected: {supplier_name} - delivery note required")
                    
            elif doc_type == 'delivery_note':
                parsed_fields = extract_delivery_note_fields(all_lines)
            else:
                # Document could not be classified - return message instead of attempting field extraction
                logger.warning("⚠️ Document classified as unknown - skipping field extraction")
                parsed_fields = {
                    'supplier_name': "This document could not be classified. Please review manually.",
                    'invoice_number': "Unknown",
                    'invoice_date': "Unknown",
                    'total_amount': 0.0,
                    'currency': "GBP",
                    'delivery_note_required': True  # Default to requiring delivery note
                }
        except Exception as field_error:
            logger.error(f"❌ Field extraction failed: {field_error}")
            parsed_fields = {
                'supplier_name': "Unknown Supplier",
                'invoice_number': "Unknown",
                'invoice_date': "Unknown",
                'total_amount': 0.0,
                'currency': "GBP",
                'delivery_note_required': True  # Default to requiring delivery note
            }
        
        # Calculate overall confidence
        overall_confidence = np.mean(all_confidences) if all_confidences else 0
        
        # Prepare response
        response_data = {
            'parsed_data': parsed_fields,
            'raw_lines': all_lines,
            'document_type': doc_type,
            'confidence_score': overall_confidence,
            'pdf_pages': len(images),
            'page_results': page_results,
            'multiple_invoices': multiple_invoices,
            'success': True,
            'error': None
        }
        
        # Add utility invoice information
        if doc_type == 'invoice':
            response_data['is_utility_invoice'] = parsed_fields.get('delivery_note_required', True) == False
            response_data['delivery_note_required'] = parsed_fields.get('delivery_note_required', True)
        
        logger.info(f"✅ PDF processing completed successfully")
        logger.info(f"📊 Document type: {doc_type}")
        logger.info(f"📊 Confidence: {overall_confidence:.2f}")
        logger.info(f"📊 Pages processed: {len(images)}")
        logger.info(f"📊 Multiple invoices detected: {len(multiple_invoices)}")
        
        return response_data
        
    except Exception as e:
        logger.error(f"❌ PDF processing failed: {str(e)}")
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        return {
            'parsed_data': {
                'supplier_name': "Processing failed",
                'invoice_number': "Unknown",
                'invoice_date': "Unknown",
                'total_amount': 0.0,
                'currency': "GBP",
                'delivery_note_required': True
            },
            'raw_lines': [],
            'document_type': 'unknown',
            'confidence_score': 0,
            'pdf_pages': 0,
            'page_results': [],
            'multiple_invoices': [],
            'success': False,
            'error': f"PDF processing failed: {str(e)}"
        }

async def process_image_with_ocr(file_content: bytes, filename: str, threshold: int = 70, debug: bool = False) -> dict:
    """Process image file with OCR (original implementation)"""
    try:
        # Validate image content
        if not file_content or len(file_content) == 0:
            raise ValueError("Image file is empty")
        
        # Save to a temp file for OpenCV
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name
        
        try:
            # Validate image can be opened
            try:
                pil_image = Image.open(tmp_path)
                pil_image.verify()  # Verify image integrity
            except Exception as verify_error:
                logger.error(f"❌ Image verification failed: {verify_error}")
                raise ValueError(f"Image file is corrupt or unsupported: {str(verify_error)}")
            
            # Reopen for processing
            try:
                pil_image = Image.open(tmp_path)
            except Exception as open_error:
                logger.error(f"❌ Failed to reopen image: {open_error}")
                raise ValueError(f"Failed to open image file: {str(open_error)}")
            
            # Convert to RGB if needed
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            logger.info(f"Image dimensions: {pil_image.size}")
            
            # Validate image dimensions
            if pil_image.size[0] == 0 or pil_image.size[1] == 0:
                raise ValueError("Image has invalid dimensions")
            
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
        lines, confidences = process_ocr_data(data, threshold)
        
        logger.info(f"Processed {len(lines)} text lines with average confidence: {np.mean(confidences) if confidences else 0:.1f}")
        logger.debug(f"First 5 lines: {lines[:5]}")
        
        # Log full OCR text for debugging
        full_text = '\n'.join(lines)
        logger.info(f"📄 OCR Text for {filename}:\n{full_text}")
        
        # Save debug data if enabled
        if debug:
            save_debug_data(data, full_text, filename, debug=True)
        
        # Validate we have some content
        if not lines:
            logger.warning("No readable text found in document")
            logger.info("OCR output:")
            logger.info(full_text)
            raise ValueError("No readable text found in document")
        
        # Bulletproof document type detection
        try:
            doc_type = classify_document_type(full_text)
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
                # Document could not be classified - provide helpful message
                logger.warning("⚠️ Document classified as unknown - providing guidance message")
                
                # Try to extract any recognizable information
                supplier_hint = "Unknown Supplier"
                for line in lines[:10]:  # Check first 10 lines
                    if any(word in line.lower() for word in ['ltd', 'inc', 'corp', 'company', 'business']):
                        supplier_hint = line.strip()
                        break
                
                parsed_fields = {
                    'supplier_name': f"Document could not be automatically classified. Please review manually. Detected text suggests this might be from: {supplier_hint}",
                    'invoice_number': "Unknown - requires manual review",
                    'invoice_date': "Unknown - requires manual review",
                    'total_amount': 0.0,
                    'currency': "GBP",
                    'classification_note': "This document did not contain clear invoice or delivery note indicators. Please manually classify it as an invoice or delivery note."
                }
        except Exception as field_error:
            logger.error(f"❌ Field extraction failed: {field_error}")
            parsed_fields = {
                'supplier_name': "Unknown Supplier - extraction failed",
                'invoice_number': "Unknown - extraction failed",
                'invoice_date': "Unknown - extraction failed",
                'total_amount': 0.0,
                'currency': "GBP",
                'classification_note': "Field extraction encountered an error. Please review the document manually."
            }
        
        # Bulletproof confidence calculation
        try:
            avg_conf = int(np.mean(confidences)) if confidences else 0
        except Exception as e:
            logger.error(f"❌ Failed to calculate average confidence: {e}")
            avg_conf = 0
        
        logger.info(f"Image OCR processing completed successfully. Type: {doc_type}, Confidence: {avg_conf}")
        
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
        logger.error(f"❌ Image OCR processing error: {str(e)}")
        logger.error(f"❌ Image processing traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Image OCR processing failed: {str(e)}")

def process_ocr_data(data: dict, threshold: int) -> tuple[List[str], List[int]]:
    """Process OCR data and return lines and confidences"""
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
    
    return lines, confidences

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

def detect_duplicate_document(new_doc: dict, existing_docs: list, threshold: float = 0.9) -> Optional[dict]:
    """
    Detect if a new document is a duplicate of an existing document.
    
    Args:
        new_doc: Dictionary containing parsed data of the new document
        existing_docs: List of existing document dictionaries
        threshold: Similarity threshold (0.0 to 1.0) for duplicate detection
    
    Returns:
        Dictionary with duplicate info if found, None otherwise
        {
            'existing_doc': dict,
            'similarity_score': float,
            'matching_fields': list,
            'differences': dict
        }
    """
    try:
        if not existing_docs:
            return None
        
        best_match = None
        best_score = 0.0
        best_matching_fields = []
        best_differences = {}
        
        new_parsed = new_doc.get('parsed_data', {})
        new_supplier = new_parsed.get('supplier_name', '').lower().strip()
        new_invoice_num = new_parsed.get('invoice_number', '').lower().strip()
        new_total = safe_parse_float(new_parsed.get('total_amount', '0'), 0.0)
        new_date = new_parsed.get('invoice_date', '').lower().strip()
        
        for existing_doc in existing_docs:
            existing_parsed = existing_doc.get('parsed_data', {})
            existing_supplier = existing_parsed.get('supplier_name', '').lower().strip()
            existing_invoice_num = existing_parsed.get('invoice_number', '').lower().strip()
            existing_total = safe_parse_float(existing_parsed.get('total_amount', '0'), 0.0)
            existing_date = existing_parsed.get('invoice_date', '').lower().strip()
            
            # Calculate field-by-field similarity scores
            supplier_similarity = 0.0
            if new_supplier and existing_supplier:
                supplier_similarity = calculate_text_similarity(new_supplier, existing_supplier)
            
            invoice_similarity = 0.0
            if new_invoice_num and existing_invoice_num:
                invoice_similarity = calculate_text_similarity(new_invoice_num, existing_invoice_num)
            
            total_similarity = 0.0
            if new_total > 0 and existing_total > 0:
                # For amounts, use percentage difference
                amount_diff = abs(new_total - existing_total) / max(new_total, existing_total)
                total_similarity = 1.0 - min(amount_diff, 1.0)
            
            date_similarity = 0.0
            if new_date and existing_date:
                date_similarity = calculate_text_similarity(new_date, existing_date)
            
            # Calculate weighted overall similarity
            # Give more weight to invoice number and supplier name
            weights = {
                'supplier': 0.4,
                'invoice_number': 0.4,
                'total_amount': 0.15,
                'date': 0.05
            }
            
            overall_similarity = (
                supplier_similarity * weights['supplier'] +
                invoice_similarity * weights['invoice_number'] +
                total_similarity * weights['total_amount'] +
                date_similarity * weights['date']
            )
            
            # Track matching fields and differences
            matching_fields = []
            differences = {}
            
            if supplier_similarity > 0.8:
                matching_fields.append('supplier_name')
            elif new_supplier and existing_supplier:
                differences['supplier_name'] = {
                    'new': new_supplier,
                    'existing': existing_supplier,
                    'similarity': supplier_similarity
                }
            
            if invoice_similarity > 0.8:
                matching_fields.append('invoice_number')
            elif new_invoice_num and existing_invoice_num:
                differences['invoice_number'] = {
                    'new': new_invoice_num,
                    'existing': existing_invoice_num,
                    'similarity': invoice_similarity
                }
            
            if total_similarity > 0.9:
                matching_fields.append('total_amount')
            elif new_total > 0 and existing_total > 0:
                differences['total_amount'] = {
                    'new': new_total,
                    'existing': existing_total,
                    'similarity': total_similarity
                }
            
            if date_similarity > 0.8:
                matching_fields.append('invoice_date')
            elif new_date and existing_date:
                differences['invoice_date'] = {
                    'new': new_date,
                    'existing': existing_date,
                    'similarity': date_similarity
                }
            
            # Update best match if this is better
            if overall_similarity > best_score:
                best_score = overall_similarity
                best_match = existing_doc
                best_matching_fields = matching_fields
                best_differences = differences
        
        # Return duplicate info if similarity exceeds threshold
        if best_score >= threshold and best_match:
            logger.info(f"Duplicate detected with {best_score:.2f} similarity score")
            return {
                'existing_doc': best_match,
                'similarity_score': best_score,
                'matching_fields': best_matching_fields,
                'differences': best_differences
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Error in duplicate detection: {e}")
        return None

def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity between two text strings using multiple methods.
    
    Args:
        text1: First text string
        text2: Second text string
    
    Returns:
        Similarity score between 0.0 and 1.0
    """
    try:
        if not text1 or not text2:
            return 0.0
        
        # Normalize text
        text1 = text1.lower().strip()
        text2 = text2.lower().strip()
        
        # Exact match
        if text1 == text2:
            return 1.0
        
        # Use difflib for fuzzy matching
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, text1, text2).ratio()
        
        # Boost similarity for partial matches
        if text1 in text2 or text2 in text1:
            similarity = max(similarity, 0.9)
        
        return similarity
        
    except Exception as e:
        logger.warning(f"Error calculating text similarity: {e}")
        return 0.0

@router.post("/ocr/parse")
async def parse_document(file: UploadFile = File(...), confidence_threshold: int = 70, debug: bool = False):
    """Parse uploaded document using OCR with real-time parsing and structured results"""
    logger.info(f"Received OCR parse request for file: {file.filename} (debug: {debug})")
    
    # Validate file
    try:
        validate_file(file)
    except HTTPException as e:
        logger.error(f"File validation failed: {e.detail}")
        return JSONResponse({
            "success": False,
            "error": e.detail,
            "document_type": "unknown",
            "confidence_score": 0,
            "data": {
                "supplier_name": "OCR Processing Failed",
                "invoice_number": "Unknown",
                "invoice_date": "Unknown", 
                "total_amount": "0.00",
                "currency": "GBP"
            }
        }, status_code=200)  # Return 200 instead of 400 to keep file visible
    
    try:
        # Read file contents
        contents = await file.read()
        
        # Validate file contents
        if not contents or len(contents) == 0:
            logger.error(f"❌ Empty file received: {file.filename}")
            return JSONResponse({
                "success": False,
                "error": "Empty file - no content to process",
                "document_type": "unknown",
                "confidence_score": 0,
                "data": {
                    "supplier_name": "OCR Processing Failed",
                    "invoice_number": "Unknown",
                    "invoice_date": "Unknown", 
                    "total_amount": "0.00",
                    "currency": "GBP"
                }
            }, status_code=200)  # Return 200 instead of 400
        
        logger.info(f"File size: {len(contents)} bytes")
        
        # Reset file stream for potential reuse
        try:
            await file.seek(0)
        except Exception as seek_error:
            logger.warning(f"⚠️ Could not reset file stream: {seek_error}")
        
        # Process based on file type
        if file.filename and is_pdf_file(file.filename):
            logger.info(f"Processing PDF file: {file.filename}")
            result = await process_pdf_with_ocr(contents, file.filename, confidence_threshold, debug)
        else:
            logger.info(f"Processing image file: {file.filename}")
            result = await process_image_with_ocr(contents, file.filename or "unknown", confidence_threshold, debug)
        
        # Extract key information
        doc_type = result.get('document_type', 'unknown')
        confidence = result.get('confidence_score', 0)
        parsed_fields = result.get('parsed_data', {})
        
        # Log the full OCR output for debugging
        logger.info(f"📄 Full OCR output for {file.filename}:")
        logger.info(f"Document type: {doc_type}")
        logger.info(f"Confidence: {confidence}%")
        logger.info(f"Parsed fields: {parsed_fields}")
        if 'raw_lines' in result:
            logger.info(f"Raw OCR lines: {result['raw_lines']}")
        
        # Format response according to specification
        response = {
            "success": True,
            "document_type": doc_type,
            "confidence_score": confidence,  # Add confidence score to response
            "data": {
                "supplier_name": str(parsed_fields.get('supplier_name', 'Unknown Supplier')),
                "invoice_number": str(parsed_fields.get('invoice_number', 'Unknown')),
                "invoice_date": str(parsed_fields.get('invoice_date', 'Unknown')),
                "total_amount": str(parsed_fields.get('total_amount', '0.00')),
                "currency": str(parsed_fields.get('currency', 'GBP'))
            }
        }
        
        logger.info(f"✅ OCR parse completed successfully for {file.filename}")
        return JSONResponse(response, status_code=200)
        
    except ValueError as e:
        # Handle validation errors (empty file, corrupt file, etc.)
        error_msg = str(e)
        logger.error(f"Validation error in OCR parsing: {error_msg}")
        
        # Provide more specific error messages
        if "empty" in error_msg.lower():
            error_msg = "The uploaded file appears to be empty or contains no data"
        elif "corrupt" in error_msg.lower():
            error_msg = "The uploaded file appears to be corrupt or in an unsupported format"
        elif "pdf" in error_msg.lower() and "valid" in error_msg.lower():
            error_msg = "The uploaded file does not appear to be a valid PDF document"
        elif "text" in error_msg.lower() and "detected" in error_msg.lower():
            error_msg = "No readable text was detected in the uploaded document"
        
        return JSONResponse({
            "success": False,
            "error": error_msg,
            "document_type": "unknown",
            "confidence_score": 0,  # Add confidence score to error response
            "data": {
                "supplier_name": "OCR Processing Failed",
                "invoice_number": "Unknown",
                "invoice_date": "Unknown", 
                "total_amount": "0.00",
                "currency": "GBP"
            }
        }, status_code=200)  # Return 200 instead of 400
        
    except Exception as e:
        # Handle unexpected errors
        error_msg = str(e)
        logger.error(f"Unexpected error in OCR parsing: {error_msg}")
        logger.error(f"Unexpected error traceback: {traceback.format_exc()}")
        
        # Check for specific error types
        if "poppler" in error_msg.lower():
            error_msg = "Unable to process PDF: Poppler missing"
        elif "tesseract" in error_msg.lower():
            error_msg = "OCR processing failed: Tesseract error"
        else:
            error_msg = "An unexpected error occurred during OCR processing"
        
        return JSONResponse({
            "success": False,
            "error": error_msg,
            "document_type": "unknown",
            "confidence_score": 0,  # Add confidence score to error response
            "data": {
                "supplier_name": "OCR Processing Failed",
                "invoice_number": "Unknown",
                "invoice_date": "Unknown", 
                "total_amount": "0.00",
                "currency": "GBP"
            }
        }, status_code=200)  # Return 200 instead of 500

def get_classification_notes(doc_type: str, confidence: int, parsed_fields: dict) -> str:
    """Generate helpful notes about the classification result"""
    if doc_type == 'unknown':
        return "Document could not be classified automatically. Please review manually."
    elif confidence < 50:
        return f"Low confidence classification ({confidence}%). Some fields may be inaccurate."
    elif confidence < 70:
        return f"Medium confidence classification ({confidence}%). Please verify extracted data."
    else:
        return f"High confidence classification ({confidence}%). Data extraction appears reliable."

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
    Returns document type (invoice, delivery_note, unknown) with confidence score and reasons.
    """
    logger.info(f"Received document classification request for file: {file.filename}")
    
    # Validate file
    validate_file(file)
    
    try:
        # Parse document with OCR
        result = await parse_with_ocr(file, confidence_threshold)
        
        # Use new deterministic classifier
        from backend.ocr.document_type_classifier import classify_document_type
        
        # Extract text from OCR result
        raw_text = result.get('raw_lines', [])
        full_text = "\n".join(raw_text) if raw_text else ""
        
        # Classify using new classifier
        if full_text:
            classification = classify_document_type(full_text)
            doc_type = classification.doc_type
            classification_confidence = classification.confidence
            doc_type_reasons = classification.reasons
        else:
            doc_type = 'unknown'
            classification_confidence = 0.0
            doc_type_reasons = ["No text extracted from document"]
        
        parsed_data = result.get('parsed_data', {})
        
        logger.info(f"Document classification completed: {doc_type} with confidence {classification_confidence}")
        
        return {
            "type": doc_type,
            "confidence": classification_confidence,
            "reasons": doc_type_reasons,
            "parsed_data": parsed_data,
            "raw_text": raw_text,
            "ocr_confidence": result.get('confidence_score', 0)
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

@router.post("/ocr/check-duplicate")
async def check_duplicate_document(file: UploadFile = File(...), threshold: float = 0.95):
    """
    Check if uploaded document is a duplicate of existing documents.
    
    Args:
        file: Uploaded document file
        threshold: Similarity threshold for duplicate detection (0.0 to 1.0)
    
    Returns:
        JSON response with duplicate detection results
    """
    logger.info(f"Received duplicate check request for file: {file.filename} (threshold: {threshold})")
    
    # Validate file
    validate_file(file)
    
    try:
        # Parse the uploaded document
        parsed_data = await parse_with_ocr(file, threshold=70, debug=False)
        
        # Get existing documents from doc_store (import from upload.py)
        from .upload import doc_store
        
        # Check for duplicates in both invoices and delivery notes
        all_existing_docs = []
        
        # Add invoices
        for inv in doc_store.get('invoices', []):
            all_existing_docs.append({
                'type': 'invoice',
                'parsed_data': inv.get('parsed_data', {}),
                'filename': inv.get('filename', ''),
                'status': inv.get('status', ''),
                'uploaded_at': inv.get('uploaded_at', '')
            })
        
        # Add delivery notes
        for dn in doc_store.get('delivery_notes', []):
            all_existing_docs.append({
                'type': 'delivery_note',
                'parsed_data': dn.get('parsed_data', {}),
                'filename': dn.get('filename', ''),
                'status': dn.get('status', ''),
                'uploaded_at': dn.get('uploaded_at', '')
            })
        
        # Perform duplicate detection
        duplicate_info = detect_duplicate_document(parsed_data, all_existing_docs, threshold)
        
        result = {
            "success": True,
            "is_duplicate": duplicate_info is not None,
            "original_filename": file.filename,
            "file_size": file.size,
            "processed_at": datetime.now().isoformat(),
            "parsed_data": parsed_data.get('parsed_data', {}),
            "document_type": parsed_data.get('document_type', 'unknown'),
            "confidence_score": parsed_data.get('confidence_score', 0)
        }
        
        if duplicate_info:
            result.update({
                "duplicate_info": {
                    "existing_doc": {
                        "filename": duplicate_info['existing_doc'].get('filename', ''),
                        "type": duplicate_info['existing_doc'].get('type', ''),
                        "status": duplicate_info['existing_doc'].get('status', ''),
                        "uploaded_at": duplicate_info['existing_doc'].get('uploaded_at', ''),
                        "parsed_data": duplicate_info['existing_doc'].get('parsed_data', {})
                    },
                    "similarity_score": duplicate_info['similarity_score'],
                    "matching_fields": duplicate_info['matching_fields'],
                    "differences": duplicate_info['differences']
                }
            })
        
        logger.info(f"Duplicate check completed for {file.filename}. Is duplicate: {duplicate_info is not None}")
        return JSONResponse(result)
        
    except Exception as e:
        logger.error(f"Error in duplicate check: {str(e)}")
        error_result = {
            "success": False,
            "is_duplicate": False,
            "error": str(e),
            "original_filename": file.filename,
            "file_size": file.size,
            "processed_at": datetime.now().isoformat()
        }
        return JSONResponse(error_result, status_code=500)

def process_invoice_ocr(file_path: str):
    """Process invoice OCR using PyMuPDF for PDF processing"""
    try:
        text_output = []
        
        # 1. Validate file exists
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return {"success": False, "error": "File not found"}

        # 2. Validate PDF header
        with open(file_path, 'rb') as f:
            header = f.read(4)
            if header != b'%PDF':
                logger.error(f"Invalid PDF header for file: {file_path}")
                raise ValueError("Invalid PDF file")

        # 3. Open PDF with fitz (PyMuPDF)
        with fitz.open(file_path) as doc:
            if doc.page_count == 0:
                logger.warning(f"PDF has 0 pages: {file_path}")
                return {"success": False, "error": "PDF has 0 pages"}
            
            for i in range(doc.page_count):
                try:
                    page = doc.load_page(i)
                    # Use the correct PyMuPDF API - get_pixmap() is the correct method
                    pix = page.get_pixmap(alpha=False)  # type: ignore
                    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                    ocr_text = pytesseract.image_to_string(img)
                    text_output.append(ocr_text)
                except Exception as page_err:
                    logger.error(f"Failed to OCR page {i+1} of {file_path}: {page_err}")
                    continue
                    
        if not text_output:
            logger.error(f"No text extracted from PDF: {file_path}")
            return {"success": False, "error": "No text extracted from PDF"}
            
        return '\n'.join(text_output)
    except FileNotFoundError as fnf:
        logger.error(fnf)
        return {"success": False, "error": str(fnf)}
    except ValueError as ve:
        logger.error(ve)
        return {"success": False, "error": str(ve)}
    except Exception as e:
        logger.error(f"OCR failed for {file_path}: {e}")
        return {"success": False, "error": f"OCR failed: {e}"}

@router.post("/ocr/enhanced")
async def parse_document_enhanced(file: UploadFile = File(...), confidence_threshold: int = 70, debug: bool = False):
    """
    Enhanced OCR processing using the improved pipeline with better preprocessing.
    
    This endpoint uses the enhanced OCR pipeline which includes:
    - Advanced image preprocessing (deskew, noise reduction, thresholding)
    - Structured line item extraction
    - Confidence scoring with review flags
    - Better handling of rotated or poor quality documents
    """
    if not ENHANCED_OCR_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="Enhanced OCR pipeline not available. Please ensure all dependencies are installed."
        )
    
    # Validate file
    validate_file(file)
    
    # Get safe values for filename and file_size
    filename = file.filename or "unknown_file"
    file_size = file.size or 0
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Use enhanced OCR pipeline
            enhanced_result = enhanced_parse_document(temp_file_path)
            
            if not enhanced_result:
                return create_safe_response(
                    filename=filename,
                    file_size=file_size,
                    success=False,
                    error="Enhanced OCR processing failed - no results returned"
                )
            
            # Extract structured data
            text = enhanced_result.get("text", "")
            line_items = enhanced_result.get("line_items", [])
            total = enhanced_result.get("total", "")
            confidence = enhanced_result.get("confidence", 0.0)
            flag_for_review = enhanced_result.get("flag_for_review", False)
            
            # Classify document type
            document_type = detect_document_type(text)
            
            # Extract additional fields using existing logic
            text_lines = text.split('\n') if text else []
            
            if document_type == "invoice":
                parsed_fields = extract_invoice_fields(text_lines)
            elif document_type == "delivery_note":
                parsed_fields = extract_delivery_note_fields(text_lines)
            else:
                parsed_fields = {
                    "supplier_name": "Unknown",
                    "invoice_number": "Unknown",
                    "invoice_date": "Unknown",
                    "total_amount": total or "0.0"
                }
            
            # Add enhanced OCR specific fields
            parsed_fields.update({
                "line_items": line_items,
                "ocr_confidence": confidence,
                "flag_for_review": flag_for_review,
                "enhanced_processing": True
            })
            
            # Save debug data if requested
            if debug:
                save_debug_data(enhanced_result, text, filename, debug=True)
            
            return create_safe_response(
                filename=filename,
                file_size=file_size,
                success=True,
                document_type=document_type,
                confidence_score=confidence,
                parsed_data=parsed_fields,
                full_text=text,
                enhanced_processing=True,
                flag_for_review=flag_for_review,
                line_items_count=len(line_items)
            )
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        logger.error(f"Enhanced OCR processing failed for {filename}: {str(e)}")
        logger.error(traceback.format_exc())
        return create_safe_response(
            filename=filename,
            file_size=file_size,
            success=False,
            error=f"Enhanced OCR processing failed: {str(e)}"
        )

def detect_multiple_invoices(page_results: List[Dict]) -> List[Dict]:
    """
    Detect if a PDF contains multiple invoices by analyzing each page.
    
    Args:
        page_results: List of page results from OCR processing
        
    Returns:
        List of detected invoice sections with their page numbers and content
    """
    try:
        if not page_results or len(page_results) <= 1:
            return []
            
        logger.info(f"🔍 Analyzing {len(page_results)} pages for multiple invoices")
        
        detected_invoices = []
        
        for page_result in page_results:
            page_num = page_result['page']
            page_lines = page_result['lines']
            page_text = '\n'.join(page_lines)
            
            # Check if this page contains invoice header indicators
            invoice_indicators = [
                "invoice number", "invoice no", "invoice #", "inv number", "inv no", "inv #",
                "bill number", "bill no", "invoice date", "billing date", "issue date"
            ]
            
            # Count invoice indicators on this page
            indicator_count = 0
            for indicator in invoice_indicators:
                if indicator in page_text.lower():
                    indicator_count += 1
            
            # Check for supplier name patterns (usually at the top of invoices)
            supplier_patterns = [
                r'^[A-Z][A-Z\s&]+(?:LTD|LIMITED|INC|LLC|PLC|CO|COMPANY)',
                r'^[A-Z][A-Z\s&]+(?:ENERGY|GAS|WATER|ELECTRIC|TELECOM)',
                r'^[A-Z][A-Z\s&]+(?:INSURANCE|BANK|FINANCE)'
            ]
            
            supplier_found = False
            for pattern in supplier_patterns:
                if re.search(pattern, page_text, re.MULTILINE | re.IGNORECASE):
                    supplier_found = True
                    break
            
            # Check for total amount patterns (usually at the bottom of invoices)
            total_patterns = [
                r'total[^\d]*[\d,]+\.?\d*',
                r'amount[^\d]*[\d,]+\.?\d*',
                r'[\d,]+\.?\d*\s*total',
                r'[\d,]+\.?\d*\s*amount'
            ]
            
            total_found = False
            for pattern in total_patterns:
                if re.search(pattern, page_text, re.IGNORECASE):
                    total_found = True
                    break
            
            # Determine if this page is likely a separate invoice
            is_separate_invoice = False
            
            if indicator_count >= 2:
                logger.info(f"🔍 Page {page_num}: {indicator_count} invoice indicators found")
                is_separate_invoice = True
            elif supplier_found and total_found:
                logger.info(f"🔍 Page {page_num}: Supplier and total amount found")
                is_separate_invoice = True
            elif len(page_lines) > 20 and indicator_count >= 1:
                # Long page with at least one invoice indicator
                logger.info(f"🔍 Page {page_num}: Long page ({len(page_lines)} lines) with invoice indicator")
                is_separate_invoice = True
            
            if is_separate_invoice:
                detected_invoices.append({
                    'page_number': page_num,
                    'lines': page_lines,
                    'text': page_text,
                    'confidence': page_result.get('confidence', 0),
                    'indicators_found': indicator_count,
                    'has_supplier': supplier_found,
                    'has_total': total_found
                })
                logger.info(f"✅ Page {page_num} identified as separate invoice")
        
        logger.info(f"🔍 Detected {len(detected_invoices)} separate invoices in PDF")
        return detected_invoices
        
    except Exception as e:
        logger.error(f"❌ Multiple invoice detection failed: {str(e)}")
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        return []