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
from typing import Tuple, List, Dict, Any
import re
import os
import datetime
import logging
from pdf2image import convert_from_path

logger = logging.getLogger(__name__)

# Initialize PaddleOCR model (lazy loading for faster startup)
ocr_model = None

def get_ocr_model():
    """Get or initialize the PaddleOCR model (lazy loading)."""
    global ocr_model
    if ocr_model is None and PADDLEOCR_AVAILABLE:
        try:
            logger.info("🧠 PaddleOCR engine loading...")
            # Use correct parameter name for newer PaddleOCR versions
            ocr_model = PaddleOCR(use_textline_orientation=True, lang='en')
            logger.info("✅ PaddleOCR model initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize PaddleOCR: {e}")
            ocr_model = None
    elif not PADDLEOCR_AVAILABLE:
        logger.warning("⚠️ PaddleOCR not available - using fallback mode")
    return ocr_model

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
            text = extract_text_with_paddle_ocr(processed_img)
            full_text += text + "\n\n"
            
            logger.info(f"✅ Page {page_num + 1} completed: {len(text)} characters")

        doc.close()
        logger.info(f"✅ PDF extraction completed: {len(full_text)} total characters")
        return full_text.strip()
        
    except Exception as e:
        logger.error(f"Error extracting text from PDF {filepath}: {str(e)}")
        raise Exception(f"OCR extraction failed: {str(e)}")

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
        
        # Step 1: Deskew the image
        logger.debug("🔄 Step 1: Deskewing image...")
        deskewed = deskew_image(gray)
        
        # Step 2: Apply adaptive thresholding
        logger.debug("🔄 Step 2: Applying adaptive thresholding...")
        thresh = cv2.adaptiveThreshold(
            deskewed, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 15, 11
        )
        
        # Step 3: Denoise the image
        logger.debug("🔄 Step 3: Denoising image...")
        denoised = cv2.fastNlMeansDenoising(thresh, None, 30, 7, 21)
        
        # Convert back to PIL Image
        processed_img = Image.fromarray(denoised)
        
        # Save debug image
        try:
            import os
            debug_dir = "data/debug"
            if not os.path.exists(debug_dir):
                os.makedirs(debug_dir)
            
            # Save with timestamp to avoid overwrites
            import time
            timestamp = int(time.time())
            debug_path = f"{debug_dir}/preprocessed_{timestamp}.png"
            processed_img.save(debug_path)
            logger.debug(f"💾 Saved preprocessed image to: {debug_path}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save debug image: {str(e)}")
        
        logger.debug("✅ Image preprocessing completed successfully")
        return processed_img
        
    except Exception as e:
        logger.warning(f"⚠️ Preprocessing failed, using original image: {str(e)}")
        return image.convert('L')

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

def extract_text_with_paddle_ocr(img: Image.Image) -> str:
    """
    Extract text using PaddleOCR.
    
    Args:
        img: PIL Image to process
        
    Returns:
        Extracted text as string
    """
    try:
        ocr_model = get_ocr_model()
        if ocr_model is None:
            logger.warning("⚠️ PaddleOCR not available - returning empty text")
            return ""
        
        logger.info(f"🔄 Starting PaddleOCR text extraction")
        logger.debug(f"📊 Input image shape: {img.size}")
        
        # Run PaddleOCR
        result = ocr_model.predict(np.array(img))
        
        # Extract text
        text = ""
        line_count = 0
        
        if result and len(result) > 0:
            logger.debug(f"📊 PaddleOCR returned {len(result)} result groups")
            
            # Handle PaddleOCR result structure (list containing OCRResult object)
            if isinstance(result, (list, tuple)) and len(result) > 0:
                ocr_result = result[0]  # Get the first (and usually only) result
                
                # Handle PaddleOCR result structure (OCRResult object)
                if hasattr(ocr_result, 'rec_texts'):
                    rec_texts = ocr_result.rec_texts
                    logger.debug(f"📊 Found {len(rec_texts)} text items")
                    
                    for i, text_item in enumerate(rec_texts):
                        extracted_text = str(text_item)
                        text += extracted_text + " "
                        line_count += 1
                        logger.debug(f"   → Extracted: '{extracted_text}'")
        
        text = text.strip()
        word_count = len([word for word in text.split() if len(word) > 1])
        
        logger.info(f"✅ PaddleOCR completed: {word_count} words, {line_count} lines")
        logger.debug(f"📝 Final text: '{text[:100]}{'...' if len(text) > 100 else ''}'")
        
        return text
        
    except Exception as e:
        logger.error(f"❌ PaddleOCR failed: {str(e)}")
        return ""

