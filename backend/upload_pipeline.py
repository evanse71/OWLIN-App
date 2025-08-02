"""
Unified Upload Pipeline for Document Processing

This module serves as the single entry point for all document processing,
providing consistent handling of PDF and image files with enhanced OCR.

Key Features:
- PDF to image conversion using pypdfium2
- Unified OCR processing with PaddleOCR primary and Tesseract fallback
- Confidence scoring and manual review logic
- Template parsing and metadata extraction
- Role-based processing workflows
- Comprehensive error handling and logging

Author: OWLIN Development Team
Version: 1.0.0
"""

import os
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
import uuid

# PDF processing
import pypdfium2 as pdfium
from PIL import Image
import io

# OCR imports
try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    PaddleOCR = None

import pytesseract
import cv2
import numpy as np

# Local imports
from .ocr.ocr_engine import preprocess_image, deskew_image, apply_adaptive_threshold
from .ocr.ocr_processing import run_ocr_with_fallback, validate_ocr_results, get_ocr_summary
from .ocr.parse_invoice import parse_invoice, ParsedInvoice, LineItem
from .ocr.parse_delivery_note import parse_delivery_note, ParsedDeliveryNote, DeliveryLineItem
from .upload_validator import validate_upload, get_validation_summary, create_upload_metadata
from .db_manager import (
    init_db, save_invoice, save_delivery_note, save_file_hash,
    check_duplicate_invoice, check_duplicate_file_hash, log_processing_result
)

logger = logging.getLogger(__name__)

# Configuration constants
CONFIDENCE_RERUN_THRESHOLD = 0.70  # Trigger pre-processing if below this
CONFIDENCE_REVIEW_THRESHOLD = 0.65  # Flag for manual review if below this
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB limit
SKIP_SECOND_OCR_PASS = False  # Enable preprocessed OCR for better low-quality scan handling

# Global PaddleOCR model (lazy initialization)
_ocr_model = None

@dataclass
class OCRResult:
    """Structured OCR result with confidence scoring"""
    text: str
    confidence: float
    bounding_box: List[Tuple[int, int]]  # Polygon coordinates
    page_number: int
    field_type: Optional[str] = None  # 'supplier', 'date', 'invoice_number', etc.

@dataclass
class ParsedInvoice:
    """Structured invoice data"""
    invoice_number: str
    date: str
    supplier: str
    net_total: float
    vat_total: float
    gross_total: float
    line_items: List[Dict[str, Any]]
    confidence: float

@dataclass
class LineItem:
    """Individual line item from invoice"""
    description: str
    quantity: float
    unit_price: float
    total_price: float

def get_paddle_ocr_model() -> Optional[PaddleOCR]:
    """Lazy initialization of PaddleOCR model"""
    global _ocr_model
    
    if _ocr_model is None and PADDLEOCR_AVAILABLE:
        try:
            _ocr_model = PaddleOCR(
                use_angle_cls=True,
                lang='en'
            )
            logger.info("✅ PaddleOCR model initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize PaddleOCR: {e}")
            _ocr_model = None
    
    return _ocr_model

def check_ocr_engines() -> Dict[str, bool]:
    """Check availability of OCR engines and provide diagnostic information."""
    diagnostics = {}
    
    # Check PaddleOCR
    try:
        if PADDLEOCR_AVAILABLE:
            model = get_paddle_ocr_model()
            diagnostics['paddleocr'] = model is not None
            if model:
                logger.info("✅ PaddleOCR: Available and initialized")
            else:
                logger.warning("⚠️ PaddleOCR: Available but failed to initialize")
        else:
            diagnostics['paddleocr'] = False
            logger.warning("⚠️ PaddleOCR: Not available (package not installed)")
    except Exception as e:
        diagnostics['paddleocr'] = False
        logger.error(f"❌ PaddleOCR: Error checking availability: {e}")
    
    # Check Tesseract
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        diagnostics['tesseract'] = True
        logger.info(f"✅ Tesseract: Available (version {version})")
    except Exception as e:
        diagnostics['tesseract'] = False
        logger.error(f"❌ Tesseract: Not available or not configured: {e}")
    
    # Log overall status
    available_engines = sum(diagnostics.values())
    if available_engines == 0:
        logger.error("❌ No OCR engines available! Install PaddleOCR or Tesseract.")
    elif available_engines == 1:
        logger.warning("⚠️ Only one OCR engine available - limited fallback capability")
    else:
        logger.info("✅ Multiple OCR engines available - good fallback capability")
    
    return diagnostics

