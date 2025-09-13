"""
OCR preprocessing: deskew, denoise, adaptive threshold
"""
from typing import Tuple
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

def preprocess_image(img: "PIL.Image.Image") -> "PIL.Image.Image":
    """Deskew, denoise, adaptive threshold; return processed image."""
    # Convert PIL to OpenCV
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    
    # Convert to grayscale
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    
    # Deskew
    gray = deskew_image(gray)
    
    # Denoise
    gray = denoise_image(gray)
    
    # Adaptive threshold
    binary = adaptive_threshold(gray)
    
    # Convert back to PIL
    return Image.fromarray(binary)

def deskew_image(gray: np.ndarray) -> np.ndarray:
    """Deskew the image using Hough lines."""
    # Edge detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    
    # Hough lines
    lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
    
    if lines is not None:
        angles = []
        for rho, theta in lines[:10]:  # Use first 10 lines
            angle = theta * 180 / np.pi
            if angle < 45:
                angles.append(angle)
            elif angle > 135:
                angles.append(angle - 180)
        
        if angles:
            # Calculate median angle
            median_angle = np.median(angles)
            
            # Rotate image
            if abs(median_angle) > 0.5:  # Only rotate if significant
                h, w = gray.shape
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                gray = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC)
    
    return gray

def denoise_image(gray: np.ndarray) -> np.ndarray:
    """Remove noise using bilateral filter."""
    # Bilateral filter preserves edges while removing noise
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # Additional smoothing for very noisy images
    if np.std(denoised) > 30:  # High noise threshold
        denoised = cv2.medianBlur(denoised, 3)
    
    return denoised

def adaptive_threshold(gray: np.ndarray) -> np.ndarray:
    """Apply adaptive threshold for better OCR."""
    # CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    
    # Adaptive threshold
    binary = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    # Morphological operations to clean up
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    
    return binary 