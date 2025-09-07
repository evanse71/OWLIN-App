import fitz  # PyMuPDF
try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PaddleOCR = None
    PADDLEOCR_AVAILABLE = False
from PIL import Image, ImageEnhance, ImageFilter
import io
import logging
import cv2
import numpy as np
from typing import Tuple, List, Dict, Any, Optional
import re
import os
import datetime
import logging
import time
from pdf2image import convert_from_path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Configuration constants
CONFIDENCE_RERUN_THRESHOLD = 0.70  # Trigger pre-processing if below this
CONFIDENCE_REVIEW_THRESHOLD = 0.65  # Flag for manual review if below this

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

def run_invoice_ocr(image: Image.Image, page_number: int = 1) -> List[OCRResult]:
    """
    Run enhanced OCR on a single image with confidence scoring
    
    Args:
        image: PIL Image to process
        page_number: Page number for tracking
        
    Returns:
        List of OCRResult objects with confidence scores
    """
    try:
        logger.info(f"🔄 Running OCR on page {page_number}")
        
        # Convert PIL to numpy array
        img_array = np.array(image)
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # First pass: Raw PaddleOCR
        paddle_model = get_paddle_ocr_model()
        raw_results = []
        
        if paddle_model:
            try:
                raw_ocr_results = paddle_model.ocr(img_array)
                if raw_ocr_results and raw_ocr_results[0]:
                    for result in raw_ocr_results[0]:
                        if result and len(result) >= 2:
                            bbox, (text, confidence) = result
                            raw_results.append(OCRResult(
                                text=text,
                                confidence=confidence,
                                bounding_box=bbox,
                                page_number=page_number
                            ))
                
                # Calculate mean confidence
                if raw_results:
                    mean_confidence = sum(r.confidence for r in raw_results) / len(raw_results)
                    logger.info(f"📊 Raw OCR confidence: {mean_confidence:.3f}")
                    
                    # If confidence is good enough, return results
                    if mean_confidence >= CONFIDENCE_RERUN_THRESHOLD:
                        logger.info("✅ Raw OCR results acceptable")
                        return raw_results
                        
            except Exception as e:
                logger.warning(f"⚠️ PaddleOCR failed: {e}")
        
        # Second pass: Pre-processed image
        logger.info("🔄 Running pre-processed OCR")
        processed_img = preprocess_image(image)
        processed_array = np.array(processed_img)
        
        processed_results = []
        if paddle_model:
            try:
                processed_ocr_results = paddle_model.ocr(processed_array)
                if processed_ocr_results and processed_ocr_results[0]:
                    for result in processed_ocr_results[0]:
                        if result and len(result) >= 2:
                            bbox, (text, confidence) = result
                            processed_results.append(OCRResult(
                                text=text,
                                confidence=confidence,
                                bounding_box=bbox,
                                page_number=page_number
                            ))
                            
            except Exception as e:
                logger.warning(f"⚠️ Pre-processed PaddleOCR failed: {e}")
        
        # Choose best results
        if raw_results and processed_results:
            raw_confidence = sum(r.confidence for r in raw_results) / len(raw_results)
            processed_confidence = sum(r.confidence for r in processed_results) / len(processed_results)
            
            if processed_confidence > raw_confidence:
                logger.info(f"✅ Using pre-processed results (confidence: {processed_confidence:.3f})")
                return processed_results
            else:
                logger.info(f"✅ Using raw results (confidence: {raw_confidence:.3f})")
                return raw_results
        elif processed_results:
            logger.info("✅ Using pre-processed results")
            return processed_results
        elif raw_results:
            logger.info("✅ Using raw results")
            return raw_results
        
        # Fallback to Tesseract
        logger.warning("⚠️ Falling back to Tesseract OCR")
        return _extract_with_tesseract(image, page_number)
        
    except Exception as e:
        logger.error(f"❌ OCR processing failed: {e}")
        raise Exception(f"OCR processing failed: {str(e)}")

