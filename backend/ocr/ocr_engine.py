import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import io
import logging
import cv2
import numpy as np
from typing import Tuple, List, Dict, Any
import re
import os
import datetime
import logging
from pdf2image import convert_from_path

logger = logging.getLogger(__name__)

def extract_text_from_pdf(filepath: str) -> str:
    """
    Extract text from PDF using enhanced OCR with Tesseract 5+.
    
    Args:
        filepath: Path to the PDF file
        
    Returns:
        Extracted text as string
    """
    try:
        doc = fitz.open(filepath)
        full_text = ""

        for page_num, page in enumerate(doc):
            logger.info(f"Processing page {page_num + 1} of {len(doc)}")
            
            # Convert page to high-resolution image
            pix = page.get_pixmap(dpi=300)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # Enhanced preprocessing
            processed_img = preprocess_image(img)
            
            # Extract text using enhanced Tesseract settings
            text = extract_text_with_enhanced_ocr(processed_img)
            full_text += text + "\n\n"

        doc.close()
        return full_text.strip()
        
    except Exception as e:
        logger.error(f"Error extracting text from PDF {filepath}: {str(e)}")
        raise Exception(f"OCR extraction failed: {str(e)}")

def preprocess_image(img: Image.Image) -> np.ndarray:
    """Apply comprehensive image preprocessing for better OCR results."""
    try:
        # Convert PIL image to numpy array
        arr = np.array(img)
        if len(arr.shape) == 3:
            gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        else:
            gray = arr
        
        # Deskew the image
        coords = np.column_stack(np.where(gray > 0))
        if coords.shape[0] > 0:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = 90 + angle
            (h, w) = gray.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            deskewed = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        else:
            deskewed = gray
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(deskewed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 11)
        
        # Denoise the image
        denoised = cv2.fastNlMeansDenoising(thresh, None, 30, 7, 21)
        
        return denoised
    except Exception as e:
        logger.warning(f"Preprocessing failed, using original image: {str(e)}")
        return np.array(img.convert('L'))

def deskew_image(image: np.ndarray) -> np.ndarray:
    """
    Deskew the image to correct rotation.
    
    Args:
        image: Grayscale image as numpy array
        
    Returns:
        Deskewed image
    """
    try:
        # Find the angle of rotation
        coords = np.column_stack(np.where(image > 0))
        angle = cv2.minAreaRect(coords)[-1]
        
        # Determine the skew angle
        if angle < -45:
            angle = 90 + angle
        
        # Rotate the image
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        
        return rotated
        
    except Exception as e:
        logger.warning(f"Deskewing failed: {str(e)}")
        return image

def apply_adaptive_threshold(image: np.ndarray) -> np.ndarray:
    """
    Apply adaptive thresholding for better text extraction.
    
    Args:
        image: Grayscale image as numpy array
        
    Returns:
        Thresholded image
    """
    try:
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        return thresh
        
    except Exception as e:
        logger.warning(f"Adaptive thresholding failed: {str(e)}")
        return image

def enhance_contrast(image: np.ndarray) -> np.ndarray:
    """
    Enhance image contrast for better OCR.
    
    Args:
        image: Grayscale image as numpy array
        
    Returns:
        Contrast-enhanced image
    """
    try:
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(image)
        return enhanced
        
    except Exception as e:
        logger.warning(f"Contrast enhancement failed: {str(e)}")
        return image

def remove_noise(image: np.ndarray) -> np.ndarray:
    """
    Remove noise from the image.
    
    Args:
        image: Grayscale image as numpy array
        
    Returns:
        Denoised image
    """
    try:
        # Apply morphological operations to remove noise
        kernel = np.ones((1, 1), np.uint8)
        denoised = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)
        return denoised
        
    except Exception as e:
        logger.warning(f"Noise removal failed: {str(e)}")
        return image

