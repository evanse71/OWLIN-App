"""
OCR module for Owlin - PaddleOCR implementation
"""

from .ocr_engine import (
    run_invoice_ocr,
    get_paddle_ocr_model,
    extract_text_from_pdf,
    extract_text_with_paddle_ocr,
    preprocess_image,
    OCRResult
)

from .ocr_processing import (
    run_ocr,
    run_ocr_with_fallback,
    validate_ocr_results,
    get_ocr_summary,
    TESSERACT_AVAILABLE
)

__all__ = [
    'run_invoice_ocr',
    'get_paddle_ocr_model',
    'extract_text_from_pdf',
    'extract_text_with_paddle_ocr',
    'preprocess_image',
    'OCRResult',
    'run_ocr',
    'run_ocr_with_fallback',
    'validate_ocr_results',
    'get_ocr_summary',
    'TESSERACT_AVAILABLE'
] 