def convert_pdf_to_images(file_path: str) -> List[Image.Image]:
    """
    Convert PDF pages to PIL Images using pypdfium2
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        List of PIL Images, one per page
    """
    try:
        logger.info(f"🔄 Converting PDF to images: {file_path}")
        
        # Load PDF with pypdfium2
        pdf = pdfium.PdfDocument(file_path)
        images = []
        
        for page_num in range(len(pdf)):
            logger.debug(f"📄 Processing page {page_num + 1}")
            
            # Get page
            page = pdf.get_page(page_num)
            
            # Render page to image (reduced DPI to speed up processing)
            bitmap = page.render(scale=150/72)  # 150 DPI instead of 300 DPI for faster processing
            pil_image = bitmap.to_pil()
            
            images.append(pil_image)
            logger.debug(f"✅ Page {page_num + 1} converted: {pil_image.size}")
        
        pdf.close()
        logger.info(f"✅ PDF conversion completed: {len(images)} pages")
        return images
        
    except Exception as e:
        logger.error(f"❌ PDF conversion failed: {e}")
        raise Exception(f"PDF conversion failed: {str(e)}")

def run_invoice_ocr(image: Image.Image, page_number: int = 1) -> List[OCRResult]:
    """
    Run enhanced OCR on a single image with confidence scoring
    
    Args:
        image: PIL Image to process
        page_number: Page number for tracking
        
    Returns:
        List of OCRResult objects with confidence scores
    """
    logger.info(f"🔄 Starting OCR for page {page_number}")
    
    # Try PaddleOCR first
    try:
        model = get_paddle_ocr_model()
        if model:
            logger.info(f"📄 Using PaddleOCR for page {page_number}")
            
            # Run PaddleOCR
            results = model.ocr(image, cls=True)
            
            if results and results[0]:
                ocr_results = []
                total_confidence = 0
                word_count = 0
                
                for line in results[0]:
                    if len(line) >= 2:
                        text = line[1][0].strip()
                        confidence = line[1][1]
                        
                        if text:  # Only process non-empty text
                            # Convert bounding box to polygon format
                            bbox = line[0]
                            polygon = [(int(bbox[0][0]), int(bbox[0][1])),
                                     (int(bbox[1][0]), int(bbox[1][1])),
                                     (int(bbox[2][0]), int(bbox[2][1])),
                                     (int(bbox[3][0]), int(bbox[3][1]))]
                            
                            result = OCRResult(
                                text=text,
                                confidence=confidence,
                                bounding_box=polygon,
                                page_number=page_number
                            )
                            ocr_results.append(result)
                            total_confidence += confidence
                            word_count += len(text.split())
                
                avg_confidence = total_confidence / len(ocr_results) if ocr_results else 0
                logger.info(f"✅ PaddleOCR page {page_number}: {len(ocr_results)} text blocks, {word_count} words, avg confidence: {avg_confidence:.3f}")
                
                if ocr_results:
                    # Log sample text
                    sample_texts = [r.text for r in ocr_results[:3]]
                    logger.debug(f"🟡 Page {page_number} sample text: {sample_texts}")
                    return ocr_results
                else:
                    logger.warning(f"⚠️ PaddleOCR page {page_number}: No text detected")
                    
    except Exception as e:
        logger.warning(f"⚠️ PaddleOCR failed: {e}")
    
    # Try pre-processed image if confidence is low
    try:
        logger.info(f"🔄 Trying pre-processed PaddleOCR for page {page_number}")
        
        # Pre-process image for better OCR
        from PIL import ImageEnhance, ImageFilter
        enhanced = image.convert('L')  # Convert to grayscale
        enhanced = ImageEnhance.Contrast(enhanced).enhance(2.0)  # Increase contrast
        enhanced = ImageEnhance.Sharpness(enhanced).enhance(2.0)  # Increase sharpness
        enhanced = enhanced.filter(ImageFilter.MedianFilter(size=3))  # Reduce noise
        
        model = get_paddle_ocr_model()
        if model:
            results = model.ocr(enhanced, cls=True)
            
            if results and results[0]:
                ocr_results = []
                total_confidence = 0
                word_count = 0
                
                for line in results[0]:
                    if len(line) >= 2:
                        text = line[1][0].strip()
                        confidence = line[1][1]
                        
                        if text:
                            bbox = line[0]
                            polygon = [(int(bbox[0][0]), int(bbox[0][1])),
                                     (int(bbox[1][0]), int(bbox[1][1])),
                                     (int(bbox[2][0]), int(bbox[2][1])),
                                     (int(bbox[3][0]), int(bbox[3][1]))]
                            
                            result = OCRResult(
                                text=text,
                                confidence=confidence,
                                bounding_box=polygon,
                                page_number=page_number
                            )
                            ocr_results.append(result)
                            total_confidence += confidence
                            word_count += len(text.split())
                
                avg_confidence = total_confidence / len(ocr_results) if ocr_results else 0
                logger.info(f"✅ Pre-processed PaddleOCR page {page_number}: {len(ocr_results)} text blocks, {word_count} words, avg confidence: {avg_confidence:.3f}")
                
                if ocr_results:
                    sample_texts = [r.text for r in ocr_results[:3]]
                    logger.debug(f"🟡 Page {page_number} pre-processed sample text: {sample_texts}")
                    return ocr_results
                    
    except Exception as e:
        logger.warning(f"⚠️ Pre-processed PaddleOCR failed: {e}")
    
    # Fallback to Tesseract
    logger.warning(f"⚠️ Falling back to Tesseract OCR for page {page_number}")
    return _extract_with_tesseract(image, page_number)