def extract_text_with_enhanced_ocr(img: Image.Image) -> str:
    """
    Extract text using enhanced Tesseract 5+ settings.
    
    Args:
        img: Preprocessed PIL Image
        
    Returns:
        Extracted text
    """
    try:
        # Enhanced Tesseract configuration for invoices
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz£$€%.,()-_/\s'
        
        # Try layout-aware OCR first
        text = pytesseract.image_to_string(
            img, 
            config=custom_config,
            lang='eng'
        )
        
        # If text is too short, try different PSM modes
        if len(text.strip()) < 50:
            # Try PSM 11 (Sparse text with OSD)
            text_psm11 = pytesseract.image_to_string(
                img, 
                config='--oem 3 --psm 11',
                lang='eng'
            )
            
            # Use the longer result
            if len(text_psm11.strip()) > len(text.strip()):
                text = text_psm11
        
        return text
        
    except Exception as e:
        logger.error(f"Enhanced OCR failed: {str(e)}")
        # Fallback to basic OCR
        return pytesseract.image_to_string(img)

def detect_table_structure(img: Image.Image) -> Dict[str, Any]:
    """
    Detect table structure in the image for better line item extraction.
    
    Args:
        img: PIL Image to analyze
        
    Returns:
        Dictionary with table structure information
    """
    try:
        # Convert to numpy array
        img_array = np.array(img)
        
        # Convert to grayscale
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Detect horizontal and vertical lines
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        
        # Detect horizontal lines
        horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel)
        
        # Detect vertical lines
        vertical_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel)
        
        # Combine lines
        table_structure = cv2.addWeighted(horizontal_lines, 0.5, vertical_lines, 0.5, 0.0)
        
        # Find contours
        contours, _ = cv2.findContours(table_structure, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Analyze table structure
        table_info = {
            "has_table": len(contours) > 5,  # Threshold for table detection
            "row_count": 0,
            "column_count": 0,
            "table_areas": []
        }
        
        if table_info["has_table"]:
            # Count potential rows and columns
            table_info["row_count"] = len([c for c in contours if cv2.contourArea(c) > 1000])
            table_info["column_count"] = max(3, len([c for c in contours if cv2.contourArea(c) > 500]))
        
        return table_info
        
    except Exception as e:
        logger.warning(f"Table detection failed: {str(e)}")
        return {"has_table": False, "row_count": 0, "column_count": 0, "table_areas": []}

def run_ocr(pdf_path: str) -> Dict[str, Any]:
    """
    Run OCR on a PDF file with page-by-page processing and debug output.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Dictionary with OCR results per page and overall statistics
    """
    try:
        # Convert PDF to images using pdf2image
        images = convert_from_path(pdf_path, dpi=300)
        
        pages = []
        all_text = []
        total_confidence = 0.0
        total_words = 0
        
        # Ensure logs directory exists
        log_dir = 'data/logs'
        os.makedirs(log_dir, exist_ok=True)
        
        for page_num, img in enumerate(images, 1):
            logger.info(f"Processing page {page_num}")
            
            try:
                # Preprocess the image
                processed_img = preprocess_image(img)
                
                # Save debug image
                debug_image_path = os.path.join(log_dir, f'page{page_num}_clean.png')
                cv2.imwrite(debug_image_path, processed_img)
                
                # Convert back to PIL for tesseract
                pil_img = Image.fromarray(processed_img)
                
                # Run OCR with detailed output
                data = pytesseract.image_to_data(
                    pil_img, 
                    lang='eng', 
                    config='--psm 6 --oem 3',
                    output_type=pytesseract.Output.DICT
                )
                
                # Extract text and calculate confidence
                page_text = ' '.join(data['text'])
                confidences = [float(conf) for conf in data['conf'] if float(conf) > 0]
                
                if confidences:
                    avg_confidence = sum(confidences) / len(confidences) / 100.0  # Normalize to 0-1
                else:
                    avg_confidence = 0.0
                
                word_count = len([text for text in data['text'] if text.strip()])
                
                # Store word-level data for table extraction
                words = []
                for i in range(len(data['text'])):
                    if int(data['conf'][i]) > 0 and data['text'][i].strip():
                        words.append({
                            'text': data['text'][i],
                            'left': data['left'][i],
                            'top': data['top'][i],
                            'width': data['width'][i],
                            'height': data['height'][i],
                            'conf': float(data['conf'][i]),
                            'page': page_num
                        })
                
                page_data = {
                    "page": page_num,
                    "text": page_text,
                    "avg_confidence": round(avg_confidence, 3),
                    "word_count": word_count,
                    "image_debug_path": debug_image_path,
                    "words": words,
                    "word_boxes": words  # Alias for table extraction
                }
                
                pages.append(page_data)
                all_text.append(page_text)
                total_confidence += avg_confidence
                total_words += word_count
                
                logger.info(f"Page {page_num}: {word_count} words, confidence: {avg_confidence:.3f}")
                
            except Exception as page_error:
                logger.error(f"Error processing page {page_num}: {str(page_error)}")
                # Add empty page data for failed pages
                page_data = {
                    "page": page_num,
                    "text": "",
                    "avg_confidence": 0.0,
                    "word_count": 0,
                    "image_debug_path": "",
                    "words": [],
                    "word_boxes": []
                }
                pages.append(page_data)
        
        # Calculate overall confidence
        overall_confidence = total_confidence / len(pages) if pages else 0.0
        
        # Combine all text
        raw_ocr_text = '\n'.join(all_text)
        
        logger.info(f"OCR completed: {len(pages)} pages, {total_words} words, confidence: {overall_confidence:.3f}")
        
        return {
            "pages": pages,
            "raw_ocr_text": raw_ocr_text,
            "overall_confidence": round(overall_confidence, 3),
            "total_pages": len(pages),
            "total_words": total_words
        }
        
    except Exception as e:
        logger.error(f"OCR failed for {pdf_path}: {str(e)}")
        logger.exception("Full traceback:")
        return {
            "pages": [],
            "raw_ocr_text": "",
            "overall_confidence": 0.0,
            "total_pages": 0,
            "total_words": 0
        }

def extract_text_with_table_awareness(filepath: str) -> Tuple[str, Dict[str, Any]]:
    """
    Legacy function for backward compatibility.
    """
    result = run_ocr(filepath)
    return result["raw_ocr_text"], {"has_table": False, "row_count": 0, "column_count": 0}

def calculate_enhanced_confidence(text: str, table_info: Dict[str, Any]) -> float:
    """
    Calculate enhanced confidence score based on text quality and table detection.
    """
    if not text:
        return 0.0
    
    # Base confidence from text length and word count
    word_count = len(text.split())
    if word_count < 10:
        return 0.1
    elif word_count < 50:
        return 0.3
    elif word_count < 100:
        return 0.5
    else:
        base_confidence = 0.7
    
    # Bonus for table detection
    if table_info.get("has_table", False):
        base_confidence += 0.1
    
    # Bonus for invoice keywords
    invoice_keywords = ['invoice', 'bill', 'total', 'amount', 'date', 'supplier', 'customer', 'payment']
    keyword_matches = sum(1 for keyword in invoice_keywords if keyword.lower() in text.lower())
    keyword_bonus = min(keyword_matches * 0.05, 0.2)
    
    # Bonus for price patterns
    price_patterns = [r'£\d+\.\d{2}', r'\$\d+\.\d{2}', r'€\d+\.\d{2}', r'\d+\.\d{2}']
    price_matches = sum(1 for pattern in price_patterns if re.search(pattern, text))
    price_bonus = min(price_matches * 0.02, 0.1)
    
    total_confidence = base_confidence + keyword_bonus + price_bonus
    return min(total_confidence, 1.0)

def calculate_confidence(text: str) -> float:
    """
    Legacy function for backward compatibility.
    """
    return calculate_enhanced_confidence(text, {"has_table": False}) 