# backend/ocr/engine.py
from typing import Optional, Dict
import os
import logging

logger = logging.getLogger("owlin.ocr")

def run_ocr_and_parse(pdf_path: str) -> Optional[Dict]:
    """
    Returns a dict like:
      {"supplier": "...", "date": "2025-10-02", "value": 123.45, "confidence": 0.87}
    or None if parsing fails.
    
    This is a graceful, offline-safe implementation that can be extended
    with real OCR engines like PaddleOCR or Tesseract.
    """
    try:
        # Check if file exists
        if not os.path.exists(pdf_path):
            logger.warning(f"OCR: File not found: {pdf_path}")
            return None
        
        # TODO: Plug in real OCR engine here (PaddleOCR/Tesseract)
        # For now, return a minimal stub that's offline-safe
        logger.info(f"OCR: Processing {pdf_path} (mock mode)")
        
        # Mock OCR result - replace with real OCR when ready
        return {
            "supplier": "Unknown",
            "date": None,
            "value": None,
            "confidence": 0.0,
            "status": "mock",
            "venue": "Unknown"
        }
        
    except Exception as e:
        logger.error(f"OCR failed for {pdf_path}: {e}")
        return None

def is_ocr_available() -> bool:
    """
    Check if OCR dependencies are available.
    Returns True if OCR can be used, False otherwise.
    """
    try:
        # TODO: Check for real OCR dependencies
        # import paddleocr  # or import pytesseract
        # return True
        return False  # Mock mode for now
    except ImportError:
        return False
    except Exception:
        return False
