from typing import Literal
import cv2
import numpy as np

def detect_document_type(text: str) -> Literal["invoice", "delivery_note", "unknown"]:
    """
    Detects whether the document is an invoice, delivery note, or unknown based on text heuristics.
    """
    text_l = text.lower()
    invoice_keywords = ["invoice", "total", "vat", "supplier", "invoice number"]
    delivery_keywords = ["delivery", "delivered", "received by", "note", "items delivered"]

    invoice_score = sum(1 for k in invoice_keywords if k in text_l)
    delivery_score = sum(1 for k in delivery_keywords if k in text_l)

    if invoice_score > delivery_score and invoice_score > 0:
        return "invoice"
    elif delivery_score > invoice_score and delivery_score > 0:
        return "delivery_note"
    elif invoice_score == delivery_score and invoice_score > 0:
        return "unknown"
    else:
        return "unknown"


def preprocess_image(image_path: str) -> np.ndarray:
    """
    Applies grayscale, thresholding, and de-noising to improve OCR accuracy.
    Returns a cleaned OpenCV image ready for OCR.
    """
    # Read image
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not read image at {image_path}")
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
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