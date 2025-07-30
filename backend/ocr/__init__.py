"""
OCR module for Owlin - PaddleOCR implementation
"""

from .ocr_engine import (
    run_paddle_ocr,
    run_enhanced_ocr,
    extract_text_with_table_awareness,
    calculate_confidence,
    calculate_display_confidence
)

__all__ = [
    'run_paddle_ocr',
    'run_enhanced_ocr',
    'extract_text_with_table_awareness',
    'calculate_confidence',
    'calculate_display_confidence'
] 