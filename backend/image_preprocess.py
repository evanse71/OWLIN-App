# -*- coding: utf-8 -*-
"""Image preprocessing utilities for Owlin OCR.
- Deskew (Hough)
- Denoise (bilateral)
- Contrast enhance (CLAHE)
- Adaptive threshold
- Optional perspective correction for photos
All functions are pure and safe for CPU-only environments."""
from __future__ import annotations
import os
import logging
from typing import Any, Dict, List, Tuple, Optional
import cv2
import numpy as np

LOGGER = logging.getLogger("owlin.preprocess")

MAX_LONG_EDGE = 2200

def _to_gray(img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

def _downscale(img: np.ndarray, max_long_edge: int = MAX_LONG_EDGE) -> np.ndarray:
    h, w = img.shape[:2]
    scale = min(1.0, float(max_long_edge) / max(h, w))
    if scale >= 1.0:
        return img
    new_w, new_h = int(w * scale), int(h * scale)
    return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

def _is_photo(img_bgr: np.ndarray) -> bool:
    """
    Detect if image is a photo (vs scanned document).
    
    Photos typically have:
    - Lower edge variance (softer edges)
    - Higher color variance (shadows, lighting variations)
    - More noise/grain
    
    Returns:
        True if image appears to be a photo
    """
    gray = _to_gray(img_bgr)
    
    # Calculate Laplacian variance (edge sharpness)
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    
    # Calculate color variance
    mean, std = cv2.meanStdDev(gray)
    std_val = std[0][0]
    
    # Photo indicators:
    # - Low edge variance (soft/blurry) OR
    # - High color variance (shadows/lighting) OR
    # - Color image (not grayscale)
    is_color = len(img_bgr.shape) == 3 and img_bgr.shape[2] == 3
    
    # Check if it's a color image with significant color variation
    if is_color:
        # Calculate variance in each channel
        b, g, r = cv2.split(img_bgr)
        b_var = cv2.meanStdDev(b)[1][0][0]
        g_var = cv2.meanStdDev(g)[1][0][0]
        r_var = cv2.meanStdDev(r)[1][0][0]
        color_variance = (b_var + g_var + r_var) / 3
        
        # High color variance suggests photo
        if color_variance > 40:
            return True
    
    # Low edge sharpness OR high grayscale variance suggests photo
    return (lap_var < 250) or (std_val > 55)

def _order_points(pts: np.ndarray) -> np.ndarray:
    x_sorted = pts[np.argsort(pts[:, 0]), :]
    left = x_sorted[:2, :]
    right = x_sorted[2:, :]
    left = left[np.argsort(left[:, 1]), :]
    (tl, bl) = left
    D = [np.linalg.norm(tl - x) for x in right]
    br = right[np.argmax(D)]
    tr = right[np.argmin(D)]
    return np.array([tl, tr, br, bl], dtype="float32")

def detect_and_dewarp(image: np.ndarray) -> np.ndarray:
    """
    Detect document edges and apply perspective correction (dewarping) for photos.
    
    This handles skewed/trapezoid photos by finding the largest 4-sided polygon
    (document edges) and flattening it using perspective transform.
    
    Args:
        image: Grayscale image (or BGR, will be converted)
        
    Returns:
        Dewarped image, or original if no document edges found
    """
    try:
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = _to_gray(image)
        else:
            gray = image.copy()
        
        h, w = gray.shape[:2]
        image_area = h * w
        
        # Apply adaptive threshold to find edges
        thr = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY, 11, 2)
        
        # Find contours
        contours, _ = cv2.findContours(thr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return gray
        
        # Find largest contour that could be a document
        largest_contour = None
        largest_area = 0
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Document should be at least 30% of image area
            if area > image_area * 0.3 and area > largest_area:
                peri = cv2.arcLength(cnt, True)
                # Approximate polygon with tolerance proportional to perimeter
                approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
                
                # Look for 4-sided polygon (document edges)
                if len(approx) == 4:
                    largest_contour = approx
                    largest_area = area
        
        if largest_contour is None:
            return gray
        
        # Order points: top-left, top-right, bottom-right, bottom-left
        pts = largest_contour.reshape(4, 2).astype("float32")
        rect = _order_points(pts)
        (tl, tr, br, bl) = rect
        
        # Calculate dimensions of the document
        widthA = np.linalg.norm(br - bl)
        widthB = np.linalg.norm(tr - tl)
        maxW = int(max(widthA, widthB))
        
        heightA = np.linalg.norm(tr - br)
        heightB = np.linalg.norm(tl - bl)
        maxH = int(max(heightA, heightB))
        
        # Destination points for perspective transform (rectangular output)
        dst = np.array([
            [0, 0],
            [maxW - 1, 0],
            [maxW - 1, maxH - 1],
            [0, maxH - 1]
        ], dtype="float32")
        
        # Calculate perspective transform matrix
        M = cv2.getPerspectiveTransform(rect, dst)
        
        # Apply perspective transform
        warped = cv2.warpPerspective(gray, M, (maxW, maxH), 
                                     flags=cv2.INTER_LINEAR,
                                     borderMode=cv2.BORDER_REPLICATE)
        
        return warped
        
    except Exception as e:
        # Log error but return original image
        import logging
        logging.getLogger("owlin.preprocess").warning(f"Dewarping failed: {e}")
        return gray if len(image.shape) == 2 else _to_gray(image)

def _deskew(gray: np.ndarray) -> Tuple[np.ndarray, float]:
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blur, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 180.0, 140)
    angles = []
    if lines is not None:
        for rho, theta in lines[:, 0]:
            ang = (theta * 180.0 / np.pi) - 90.0
            if -45 <= ang <= 45:
                angles.append(ang)
    angle = float(np.median(angles)) if len(angles) > 0 else 0.0
    h, w = gray.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    rotated = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return rotated, angle

