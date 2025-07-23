from typing import Literal
import cv2
import numpy as np


def detect_document_type(text: str) -> Literal["invoice", "delivery_note", "unknown"]:
    """Detect whether text resembles an invoice or delivery note."""
    text_l = text.lower()
    invoice_keywords = ["invoice", "total", "vat", "supplier", "invoice number"]
    delivery_keywords = ["delivery", "delivered", "received by", "note", "items delivered"]

    invoice_score = sum(1 for k in invoice_keywords if k in text_l)
    delivery_score = sum(1 for k in delivery_keywords if k in text_l)

    if invoice_score > delivery_score and invoice_score > 0:
        return "invoice"
    if delivery_score > invoice_score and delivery_score > 0:
        return "delivery_note"
    if invoice_score == delivery_score and invoice_score > 0:
        return "unknown"
    return "unknown"


def preprocess_image(image_path: str) -> np.ndarray:
    """Load and enhance an image for optimal OCR accuracy."""
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not read image at {image_path}")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Deskew based on text orientation
    coords = np.column_stack(np.where(gray > 0))
    if coords.size > 0:
        angle = cv2.minAreaRect(coords)[-1]
        angle = -(90 + angle) if angle < -45 else -angle
        (h, w) = gray.shape[:2]
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        gray = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    # Reduce noise
    denoised = cv2.medianBlur(gray, 3)

    # Apply Otsu thresholding
    _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Boost contrast with CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(thresh)

    # Sharpen result
    blurred = cv2.GaussianBlur(enhanced, (0, 0), 1)
    sharp = cv2.addWeighted(enhanced, 1.5, blurred, -0.5, 0)

    return sharp 