def _extract_with_tesseract(image: Image.Image, page_number: int) -> List[OCRResult]:
    """
    Extract text using Tesseract OCR with confidence scoring
    
    Args:
        image: PIL Image to process
        page_number: Page number for tracking
        
    Returns:
        List of OCRResult objects
    """
    logger.info(f"🔄 Using Tesseract OCR for page {page_number}")
    
    try:
        import pytesseract
        
        # Get OCR data with confidence scores
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        
        results = []
        total_confidence = 0
        word_count = 0
        minus_one_count = 0
        
        for i in range(len(data['text'])):
            text = data['text'][i].strip()
            if text:  # Only process non-empty text
                raw_confidence = data['conf'][i]
                if raw_confidence == "-1":
                    minus_one_count += 1
                    # Skip "-1" confidence results entirely instead of converting to 0.0
                    logger.debug(f"🟡 Skipping low-confidence text: '{text[:20]}...' (confidence: -1)")
                    continue
                else:
                    try:
                        confidence = float(raw_confidence) / 100.0  # Convert 0-100 to 0-1 scale
                    except (ValueError, TypeError):
                        logger.warning(f"⚠️ Invalid confidence value: {raw_confidence}, skipping")
                        continue
                
                # Create bounding box from coordinates
                x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                bounding_box = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
                
                result = OCRResult(
                    text=text,
                    confidence=confidence,
                    bounding_box=bounding_box,
                    page_number=page_number
                )
                results.append(result)
                total_confidence += confidence
                word_count += len(text.split())
        
        # Log statistics
        if minus_one_count > 0:
            logger.warning(f"⚠️ Skipped {minus_one_count} low-confidence results (confidence: -1)")
        
        if results:
            avg_confidence = total_confidence / len(results)
            logger.info(f"✅ Tesseract page {page_number}: {len(results)} text blocks, {word_count} words, avg confidence: {avg_confidence:.3f}")
            
            # Log sample text
            sample_texts = [r.text for r in results[:3]]
            logger.debug(f"🟡 Page {page_number} Tesseract sample text: {sample_texts}")
            
            return results
        else:
            if minus_one_count > 0:
                logger.error(f"❌ Tesseract found {minus_one_count} text segments but all had low confidence (-1)")
                raise Exception("OCR failed - all detected text had low confidence. Image may be too poor quality.")
            else:
                logger.error(f"❌ Tesseract found no text on page {page_number}")
                raise Exception("OCR failed - no text detected. Image may be too poor quality.")
                
    except Exception as e:
        logger.error(f"❌ Tesseract OCR failed for page {page_number}: {e}")
        raise Exception(f"Tesseract OCR failed: {str(e)}")