def preprocess_bgr_page(img_bgr: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Preprocess a single page image (BGR) -> (enhanced grayscale image, metadata).
    
    IMPORTANT: Returns enhanced grayscale (NOT binary) for better PaddleOCR performance.
    PaddleOCR is a deep learning model trained on grayscale/color images with anti-aliasing.
    Binary thresholding creates jagged edges that lower Paddle's confidence.
    
    For OpenCV structure detection (lines/contours), apply thresholding separately.
    """
    meta: Dict[str, Any] = {"steps": [], "warnings": []}
    try:
        img = _downscale(img_bgr)
        meta["steps"].append({"op": "downscale", "shape": list(img.shape)})
        gray = _to_gray(img)
        meta["steps"].append({"op": "to_gray"})

        # Apply dewarping for photos BEFORE deskewing
        # This handles skewed/trapezoid photos by flattening perspective first
        if _is_photo(img):
            gray_before = gray.copy()
            gray = detect_and_dewarp(gray)
            if not np.array_equal(gray, gray_before):
                meta["steps"].append({"op": "dewarp_perspective_correction", 
                                     "shape_before": list(gray_before.shape),
                                     "shape_after": list(gray.shape)})

        deskewed, angle = _deskew(gray)
        meta["steps"].append({"op": "deskew", "angle_deg": angle})

        den = cv2.bilateralFilter(deskewed, 5, 75, 75)
        meta["steps"].append({"op": "denoise_bilateral"})

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(den)
        meta["steps"].append({"op": "clahe"})

        # Return enhanced grayscale (NOT binary) for PaddleOCR
        # Binary thresholding is now done separately only when needed for OpenCV operations
        meta["steps"].append({"op": "enhanced_grayscale_for_paddle"})
        return enhanced, meta
    except Exception as e:
        meta["warnings"].append(f"preprocess_error:{e}")
        # Safe fallback: grayscale only
        return _to_gray(img_bgr), meta

def get_binary_for_structure_detection(enhanced_gray: np.ndarray) -> np.ndarray:
    """
    Apply binary thresholding to enhanced grayscale for OpenCV structure detection.
    Use this ONLY for line/contour detection, NOT for PaddleOCR.
    """
    try:
        bw = cv2.adaptiveThreshold(enhanced_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 31, 9)
        return bw
    except Exception:
        return enhanced_gray

def preprocess_minimal(img_bgr: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Minimal preprocessing for good quality photos.
    
    This is a gentle preprocessing pipeline that preserves image quality:
    - Resize to reasonable DPI (max 2200px long edge)
    - Convert to grayscale
    - Light denoise (gentle bilateral filter)
    - NO CLAHE, NO thresholding, NO aggressive enhancement
    
    Returns grayscale image suitable for PaddleOCR (which prefers grayscale/color over binary).
    
    Args:
        img_bgr: Input BGR image
        
    Returns:
        Tuple of (preprocessed grayscale image, metadata dict)
    """
    meta: Dict[str, Any] = {"steps": [], "warnings": []}
    try:
        # 1. Downscale if needed
        img = _downscale(img_bgr)
        meta["steps"].append({"op": "downscale", "shape": list(img.shape)})
        
        # 2. Convert to grayscale
        gray = _to_gray(img)
        meta["steps"].append({"op": "to_gray"})
        
        # 3. Light denoise (gentler than enhanced path)
        # Using smaller sigma values for gentler filtering
        den = cv2.bilateralFilter(gray, 5, 50, 50)
        meta["steps"].append({"op": "denoise_bilateral_light", "d": 5, "sigmaColor": 50, "sigmaSpace": 50})
        
        # Return grayscale (NOT binary) - PaddleOCR works better with grayscale
        meta["steps"].append({"op": "minimal_grayscale_for_paddle"})
        return den, meta
    except Exception as e:
        meta["warnings"].append(f"preprocess_minimal_error:{e}")
        # Safe fallback: just grayscale
        return _to_gray(img_bgr), meta

def _run_ocr_on_image(image: np.ndarray) -> Tuple[str, float, int, List[str]]:
    """
    Run OCR on a preprocessed image using the existing OCRProcessor infrastructure.
    
    Returns:
        Tuple of (combined_text, avg_confidence, word_count, sample_words)
    """
    try:
        # Use the existing OCRProcessor to ensure consistency
        from backend.ocr.ocr_processor import get_ocr_processor
        
        # Validate and normalize image
        if image is None or image.size == 0:
            LOGGER.error("Empty or None image provided to OCR")
            return "", 0.0, 0, []
        
        # Ensure image is in correct format (numpy array, uint8)
        if image.dtype != np.uint8:
            if image.dtype == np.float32 or image.dtype == np.float64:
                # Normalize float images to 0-255 range
                if image.max() <= 1.0:
                    image = (image * 255).astype(np.uint8)
                else:
                    image = image.astype(np.uint8)
            else:
                image = image.astype(np.uint8)
        
        # Convert grayscale to BGR if needed (OCRProcessor expects BGR)
        if len(image.shape) == 2:
            # Grayscale - convert to BGR
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            LOGGER.debug(f"Converted grayscale to BGR: {image.shape}")
        elif len(image.shape) == 3 and image.shape[2] == 3:
            # Already BGR
            pass
        else:
            LOGGER.error(f"Invalid image shape for OCR: {image.shape}")
            return "", 0.0, 0, []
        
        # Get OCR processor instance
        processor = get_ocr_processor()
        
        # Process the full image as a single block
        h, w = image.shape[:2]
        block_info = {
            "type": "body",
            "bbox": (0, 0, w, h)  # Full image
        }
        
        LOGGER.debug(f"Running OCR on full image: shape={image.shape}, dtype={image.dtype}")
        ocr_result = processor.process_block(image, block_info)
        
        # Extract metrics
        text = ocr_result.ocr_text
        confidence = ocr_result.confidence
        
        # Split text into words
        words = text.split() if text else []
        word_count = len(words)
        sample_words = words[:20]  # First 20 words for preview
        
        if word_count == 0:
            LOGGER.warning(f"OCR found 0 words. Confidence: {confidence:.3f}, Text length: {len(text)}, Method: {ocr_result.method_used}")
        else:
            LOGGER.info(f"OCR extracted {word_count} words with confidence {confidence:.3f} (method: {ocr_result.method_used})")
        
        return text, confidence, word_count, sample_words
    except Exception as e:
        LOGGER.error(f"OCR comparison failed: {e}", exc_info=True)
        return "", 0.0, 0, []

def compare_preprocessing_paths(img_bgr: np.ndarray) -> Dict[str, Any]:
    """
    Compare minimal vs enhanced preprocessing paths by running OCR on both.
    
    This function:
    1. Runs minimal preprocessing → OCR → metrics
    2. Runs enhanced preprocessing → OCR → metrics
    3. Compares results and chooses better path
    
    Args:
        img_bgr: Input BGR image
        
    Returns:
        Dict with:
        - minimal: {avg_confidence, word_count, sample_text, preprocessed_image}
        - enhanced: {avg_confidence, word_count, sample_text, preprocessed_image}
        - chosen_path: "minimal" or "enhanced"
        - comparison_metrics: detailed comparison stats
    """
    result: Dict[str, Any] = {
        "minimal": {},
        "enhanced": {},
        "chosen_path": "enhanced",  # Default fallback
        "comparison_metrics": {},
        "errors": []
    }
    
    try:
        # Path A: Minimal preprocessing
        LOGGER.info("Running minimal preprocessing path...")
        try:
            minimal_img, minimal_meta = preprocess_minimal(img_bgr)
            LOGGER.info(f"Minimal preprocessing complete, image shape: {minimal_img.shape}")
            minimal_text, minimal_conf, minimal_words, minimal_sample = _run_ocr_on_image(minimal_img)
            minimal_sample_text = " ".join(minimal_sample) if minimal_sample else ""
            
            result["minimal"] = {
                "avg_confidence": minimal_conf,
                "word_count": minimal_words,
                "sample_text": minimal_sample_text,
                "full_text": minimal_text,
                "preprocessing_meta": minimal_meta,
                "image_shape": list(minimal_img.shape) if minimal_img is not None else None,
                "image_dtype": str(minimal_img.dtype) if minimal_img is not None else None
            }
            LOGGER.info(f"Minimal path OCR: {minimal_words} words, confidence: {minimal_conf:.3f}, image shape: {minimal_img.shape if minimal_img is not None else 'None'}")
        except Exception as e:
            error_msg = f"Minimal path failed: {str(e)}"
            LOGGER.error(error_msg, exc_info=True)
            result["errors"].append(error_msg)
            result["minimal"] = {
                "avg_confidence": 0.0,
                "word_count": 0,
                "sample_text": "",
                "error": error_msg
            }
        
        # Path B: Enhanced preprocessing (current)
        LOGGER.info("Running enhanced preprocessing path...")
        try:
            enhanced_img, enhanced_meta = preprocess_bgr_page(img_bgr)
            LOGGER.info(f"Enhanced preprocessing complete, image shape: {enhanced_img.shape}")
            enhanced_text, enhanced_conf, enhanced_words, enhanced_sample = _run_ocr_on_image(enhanced_img)
            enhanced_sample_text = " ".join(enhanced_sample) if enhanced_sample else ""
            
            result["enhanced"] = {
                "avg_confidence": enhanced_conf,
                "word_count": enhanced_words,
                "sample_text": enhanced_sample_text,
                "full_text": enhanced_text,
                "preprocessing_meta": enhanced_meta,
                "image_shape": list(enhanced_img.shape) if enhanced_img is not None else None,
                "image_dtype": str(enhanced_img.dtype) if enhanced_img is not None else None
            }
            LOGGER.info(f"Enhanced path OCR: {enhanced_words} words, confidence: {enhanced_conf:.3f}, image shape: {enhanced_img.shape if enhanced_img is not None else 'None'}")
        except Exception as e:
            error_msg = f"Enhanced path failed: {str(e)}"
            LOGGER.error(error_msg, exc_info=True)
            result["errors"].append(error_msg)
            result["enhanced"] = {
                "avg_confidence": 0.0,
                "word_count": 0,
                "sample_text": "",
                "error": error_msg
            }
        
        # Compare and choose better path
        # Primary metric: average confidence
        # Secondary metric: word count (more words usually means better extraction)
        # Tertiary: prefer minimal if confidence is close (within 5%) since it's faster
        
        confidence_diff = minimal_conf - enhanced_conf
        word_diff = minimal_words - enhanced_words
        
        # Choose minimal if:
        # 1. Confidence is higher, OR
        # 2. Confidence is within 5% and word count is higher, OR
        # 3. Confidence is within 5% and word count is similar (within 10%)
        if minimal_conf > enhanced_conf:
            chosen = "minimal"
            reason = f"Higher confidence ({minimal_conf:.3f} vs {enhanced_conf:.3f})"
        elif abs(confidence_diff) <= 0.05 and minimal_words > enhanced_words:
            chosen = "minimal"
            reason = f"Similar confidence ({minimal_conf:.3f} vs {enhanced_conf:.3f}) but more words ({minimal_words} vs {enhanced_words})"
        elif abs(confidence_diff) <= 0.05 and abs(word_diff) <= max(minimal_words, enhanced_words) * 0.1:
            chosen = "minimal"
            reason = f"Similar results, preferring minimal (faster)"
        else:
            chosen = "enhanced"
            reason = f"Enhanced path better (conf: {enhanced_conf:.3f} vs {minimal_conf:.3f}, words: {enhanced_words} vs {minimal_words})"
        
        result["chosen_path"] = chosen
        result["comparison_metrics"] = {
            "confidence_diff": confidence_diff,
            "word_count_diff": word_diff,
            "minimal_confidence": minimal_conf,
            "enhanced_confidence": enhanced_conf,
            "minimal_words": minimal_words,
            "enhanced_words": enhanced_words,
            "choice_reason": reason
        }
        
        LOGGER.info(f"Preprocessing comparison complete: chosen={chosen}, reason={reason}")
        
    except Exception as e:
        LOGGER.error(f"Preprocessing comparison failed: {e}", exc_info=True)
        result["error"] = str(e)
        # Fallback to enhanced if comparison fails
        result["chosen_path"] = "enhanced"
    
    return result

def save_preprocessed_artifact(bw_or_gray: np.ndarray, artifact_dir: str, basename: str) -> str:
    os.makedirs(artifact_dir, exist_ok=True)
    out_path = os.path.join(artifact_dir, f"{basename}.png")
    cv2.imwrite(out_path, bw_or_gray)
    return out_path