def run_enhanced_ocr(image: Image.Image) -> Dict[str, Any]:
    """
    Run OCR with PaddleOCR and return the best result.
    
    Args:
        image: PIL Image to process
        
    Returns:
        Dictionary with text, confidence, and processing info
    """
    logger.debug("🔄 Starting enhanced OCR with PaddleOCR...")
    
    ocr_model = get_ocr_model()
    if ocr_model is None:
        logger.warning("⚠️ PaddleOCR not available - using fallback mode")
        return {
            "text": "",
            "confidence": 0.0,
            "psm_used": "paddle",
            "word_count": 0
        }
    
    try:
        # Run PaddleOCR
        result = ocr_model.predict(np.array(image))
        
        # Extract text and calculate confidence
        text = ""
        total_confidence = 0.0
        line_count = 0
        
        if result and len(result) > 0:
            # Handle PaddleOCR result structure (list containing OCRResult object)
            if isinstance(result, (list, tuple)) and len(result) > 0:
                ocr_result = result[0]  # Get the first (and usually only) result
                
                # Handle PaddleOCR result structure (OCRResult object)
                if hasattr(ocr_result, 'rec_texts') and hasattr(ocr_result, 'rec_scores'):
                    rec_texts = ocr_result.rec_texts
                    rec_scores = ocr_result.rec_scores
                    
                    for i, (text_item, score) in enumerate(zip(rec_texts, rec_scores)):
                        extracted_text = str(text_item)
                        text += extracted_text + " "
                        
                        # Handle both string and float confidence values
                        confidence = float(score) if score is not None else 0.0
                        
                        total_confidence += confidence
                        line_count += 1
        
        text = text.strip()
        word_count = len([word for word in text.split() if len(word) > 1])
        
        # Calculate average confidence
        avg_confidence = total_confidence / line_count if line_count > 0 else 0.0
        
        # Calculate meaningful character ratio
        meaningful_chars = sum(1 for c in text if c.isalnum() or c.isspace())
        total_chars = len(text)
        meaningful_ratio = meaningful_chars / total_chars if total_chars > 0 else 0
        
        logger.debug(f"   PaddleOCR: {len(text)} chars, {word_count} words, {avg_confidence:.1f}% confidence, {meaningful_ratio:.1%} meaningful chars")
        
        # Normalize confidence using the existing function
        display_confidence = calculate_display_confidence(avg_confidence, word_count, text)
        
        logger.info(f"✅ Enhanced OCR completed: PaddleOCR, "
                    f"{word_count} words, {display_confidence:.1f}% confidence")
        
        return {
            "text": text,
            "confidence": display_confidence,
            "psm_used": "paddle",
            "word_count": word_count,
            "meaningful_ratio": meaningful_ratio
        }
        
    except Exception as e:
        logger.error(f"❌ PaddleOCR failed: {str(e)}")
        return {
            "text": "",
            "confidence": 0.0,
            "psm_used": "paddle",
            "word_count": 0
        }

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

