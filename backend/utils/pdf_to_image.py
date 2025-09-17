from typing import Optional
import numpy as np
import cv2
import pypdfium2 as pdfium

def _preprocess_for_ocr(img_bgr: "np.ndarray") -> "np.ndarray":
    """Lightweight preprocessing: grayscale -> bilateral -> adaptive threshold -> tiny deskew."""
    # Convert to grayscale
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    
    # Bilateral filter to reduce noise while preserving edges
    filtered = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # Adaptive threshold for better text contrast
    thresh = cv2.adaptiveThreshold(filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    # Tiny deskew (±5° max) - detect text angle and correct
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) > 0:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle += 90
        # Only correct if angle is significant but small
        if abs(angle) > 1 and abs(angle) <= 5:
            (h, w) = thresh.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, -angle, 1.0)
            thresh = cv2.warpAffine(thresh, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    # Convert back to BGR for OCR
    return cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)

def render_pdf_page_bgr(path: str, page_no: int, scale: float = 2.0) -> Optional["np.ndarray"]:
    pdf = pdfium.PdfDocument(path)
    if page_no < 0 or page_no >= len(pdf):
        return None
    page = pdf.get_page(page_no)
    bmp = page.render(scale=scale, rotation=0)
    rgba = bmp.to_numpy()
    page.close(); pdf.close()
    # RGBA -> BGR for OpenCV / PaddleOCR
    bgr = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)
    
    # Apply preprocessing for better OCR
    return _preprocess_for_ocr(bgr)