def assign_field_types(ocr_results: List[OCRResult]) -> List[OCRResult]:
    """
    Assign field types to OCR results based on keywords and position
    
    Args:
        ocr_results: List of OCR results
        
    Returns:
        List of OCR results with field types assigned
    """
    field_keywords = {
        'supplier': ['supplier', 'vendor', 'company', 'business', 'ltd', 'limited', 'plc'],
        'date': ['date', 'invoice date', 'issued', 'created'],
        'invoice_number': ['invoice', 'inv', 'number', 'no', 'ref', 'reference'],
        'net': ['net', 'subtotal', 'amount'],
        'vat': ['vat', 'tax', 'gst'],
        'total': ['total', 'amount due', 'grand total', 'sum']
    }
    
    for result in ocr_results:
        text_lower = result.text.lower()
        
        # Check for field type based on keywords
        for field_type, keywords in field_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                result.field_type = field_type
                break
    
    return ocr_results

def save_debug_artifacts(image: Image.Image, ocr_results: List[OCRResult], 
                        page_number: int, filename: str) -> None:
    """
    Save debug artifacts for visual inspection
    
    Args:
        image: Original image
        ocr_results: OCR results
        page_number: Page number
        filename: Original filename
    """
    try:
        debug_dir = Path("data/debug_ocr")
        debug_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate safe filename
        safe_filename = filename.replace('/', '_').replace('\\', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save preprocessed image
        processed_img = preprocess_image(image)
        img_path = debug_dir / f"preprocessed_{safe_filename}_page{page_number}_{timestamp}.png"
        processed_img.save(img_path)
        
        # Save OCR results as JSON
        results_data = []
        for result in ocr_results:
            results_data.append({
                'text': result.text,
                'confidence': result.confidence,
                'bounding_box': result.bounding_box,
                'field_type': result.field_type
            })
        
        json_path = debug_dir / f"ocr_results_{safe_filename}_page{page_number}_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(results_data, f, indent=2)
            
        logger.debug(f"💾 Saved debug artifacts: {img_path}, {json_path}")
        
    except Exception as e:
        logger.warning(f"⚠️ Failed to save debug artifacts: {e}")

def process_document(file_path: str, parse_templates: bool = True, 
                   save_debug: bool = False, validate_upload: bool = True,
                   db_path: str = "data/owlin.db") -> Dict[str, Any]:
    """
    Main document processing function - single entry point for all document processing
    
    Args:
        file_path: Path to document file (PDF or image)
        parse_templates: Whether to parse invoice templates
        save_debug: Whether to save debug artifacts
        validate_upload: Whether to perform upload validation
        db_path: Path to database for duplicate checking
        
    Returns:
        Dictionary with processing results including:
        - ocr_results: List of OCRResult objects
        - confidence_scores: Per-page confidence scores
        - manual_review_required: Boolean flag
        - parsed_invoice: ParsedInvoice object (if parse_templates=True)
        - document_type: 'invoice', 'delivery_note', or 'unknown'
        - processing_time: Processing duration
        - upload_validation: Validation results (if validate_upload=True)
    """
    import time
    start_time = time.time()
    step_times = {}
    
    try:
        logger.info(f"🔄 Starting document processing: {file_path}")
        
        # ✅ Check OCR engines availability
        logger.info("🔍 Checking OCR engines availability...")
        ocr_diagnostics = check_ocr_engines()
        
        # Initialize database
        db_start = time.time()
        init_db(db_path)
        step_times['db_init'] = time.time() - db_start
        
        # Validate file
        validation_start = time.time()
        if not os.path.exists(file_path):
            raise Exception(f"File not found: {file_path}")
        
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            raise Exception(f"File too large: {file_size} bytes (max: {MAX_FILE_SIZE})")
        step_times['validation'] = time.time() - validation_start
        
        # Determine file type and convert to images
        conversion_start = time.time()
        file_ext = Path(file_path).suffix.lower()
        images = []
        
        if file_ext == '.pdf':
            logger.info("📄 Processing PDF file")
            images = convert_pdf_to_images(file_path)
        elif file_ext in ['.jpg', '.jpeg', '.png']:
            logger.info("🖼️ Processing image file")
            image = Image.open(file_path)
            images = [image]
        else:
            raise Exception(f"Unsupported file type: {file_ext}")
        step_times['conversion'] = time.time() - conversion_start
        
        # Process each page
        all_ocr_results = []
        page_confidence_scores = []
        ocr_total_time = 0
        
        for page_num, image in enumerate(images):
            logger.info(f"📄 Processing page {page_num + 1} of {len(images)}")
            page_start = time.time()
            
            # Run OCR with fallback
            page_results = run_invoice_ocr(image, page_num + 1)
            
            # ✅ Add diagnostic logging to verify OCR results count
            logger.debug(f"🟡 Page {page_num + 1} OCR results: {len(page_results)}")
            
            # If no results from PaddleOCR, try fallback
            if not page_results:
                logger.warning(f"⚠️ PaddleOCR failed for page {page_num + 1}, trying fallback...")
                # Convert image to temporary file for fallback OCR
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                    image.save(tmp_file.name)
                    fallback_results = run_ocr_with_fallback(tmp_file.name, use_paddle_first=False)
                    # Convert fallback results to OCRResult format
                    page_results = []
                    for result in fallback_results:
                        if result.get('page_num') == page_num + 1:
                            page_results.append(OCRResult(
                                text=result['text'],
                                confidence=result['confidence'] / 100.0,  # Convert from 0-100 to 0-1
                                bounding_box=result['bbox'],
                                page_number=result['page_num']
                            ))
                    os.unlink(tmp_file.name)  # Clean up temp file
                
                # ✅ Add diagnostic logging for fallback results
                logger.debug(f"🟡 Page {page_num + 1} fallback OCR results: {len(page_results)}")
            
            # Assign field types
            page_results = assign_field_types(page_results)
            
            # Calculate page confidence
            if page_results:
                page_confidence = sum(r.confidence for r in page_results) / len(page_results)
                page_confidence_scores.append(page_confidence)
                logger.info(f"📊 Page {page_num + 1} confidence: {page_confidence:.3f}")
            else:
                page_confidence_scores.append(0.0)
                logger.warning(f"⚠️ No OCR results for page {page_num + 1}")
            
            # Save debug artifacts if requested
            if save_debug:
                save_debug_artifacts(image, page_results, page_num + 1, Path(file_path).name)
            
            page_time = time.time() - page_start
            ocr_total_time += page_time
            logger.info(f"⏱️ Page {page_num + 1} processing took {page_time:.2f} seconds")
            
            all_ocr_results.extend(page_results)
        
        step_times['ocr_processing'] = ocr_total_time
        
        # ✅ Raise clear error if no text is found
        if not all_ocr_results:
            error_msg = "OCR failed - no text detected. This may be due to poor image quality, rotation, or unsupported file format."
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg)
        
        # Calculate overall confidence and manual review flag
        overall_confidence = sum(page_confidence_scores) / len(page_confidence_scores) if page_confidence_scores else 0.0
        manual_review_required = any(score < CONFIDENCE_REVIEW_THRESHOLD for score in page_confidence_scores)
        
        # Generate OCR summary
        ocr_summary = get_ocr_summary([
            {
                "text": result.text,
                "confidence": result.confidence * 100,  # Convert to 0-100 scale
                "page_num": result.page_number
            }
            for result in all_ocr_results
        ])
        
        # Parse document template if requested
        parsed_invoice = None
        parsed_delivery_note = None
        
        if parse_templates and all_ocr_results:
            try:
                # Determine document type
                document_type = _classify_document_type(all_ocr_results)
                
                if document_type == 'invoice':
                    # Convert OCR results to text with proper line structure
                    lines = []
                    current_line = []
                    current_y = None
                    
                    # Sort OCR results by Y position to group by lines
                    sorted_results = sorted(all_ocr_results, key=lambda r: r.bounding_box[0][1])
                    
                    for result in sorted_results:
                        y_pos = result.bounding_box[0][1]
                        
                        # If this is a new line (different Y position)
                        if current_y is None or abs(y_pos - current_y) > 10:  # 10 pixel tolerance
                            if current_line:
                                lines.append(' '.join(current_line))
                                current_line = []
                            current_y = y_pos
                        
                        current_line.append(result.text)
                    
                    # Add the last line
                    if current_line:
                        lines.append(' '.join(current_line))
                    
                    full_text = '\n'.join(lines)
                    parsed_invoice = parse_invoice(full_text, overall_confidence)
                    logger.info(f"✅ Invoice parsed: {parsed_invoice.invoice_number if parsed_invoice else 'Unknown'}")
                elif document_type == 'delivery_note':
                    # Convert OCR results to text with proper line structure
                    lines = []
                    current_line = []
                    current_y = None
                    
                    # Sort OCR results by Y position to group by lines
                    sorted_results = sorted(all_ocr_results, key=lambda r: r.bounding_box[0][1])
                    
                    for result in sorted_results:
                        y_pos = result.bounding_box[0][1]
                        
                        # If this is a new line (different Y position)
                        if current_y is None or abs(y_pos - current_y) > 10:  # 10 pixel tolerance
                            if current_line:
                                lines.append(' '.join(current_line))
                                current_line = []
                            current_y = y_pos
                        
                        current_line.append(result.text)
                    
                    # Add the last line
                    if current_line:
                        lines.append(' '.join(current_line))
                    
                    full_text = '\n'.join(lines)
                    parsed_delivery_note = parse_delivery_note(full_text, overall_confidence)
                    logger.info(f"✅ Delivery note parsed: {parsed_delivery_note.delivery_number if parsed_delivery_note else 'Unknown'}")
                else:
                    logger.warning(f"⚠️ Unknown document type: {document_type}")
            except Exception as e:
                logger.warning(f"⚠️ Template parsing failed: {e}")
        else:
            # Determine document type without parsing
            document_type = _classify_document_type(all_ocr_results)
        
        processing_time = time.time() - start_time
        
        result = {
            'ocr_results': all_ocr_results,
            'confidence_scores': page_confidence_scores,
            'overall_confidence': overall_confidence,
            'manual_review_required': manual_review_required,
            'document_type': document_type,
            'processing_time': processing_time,
            'pages_processed': len(images),
            'ocr_summary': ocr_summary
        }
        
        if parsed_invoice:
            result['parsed_invoice'] = parsed_invoice
        if parsed_delivery_note:
            result['parsed_delivery_note'] = parsed_delivery_note
        
        # Perform upload validation if requested
        if validate_upload:
            try:
                logger.info("🔍 Performing upload validation...")
                
                # Extract data for validation
                extracted_data = {}
                if parsed_invoice:
                    extracted_data = {
                        'supplier_name': parsed_invoice.supplier,
                        'invoice_number': parsed_invoice.invoice_number,
                        'invoice_date': parsed_invoice.date
                    }
                elif parsed_delivery_note:
                    extracted_data = {
                        'supplier_name': parsed_delivery_note.supplier,
                        'delivery_number': parsed_delivery_note.delivery_number,
                        'invoice_date': parsed_delivery_note.date
                    }
                
                # Run validation
                upload_allowed, validation_messages, validation_data = validate_upload(
                    file_path, extracted_data, db_path
                )
                
                # Add validation results to response
                result['upload_validation'] = {
                    'allowed': upload_allowed,
                    'messages': validation_messages,
                    'validation_data': validation_data,
                    'summary': get_validation_summary(validation_data),
                    'metadata': create_upload_metadata(validation_data)
                }
                
                if upload_allowed:
                    logger.info("✅ Upload validation passed")
                else:
                    logger.warning(f"⚠️ Upload validation failed: {validation_messages.get('error', 'Unknown error')}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Upload validation failed: {e}")
                result['upload_validation'] = {
                    'allowed': True,  # Allow upload if validation fails
                    'messages': {'warning': f'Validation failed: {str(e)}'},
                    'validation_data': {},
                    'summary': {},
                    'metadata': {}
                }
        
        # Save to database if processing was successful
        try:
            if parsed_invoice or parsed_delivery_note:
                # Generate file hash for duplicate detection
                import hashlib
                with open(file_path, 'rb') as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                
                # Save file hash
                save_file_hash(file_hash, file_path, file_size, "application/pdf" if file_ext == '.pdf' else "image/jpeg")
                
                # Save invoice or delivery note data
                if parsed_invoice:
                    # Convert OCR results to text for storage
                    ocr_text = " ".join([r.text for r in all_ocr_results])
                    
                    # Convert line items to list of dictionaries
                    line_items_data = []
                    for item in parsed_invoice.line_items:
                        line_items_data.append({
                            'description': item.description,
                            'quantity': item.quantity,
                            'unit_price': item.unit_price,
                            'total_price': item.total_price,
                            'confidence': item.confidence
                        })
                    
                    invoice_data = {
                        'supplier_name': parsed_invoice.supplier,
                        'invoice_number': parsed_invoice.invoice_number,
                        'invoice_date': parsed_invoice.date,
                        'net_amount': parsed_invoice.net_total,
                        'vat_amount': parsed_invoice.vat_total,
                        'total_amount': parsed_invoice.gross_total,
                        'currency': 'GBP',  # Default currency
                        'file_path': file_path,
                        'file_hash': file_hash,
                        'ocr_confidence': overall_confidence * 100,  # Convert to 0-100 scale
                        'ocr_text': ocr_text,
                        'page_numbers': list(range(1, len(images) + 1)),  # Page numbers
                        'line_items': line_items_data,
                        'subtotal': parsed_invoice.net_total,
                        'vat': parsed_invoice.vat_total,
                        'vat_rate': parsed_invoice.vat_rate,
                        'total_incl_vat': parsed_invoice.gross_total
                    }
                    save_invoice(invoice_data, db_path)
                    logger.info(f"💾 Invoice saved to database: {parsed_invoice.invoice_number}")
                
                elif parsed_delivery_note:
                    delivery_data = {
                        'supplier_name': parsed_delivery_note.supplier,
                        'delivery_number': parsed_delivery_note.delivery_number,
                        'delivery_date': parsed_delivery_note.date,
                        'total_items': len(parsed_delivery_note.line_items),
                        'file_path': file_path,
                        'file_hash': file_hash,
                        'ocr_confidence': overall_confidence * 100  # Convert to 0-100 scale
                    }
                    save_delivery_note(delivery_data, db_path)
                    logger.info(f"💾 Delivery note saved to database: {parsed_delivery_note.delivery_number}")
                
                # Log processing result
                log_processing_result(
                    file_path=file_path,
                    status='success',
                    ocr_confidence=overall_confidence * 100,
                    processing_time=processing_time
                )
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to save to database: {e}")
            # Log processing result with error
            log_processing_result(
                file_path=file_path,
                status='error',
                error_message=str(e),
                processing_time=processing_time
            )
        
        logger.info(f"✅ Document processing completed in {processing_time:.2f}s")
        logger.info(f"📊 Overall confidence: {overall_confidence:.3f}")
        logger.info(f"🔍 Manual review required: {manual_review_required}")
        
        # Log detailed timing breakdown
        logger.info("⏱️ Processing time breakdown:")
        for step, duration in step_times.items():
            percentage = (duration / processing_time) * 100 if processing_time > 0 else 0
            logger.info(f"   {step}: {duration:.2f}s ({percentage:.1f}%)")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Document processing failed: {e}")
        raise Exception(f"Document processing failed: {str(e)}")

def _classify_document_type(ocr_results: List[OCRResult]) -> str:
    """
    Classify document type based on OCR content
    
    Args:
        ocr_results: List of OCR results
        
    Returns:
        Document type: 'invoice', 'delivery_note', or 'unknown'
    """
    if not ocr_results:
        return 'unknown'
    
    # Combine all text
    full_text = " ".join(result.text.lower() for result in ocr_results)
    
    # Invoice keywords
    invoice_keywords = ['invoice', 'tax', 'vat', 'total', 'amount due', 'payment']
    invoice_count = sum(1 for keyword in invoice_keywords if keyword in full_text)
    
    # Delivery note keywords
    delivery_keywords = ['delivery note', 'goods received', 'pod', 'driver', 'delivery date']
    delivery_count = sum(1 for keyword in delivery_keywords if keyword in full_text)
    
    if invoice_count > delivery_count:
        return 'invoice'
    elif delivery_count > invoice_count:
        return 'delivery_note'
    else:
        return 'unknown' 