def _extract_with_tesseract(image: Image.Image, page_number: int) -> List[OCRResult]:
    """
    Fallback OCR using Tesseract
    
    Args:
        image: PIL Image to process
        page_number: Page number for tracking
        
    Returns:
        List of OCRResult objects
    """
    try:
        logger.info("🔄 Running Tesseract fallback OCR")
        
        # Get detailed OCR data from Tesseract
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        
        results = []
        minus_one_count = 0  # Track "-1" confidence values
        
        for i in range(len(data['text'])):
            text = data['text'][i].strip()
            if text:  # Only process non-empty text
                # ✅ Fix confidence calculation: convert string to float and handle "-1"
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
                
                # Create bounding box from Tesseract data
                left = data['left'][i]
                top = data['top'][i]
                width = data['width'][i]
                height = data['height'][i]
                
                bbox = [
                    (left, top),
                    (left + width, top),
                    (left + width, top + height),
                    (left, top + height)
                ]
                
                results.append(OCRResult(
                    text=text,
                    confidence=confidence,
                    bounding_box=bbox,
                    page_number=page_number
                ))
        
        # ✅ Log "-1" confidence count for diagnostics
        if minus_one_count > 0:
            logger.warning(f"⚠️ Skipped {minus_one_count} low-confidence results (confidence: -1)")
        
        # ✅ Raise error if no usable results found
        if not results:
            if minus_one_count > 0:
                logger.error(f"❌ Tesseract found {minus_one_count} text segments but all had low confidence (-1)")
                raise Exception("OCR failed - all detected text had low confidence. Image may be too poor quality.")
            else:
                logger.error("❌ Tesseract found no text in image")
                raise Exception("OCR failed - no text detected in image")
        
        # Log fallback usage
        os.makedirs("data/logs", exist_ok=True)
        with open("data/logs/ocr_fallback.log", "a") as f:
            timestamp = datetime.datetime.now().isoformat()
            f.write(f"{timestamp} - Tesseract fallback used for page {page_number}\n")
        
        # ✅ Add optional logging for average confidence
        if results:
            avg_conf = sum(r.confidence for r in results) / len(results)
            logger.debug(f"🟡 Tesseract fallback average confidence: {avg_conf:.2f}")
        
        logger.info(f"✅ Tesseract fallback completed: {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"❌ Tesseract fallback failed: {e}")
        raise Exception(f"Tesseract fallback failed: {str(e)}")

def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Apply comprehensive image preprocessing for better OCR results.
    
    Args:
        image: PIL Image to preprocess
        
    Returns:
        Preprocessed PIL Image
    """
    try:
        logger.debug("🔄 Starting image preprocessing...")
        
        # Convert PIL image to numpy array
        arr = np.array(image)
        if len(arr.shape) == 3:
            gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        else:
            gray = arr
        
        logger.debug(f"📊 Original image shape: {arr.shape}")
        
        # Apply deskewing
        deskewed = deskew_image(gray)
        logger.debug("✅ Deskewing completed")
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(deskewed)
        logger.debug("✅ CLAHE enhancement completed")
        
        # Apply adaptive thresholding
        thresholded = apply_adaptive_threshold(enhanced)
        logger.debug("✅ Adaptive thresholding completed")
        
        # Remove noise
        denoised = remove_noise(thresholded)
        logger.debug("✅ Noise removal completed")
        
        # Convert back to PIL Image
        result = Image.fromarray(denoised)
        logger.debug("✅ Preprocessing completed")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Image preprocessing failed: {e}")
        # Return original image if preprocessing fails
        return image

def deskew_image(image: np.ndarray) -> np.ndarray:
    """
    Deskew image by detecting and correcting rotation.
    
    Args:
        image: Grayscale image as numpy array
        
    Returns:
        Deskewed image as numpy array
    """
    try:
        # Detect lines using Hough transform
        edges = cv2.Canny(image, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
        
        if lines is None:
            return image
        
        # Calculate angles
        angles = []
        for line in lines:
            rho, theta = line[0]
            angle = theta * 180 / np.pi
            if angle < 45:
                angles.append(angle)
            elif angle > 135:
                angles.append(angle - 180)
        
        if not angles:
            return image
        
        # Calculate median angle for correction
        median_angle = np.median(angles)
        
        # Apply rotation if significant
        if abs(median_angle) > 0.5:
            height, width = image.shape
            center = (width // 2, height // 2)
            rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
            rotated = cv2.warpAffine(image, rotation_matrix, (width, height), 
                                   flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            return rotated
        
        return image
        
    except Exception as e:
        logger.warning(f"⚠️ Deskewing failed: {e}")
        return image

def apply_adaptive_threshold(image: np.ndarray) -> np.ndarray:
    """
    Apply adaptive thresholding to binarize image.
    
    Args:
        image: Grayscale image as numpy array
        
    Returns:
        Binary image as numpy array
    """
    try:
        # Apply adaptive thresholding
        binary = cv2.adaptiveThreshold(
            image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        return binary
        
    except Exception as e:
        logger.warning(f"⚠️ Adaptive thresholding failed: {e}")
        return image

def enhance_contrast(image: np.ndarray) -> np.ndarray:
    """
    Enhance image contrast.
    
    Args:
        image: Grayscale image as numpy array
        
    Returns:
        Enhanced image as numpy array
    """
    try:
        # Apply histogram equalization
        enhanced = cv2.equalizeHist(image)
        return enhanced
        
    except Exception as e:
        logger.warning(f"⚠️ Contrast enhancement failed: {e}")
        return image

def remove_noise(image: np.ndarray) -> np.ndarray:
    """
    Remove noise from image using median filtering.
    
    Args:
        image: Binary image as numpy array
        
    Returns:
        Denoised image as numpy array
    """
    try:
        # Apply median filtering to remove salt-and-pepper noise
        denoised = cv2.medianBlur(image, 3)
        return denoised
        
    except Exception as e:
        logger.warning(f"⚠️ Noise removal failed: {e}")
        return image

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
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
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

# Legacy functions for backward compatibility
def extract_text_from_pdf(filepath: str) -> str:
    """
    Extract text from PDF using enhanced OCR with PaddleOCR.
    
    Args:
        filepath: Path to the PDF file
        
    Returns:
        Extracted text as string
    """
    try:
        logger.info(f"🔄 Starting PDF text extraction: {filepath}")
        doc = fitz.open(filepath)
        full_text = ""

        for page_num, page in enumerate(doc):
            logger.info(f"🔄 Processing page {page_num + 1} of {len(doc)}")
            
            # Convert page to high-resolution image (300 DPI minimum)
            pix = page.get_pixmap(dpi=300)
            logger.debug(f"📊 Page {page_num + 1} converted to image: {pix.width}x{pix.height}")
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            logger.debug(f"📊 Page {page_num + 1} image size: {img.size}")
            
            # Enhanced preprocessing
            processed_img = preprocess_image(img)
            
            # Extract text using PaddleOCR
            ocr_results = run_invoice_ocr(processed_img, page_num + 1)
            text = " ".join(result.text for result in ocr_results)
            full_text += text + "\n\n"
            
            logger.info(f"✅ Page {page_num + 1} completed: {len(text)} characters")

        doc.close()
        logger.info(f"✅ PDF extraction completed: {len(full_text)} total characters")
        return full_text.strip()
        
    except Exception as e:
        logger.error(f"Error extracting text from PDF {filepath}: {str(e)}")
        raise Exception(f"OCR extraction failed: {str(e)}")

def extract_text_with_paddle_ocr(img: Image.Image) -> str:
    """
    Extract text using PaddleOCR with fallback to Tesseract.
    
    Args:
        img: PIL Image to process
        
    Returns:
        Extracted text as string
    """
    try:
        ocr_results = run_invoice_ocr(img)
        return " ".join(result.text for result in ocr_results)
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        return ""

# Import missing modules
import json
from pathlib import Path
import pytesseract

def calculate_display_confidence(raw_confidence: float, word_count: int = 0, text: str = "") -> float:
    """
    Calculate display confidence with enhanced logic.
    
    Args:
        raw_confidence: Raw confidence score from OCR (0.0 to 1.0)
        word_count: Number of words in the text
        text: The extracted text
        
    Returns:
        Display confidence as percentage (0.0 to 100.0)
    """
    # Base confidence calculation
    base_confidence = raw_confidence * 100
    
    # Minimum confidence threshold
    min_confidence = 10.0
    
    # Adjust confidence based on text quality
    if text:
        # Boost confidence for meaningful text
        if len(text.strip()) > 3:
            base_confidence = min(100.0, base_confidence + 5.0)
        
        # Reduce confidence for very short or repetitive text
        if len(text.strip()) < 2:
            base_confidence = max(min_confidence, base_confidence - 10.0)
    
    # Adjust based on word count
    if word_count > 0:
        if word_count >= 5:
            base_confidence = min(100.0, base_confidence + 3.0)
        elif word_count < 2:
            base_confidence = max(min_confidence, base_confidence - 5.0)
    
    # Ensure confidence is within bounds
    return max(min_confidence, min(100.0, base_confidence)) 