def run_paddle_ocr(file_path: str) -> Dict[str, Any]:
    """
    Main entry point for PaddleOCR processing.
    
    Args:
        file_path: Path to the file to process (PDF, JPG, PNG, etc.)
        
    Returns:
        Dictionary with OCR results including pages, text, confidence, and metadata
    """
    try:
        logger.info(f"🔄 Starting PaddleOCR processing for: {file_path}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        ocr_model = get_ocr_model()
        if ocr_model is None:
            logger.warning("⚠️ PaddleOCR not available - using fallback mode")
            return {
                "pages": [],
                "raw_ocr_text": "",
                "overall_confidence": 0.0,
                "total_pages": 0,
                "total_words": 0,
                "was_retried": False
            }
        
        # Determine file type
        file_ext = os.path.splitext(file_path)[1].lower()
        logger.info(f"📄 File type detected: {file_ext}")
        
        pages_data = []
        total_words = 0
        total_confidence = 0.0
        was_retried = False
        
        if file_ext in ['.pdf']:
            # Process PDF
            logger.info("📄 Processing PDF file with PaddleOCR")
            try:
                # Convert PDF to images
                logger.info(f"🔄 Converting PDF to images...")
                images = convert_from_path(file_path, dpi=300)
                logger.info(f"✅ PDF converted to {len(images)} images at 300 DPI")
                
                if images:
                    logger.info(f"🔍 First image shape: {images[0].size}")
                
                for page_num, image in enumerate(images):
                    logger.info(f"🔄 Processing page {page_num + 1} of {len(images)}")
                    logger.debug(f"📊 Page {page_num + 1} image size: {image.size}")
                    
                    # Preprocess image
                    logger.debug(f"🔄 Preprocessing page {page_num + 1}")
                    processed_image = preprocess_image(image)
                    logger.debug(f"✅ Preprocessing completed for page {page_num + 1}")
                    
                    # Run PaddleOCR on this page
                    logger.info(f"🔄 Running PaddleOCR on page {page_num + 1}")
                    page_result = _process_single_page_with_paddle(processed_image, page_num + 1)
                    pages_data.append(page_result)
                    
                    total_words += page_result["word_count"]
                    total_confidence += page_result["avg_confidence"]
                    
                    logger.info(f"✅ Page {page_num + 1} completed: {page_result['word_count']} words, "
                               f"{page_result['avg_confidence']:.1f}% confidence")
                
            except Exception as e:
                logger.error(f"❌ PDF processing failed: {str(e)}")
                raise
                
        elif file_ext in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
            # Process single image
            logger.info("🖼️ Processing image file with PaddleOCR")
            try:
                logger.debug(f"🔄 Opening image file: {file_path}")
                image = Image.open(file_path)
                logger.debug(f"✅ Image opened successfully")
                
                logger.debug(f"🔄 Preprocessing image")
                processed_image = preprocess_image(image)
                logger.debug(f"✅ Image preprocessing completed")
                
                # Run PaddleOCR on this image
                logger.info(f"🔄 Running PaddleOCR on image")
                page_result = _process_single_page_with_paddle(processed_image, 1)
                pages_data.append(page_result)
                
                total_words = page_result["word_count"]
                total_confidence = page_result["avg_confidence"]
                
                logger.info(f"✅ Image processing completed: {page_result['word_count']} words, "
                           f"{page_result['avg_confidence']:.1f}% confidence")
                
            except Exception as e:
                logger.error(f"❌ Image processing failed: {str(e)}")
                raise
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
        
        # Calculate overall confidence
        overall_confidence = total_confidence / len(pages_data) if pages_data else 0.0
        logger.info(f"📊 Overall confidence calculated: {overall_confidence:.1f}%")
        
        # Combine all text
        raw_ocr_text = "\n\n".join([page["text"] for page in pages_data])
        logger.info(f"📝 Combined text length: {len(raw_ocr_text)} characters")
        
        # Check if retry is needed
        if overall_confidence < 15.0 or total_words < 10:
            logger.warning(f"⚠️ Low OCR quality - confidence: {overall_confidence:.1f}%, "
                          f"words: {total_words} - attempting retry")
            was_retried = True
            
            # Retry with different preprocessing
            try:
                logger.info(f"🔄 Starting retry with different preprocessing...")
                if file_ext in ['.pdf']:
                    logger.debug(f"🔄 Retry: Converting PDF with higher DPI (400)")
                    images = convert_from_path(file_path, dpi=400)  # Higher DPI
                    logger.info(f"✅ Retry: PDF converted to {len(images)} images at 400 DPI")
                    
                    # Save debug images
                    try:
                        debug_dir = "data/debug_ocr"
                        os.makedirs(debug_dir, exist_ok=True)
                        for i, img in enumerate(images):
                            debug_path = f"{debug_dir}/retry_page_{i+1}.png"
                            img.save(debug_path)
                            logger.debug(f"💾 Saved retry debug image: {debug_path}")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to save debug images: {e}")
                else:
                    logger.debug(f"🔄 Retry: Opening image without preprocessing")
                    image = Image.open(file_path)
                    images = [image]
                
                retry_pages_data = []
                retry_total_words = 0
                retry_total_confidence = 0.0
                
                for page_num, image in enumerate(images):
                    logger.info(f"🔄 Retry: Processing page {page_num + 1}")
                    logger.debug(f"📊 Retry page {page_num + 1} image size: {image.size}")
                    
                    # Try without preprocessing for retry
                    page_result = _process_single_page_with_paddle(image, page_num + 1)
                    retry_pages_data.append(page_result)
                    retry_total_words += page_result["word_count"]
                    retry_total_confidence += page_result["avg_confidence"]
                    
                    logger.info(f"✅ Retry page {page_num + 1}: {page_result['word_count']} words, "
                               f"{page_result['avg_confidence']:.1f}% confidence")
                
                retry_overall_confidence = retry_total_confidence / len(retry_pages_data) if retry_pages_data else 0.0
                
                # Use retry result if it's better
                if retry_overall_confidence > overall_confidence or retry_total_words > total_words:
                    logger.info(f"✅ Retry improved results: {retry_overall_confidence:.1f}% confidence, "
                              f"{retry_total_words} words (vs {overall_confidence:.1f}%, {total_words} words)")
                    pages_data = retry_pages_data
                    total_words = retry_total_words
                    overall_confidence = retry_overall_confidence
                    raw_ocr_text = "\n\n".join([page["text"] for page in pages_data])
                else:
                    logger.info(f"⚠️ Retry did not improve results, using original")
                    
            except Exception as e:
                logger.warning(f"⚠️ Retry failed: {str(e)}")
                logger.debug(f"📊 Retry error details: {type(e).__name__}: {e}")
        
        result = {
            "pages": pages_data,
            "raw_ocr_text": raw_ocr_text,
            "overall_confidence": overall_confidence,
            "total_pages": len(pages_data),
            "total_words": total_words,
            "was_retried": was_retried
        }
        
        logger.info(f"✅ PaddleOCR completed: {len(pages_data)} pages, {total_words} words, "
                   f"confidence: {overall_confidence:.1f}%, retried: {was_retried}")
        
        # Log detailed summary
        if total_words > 0:
            logger.info(f"📊 OCR Summary:")
            logger.info(f"   - Pages processed: {len(pages_data)}")
            logger.info(f"   - Total words extracted: {total_words}")
            logger.info(f"   - Average confidence: {overall_confidence:.1f}%")
            logger.info(f"   - Retry attempted: {was_retried}")
            logger.info(f"   - Text length: {len(raw_ocr_text)} characters")
            
            # Log first few words for verification
            first_words = " ".join(raw_ocr_text.split()[:10])
            logger.info(f"   - Sample text: {first_words}...")
        else:
            logger.warning(f"⚠️ OCR Summary: No text extracted")
            logger.warning(f"   - Pages processed: {len(pages_data)}")
            logger.warning(f"   - Total words: {total_words}")
            logger.warning(f"   - Confidence: {overall_confidence:.1f}%")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ PaddleOCR processing failed for {file_path}: {str(e)}")
        raise Exception(f"PaddleOCR processing failed: {str(e)}")

def _process_single_page_with_paddle(image: Image.Image, page_number: int) -> Dict[str, Any]:
    """
    Process a single page/image with PaddleOCR.
    
    Args:
        image: PIL Image to process
        page_number: Page number for logging
        
    Returns:
        Dictionary with page OCR results
    """
    try:
        logger.info(f"🔄 Starting PaddleOCR processing for page {page_number}")
        
        ocr_model = get_ocr_model()
        if ocr_model is None:
            logger.warning(f"⚠️ PaddleOCR not available for page {page_number} - using fallback mode")
            return {
                "page": page_number,
                "text": "",
                "avg_confidence": 0.0,
                "word_count": 0,
                "psm_used": "paddle",
                "line_items": [],
                "boxes": [],
                "line_count": 0
            }
        
        # Convert image to numpy array
        logger.debug(f"🔄 Converting image to numpy array for page {page_number}")
        img_array = np.array(image)
        logger.debug(f"📊 Image array shape: {img_array.shape}")
        
        # Run PaddleOCR
        logger.info(f"🔄 Running PaddleOCR on page {page_number}...")
        try:
            result = ocr_model.predict(np.array(image))
            logger.info(f"✅ PaddleOCR completed for page {page_number}")
            logger.debug(f"📊 OCR result type: {type(result)}")
            if result:
                logger.debug(f"📊 OCR result length: {len(result) if hasattr(result, '__len__') else 'No length'}")
        except Exception as e:
            logger.error(f"❌ PaddleOCR failed for page {page_number}: {str(e)}")
            return {
                "page": page_number,
                "text": "",
                "avg_confidence": 0.0,
                "word_count": 0,
                "psm_used": "paddle",
                "line_items": [],
                "boxes": [],
                "line_count": 0
            }
        
        # Extract text and calculate confidence
        full_text = ""
        total_confidence = 0.0
        line_count = 0
        bounding_boxes = []
        line_items = []
        
        logger.debug(f"🔄 Processing PaddleOCR results for page {page_number}")
        if result and len(result) > 0:
            logger.debug(f"📊 Found result structure: {type(result)}")
            
            # Handle PaddleOCR result structure (list containing OCRResult object)
            if isinstance(result, (list, tuple)) and len(result) > 0:
                ocr_result = result[0]  # Get the first (and usually only) result
                logger.debug(f"📊 OCRResult type: {type(ocr_result)}")
                
                # Handle PaddleOCR result structure (OCRResult object)
                if hasattr(ocr_result, 'rec_texts') and hasattr(ocr_result, 'rec_scores'):
                    rec_texts = ocr_result.rec_texts
                    rec_scores = ocr_result.rec_scores
                    rec_boxes = getattr(ocr_result, 'rec_boxes', [])
                    
                    logger.debug(f"📊 Found {len(rec_texts)} text items")
                    
                    for i, (text, score) in enumerate(zip(rec_texts, rec_scores)):
                        try:
                            extracted_text = str(text)
                            confidence = float(score) if score is not None else 0.0
                            
                            total_confidence += confidence
                            line_count += 1
                            full_text += extracted_text + " "
                            
                            # Log first few text blocks for debugging
                            if line_count <= 3:
                                logger.debug(f"   → '{extracted_text}' (confidence: {confidence:.2f})")
                            
                            # Store bounding box if available
                            box = rec_boxes[i] if i < len(rec_boxes) else None
                            bounding_boxes.append({
                                "text": extracted_text,
                                "confidence": confidence,
                                "bbox": box
                            })
                            
                            # Basic line item detection
                            if _is_line_item_candidate(extracted_text):
                                line_items.append({
                                    "text": extracted_text,
                                    "confidence": confidence,
                                    "bbox": box
                                })
                        except Exception as e:
                            logger.warning(f"⚠️ Error processing OCR item {i}: {str(e)}")
                            continue
                else:
                    logger.warning(f"⚠️ Unexpected OCRResult structure: {type(ocr_result)}")
            else:
                logger.warning(f"⚠️ Unexpected result structure: {type(result)}")
        else:
            logger.warning(f"⚠️ No OCR results for page {page_number}")
        
        text = full_text.strip()
        word_count = len([word for word in text.split() if len(word) > 1])
        
        # Calculate average confidence
        avg_confidence = total_confidence / line_count if line_count > 0 else 0.0
        
        # Normalize confidence using the existing function
        display_confidence = calculate_display_confidence(avg_confidence, word_count, text)
        
        logger.info(f"📄 OCR page {page_number}: found {word_count} words, confidence ~{display_confidence:.2f}%")
        logger.info(f"✅ PaddleOCR returned text length: {len(text)} for page {page_number}")
        logger.debug(f"   Page {page_number}: {len(text)} chars, {word_count} words, "
                    f"{display_confidence:.1f}% confidence, {line_count} lines")
        
        return {
            "page": page_number,
            "text": text,
            "avg_confidence": display_confidence,
            "word_count": word_count,
            "psm_used": "paddle",
            "line_items": line_items,
            "boxes": bounding_boxes,
            "line_count": line_count
        }
        
    except Exception as e:
        logger.error(f"❌ PaddleOCR failed for page {page_number}: {str(e)}")
        return {
            "page": page_number,
            "text": "",
            "avg_confidence": 0.0,
            "word_count": 0,
            "psm_used": "paddle",
            "line_items": [],
            "boxes": [],
            "line_count": 0
        }

def _is_line_item_candidate(text: str) -> bool:
    """
    Basic heuristic to identify potential line items.
    
    Args:
        text: Text to analyze
        
    Returns:
        True if text looks like a line item
    """
    if not text or len(text.strip()) < 3:
        return False
    
    # Look for patterns that suggest line items
    text_lower = text.lower()
    
    # Quantity patterns
    quantity_patterns = [
        r'\d+\s*x\s*[£$€]?\d+',  # "2 x £10.50"
        r'\d+\s*@\s*[£$€]?\d+',  # "2 @ £10.50"
        r'qty\s*:\s*\d+',         # "Qty: 2"
        r'quantity\s*:\s*\d+',    # "Quantity: 2"
    ]
    
    # Price patterns
    price_patterns = [
        r'[£$€]\s*\d+\.\d{2}',   # "£10.50"
        r'\d+\.\d{2}\s*[£$€]',   # "10.50 £"
        r'total\s*:\s*[£$€]?\d+', # "Total: £10.50"
    ]
    
    # Check for quantity patterns
    for pattern in quantity_patterns:
        if re.search(pattern, text_lower):
            return True
    
    # Check for price patterns
    for pattern in price_patterns:
        if re.search(pattern, text_lower):
            return True
    
    # Check for common line item keywords
    line_item_keywords = [
        'each', 'unit', 'price', 'total', 'subtotal', 'amount',
        'quantity', 'qty', 'units', 'pieces', 'items'
    ]
    
    if any(keyword in text_lower for keyword in line_item_keywords):
        return True
    
    return False

def calculate_display_confidence(raw_confidence: float, word_count: int = 0, text: str = "") -> float:
    """
    Convert OCR confidence (0–1 or 0–100) into 0–100 scale with improved fallback logic.
    
    Args:
        raw_confidence: Raw confidence value from OCR
        word_count: Number of words found
        text: OCR text for meaningful character analysis
        
    Returns:
        Display confidence (0-100) rounded to 1 decimal place
    """
    # If we have meaningful text, don't return 0 confidence
    if word_count > 10 or (text and len(text.strip()) > 50):
        min_confidence = 10.0  # Minimum confidence if we have meaningful text
    else:
        min_confidence = 0.0
    
    if isinstance(raw_confidence, (int, float)):
        if raw_confidence > 1.0:
            # Already in 0-100 scale
            confidence = min(100.0, float(raw_confidence))
        else:
            # Convert from 0-1 scale to 0-100
            confidence = min(100.0, float(raw_confidence) * 100)
        
        # Apply minimum confidence if we have meaningful text
        confidence = max(confidence, min_confidence)
        
        # Round to 1 decimal place
        return round(confidence, 1)
    
    # Fallback: if we have text but no confidence, give a reasonable default
    if word_count > 0 or (text and len(text.strip()) > 20):
        return round(min_confidence, 1)
    
    return 0.0

def extract_text_with_table_awareness(filepath: str) -> Tuple[str, Dict[str, Any]]:
    """
    Legacy function for backward compatibility.
    """
    result = run_paddle_ocr(filepath)
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