#!/usr/bin/env python3
"""
Enhanced Image Operations for Phase B

Features:
- Deskew using orientation estimation
- Denoise via OpenCV fastNlMeans
- Contrast enhancement using CLAHE
- Adaptive binarization
- HEIC support
- Document-type aware preprocessing
"""

import cv2
import numpy as np
from typing import Tuple, List, Optional, Dict, Any
import logging
from PIL import Image
import io

logger = logging.getLogger(__name__)

def deskew(img: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    Deskew image using orientation estimation
    
    Args:
        img: Input image as numpy array
        
    Returns:
        Tuple of (deskewed_image, angle_corrected)
    """
    try:
        # Convert to grayscale if needed
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        
        # Binarize for edge detection
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            logger.warning("No contours found for deskew")
            return img, 0.0
        
        # Find the largest contour (assumed to be the main content)
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Get minimum area rectangle
        rect = cv2.minAreaRect(largest_contour)
        angle = rect[2]
        
        # Normalize angle to -45 to 45 degrees
        if angle < -45:
            angle = 90 + angle
        
        # Skip if angle is very small (less than 1 degree)
        if abs(angle) < 1.0:
            logger.info(f"Image already straight (angle: {angle:.2f}°)")
            return img, 0.0
        
        # Rotate image
        height, width = img.shape[:2]
        center = (width // 2, height // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        deskewed = cv2.warpAffine(img, rotation_matrix, (width, height), 
                                 flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, 
                                 borderValue=255)
        
        logger.info(f"Deskewed image by {angle:.2f}°")
        return deskewed, angle
        
    except Exception as e:
        logger.error(f"Deskew failed: {e}")
        return img, 0.0

def denoise(img: np.ndarray) -> np.ndarray:
    """
    Denoise image using OpenCV fastNlMeans or Gaussian fallback
    
    Args:
        img: Input image as numpy array
        
    Returns:
        Denoised image
    """
    try:
        # Convert to grayscale if needed
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        
        # Try fastNlMeans first (better for color images)
        if len(img.shape) == 3:
            denoised = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
        else:
            # For grayscale, use fastNlMeans
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        logger.info("Applied fastNlMeans denoising")
        return denoised
        
    except Exception as e:
        logger.warning(f"fastNlMeans failed, using Gaussian blur: {e}")
        # Fallback to Gaussian blur
        if len(img.shape) == 3:
            denoised = cv2.GaussianBlur(img, (3, 3), 0)
        else:
            denoised = cv2.GaussianBlur(img, (3, 3), 0)
        
        return denoised

def enhance_contrast(img: np.ndarray) -> np.ndarray:
    """
    Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
    
    Args:
        img: Input image as numpy array
        
    Returns:
        Contrast enhanced image
    """
    try:
        # Convert to grayscale if needed
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        
        # Create CLAHE object
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        logger.info("Applied CLAHE contrast enhancement")
        return enhanced
        
    except Exception as e:
        logger.error(f"CLAHE enhancement failed: {e}")
        return img

def adaptive_binarize(img: np.ndarray) -> np.ndarray:
    """
    Adaptive binarization with morphological closing for broken thermal text
    
    Args:
        img: Input image as numpy array
        
    Returns:
        Binarized image
    """
    try:
        # Convert to grayscale if needed
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        
        # Adaptive thresholding
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                     cv2.THRESH_BINARY, 11, 2)
        
        # Morphological closing to connect broken characters
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        logger.info("Applied adaptive binarization with morphological closing")
        return closed
        
    except Exception as e:
        logger.error(f"Adaptive binarization failed: {e}")
        # Fallback to simple thresholding
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary

def preprocess_for_ocr(img: np.ndarray, profile: str = "auto") -> Tuple[np.ndarray, List[str]]:
    """
    Preprocess image for OCR with document-type aware processing
    
    Args:
        img: Input image as numpy array
        profile: Processing profile ("auto", "receipt", "invoice", "document")
        
    Returns:
        Tuple of (processed_image, steps_used)
    """
    steps_used = []
    processed = img.copy()
    
    try:
        # Auto-detect profile if not specified
        if profile == "auto":
            profile = _detect_document_profile(processed)
            steps_used.append(f"detected_profile:{profile}")
        
        # Receipt-like processing (narrow aspect OR many short lines)
        if profile == "receipt":
            logger.info("Applying receipt-optimized preprocessing")
            
            # Increase DPI target (resize for better OCR)
            height, width = processed.shape[:2]
            if width < 800:  # Narrow receipt
                scale_factor = 2.0
                processed = cv2.resize(processed, None, fx=scale_factor, fy=scale_factor, 
                                     interpolation=cv2.INTER_CUBIC)
                steps_used.append("upscaled_2x")
            
            # Stronger denoising for thermal receipts
            processed = denoise(processed)
            steps_used.append("denoise")
            
            # Enhanced contrast for thermal printing
            processed = enhance_contrast(processed)
            steps_used.append("enhance_contrast")
            
            # Adaptive binarization for thermal text
            processed = adaptive_binarize(processed)
            steps_used.append("adaptive_binarize")
            
        else:
            # Standard document processing
            logger.info("Applying standard document preprocessing")
            
            # Deskew
            processed, angle = deskew(processed)
            if abs(angle) > 1.0:
                steps_used.append(f"deskew:{angle:.1f}deg")
            
            # Denoise
            processed = denoise(processed)
            steps_used.append("denoise")
            
            # Enhance contrast
            processed = enhance_contrast(processed)
            steps_used.append("enhance_contrast")
            
            # Binarize
            processed = adaptive_binarize(processed)
            steps_used.append("adaptive_binarize")
        
        logger.info(f"Preprocessing completed: {steps_used}")
        return processed, steps_used
        
    except Exception as e:
        logger.error(f"Preprocessing failed: {e}")
        return img, ["error"]

def _detect_document_profile(img: np.ndarray) -> str:
    """
    Auto-detect document profile based on image characteristics
    
    Args:
        img: Input image
        
    Returns:
        Profile string ("receipt", "invoice", "document")
    """
    try:
        height, width = img.shape[:2]
        aspect_ratio = width / height
        
        # Receipt characteristics
        if aspect_ratio < 1.5:  # Narrow aspect ratio
            return "receipt"
        
        # Count text lines (rough estimate)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Horizontal projection to count lines
        horizontal_projection = np.sum(binary, axis=1)
        text_lines = np.sum(horizontal_projection > np.mean(horizontal_projection))
        
        if text_lines < 20:  # Few lines, likely receipt
            return "receipt"
        elif text_lines < 50:  # Moderate lines, likely invoice
            return "invoice"
        else:  # Many lines, general document
            return "document"
            
    except Exception as e:
        logger.warning(f"Profile detection failed: {e}")
        return "document"

def convert_heic_to_rgb(heic_data: bytes) -> np.ndarray:
    """
    Convert HEIC image data to RGB numpy array
    
    Args:
        heic_data: HEIC image data as bytes
        
    Returns:
        RGB image as numpy array
    """
    try:
        # Try to import pillow_heif
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except ImportError:
            logger.warning("pillow_heif not available, HEIC support limited")
            raise ImportError("pillow_heif required for HEIC support")
        
        # Open HEIC with Pillow
        image = Image.open(io.BytesIO(heic_data))
        
        # Convert to RGB
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to numpy array
        rgb_array = np.array(image)
        
        logger.info(f"Converted HEIC to RGB: {rgb_array.shape}")
        return rgb_array
        
    except Exception as e:
        logger.error(f"HEIC conversion failed: {e}")
        raise

def get_image_info(img: np.ndarray) -> Dict[str, Any]:
    """
    Get comprehensive image information
    
    Args:
        img: Input image
        
    Returns:
        Dictionary with image information
    """
    info = {
        'shape': img.shape,
        'dtype': str(img.dtype),
        'channels': img.shape[2] if len(img.shape) == 3 else 1,
        'width': img.shape[1],
        'height': img.shape[0],
        'aspect_ratio': img.shape[1] / img.shape[0],
        'size_bytes': img.nbytes,
    }
    
    if len(img.shape) == 3:
        # Color statistics
        for i, channel in enumerate(['blue', 'green', 'red']):
            info[f'{channel}_mean'] = float(np.mean(img[:, :, i]))
            info[f'{channel}_std'] = float(np.std(img[:, :, i]))
    else:
        # Grayscale statistics
        info['mean'] = float(np.mean(img))
        info['std'] = float(np.std(img))
    
    return info 