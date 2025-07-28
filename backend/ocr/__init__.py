"""
OCR Module for Owlin Invoice Processing

This module provides comprehensive OCR capabilities for processing invoice PDFs:
- Enhanced OCR engine with preprocessing
- Table extraction and line item parsing
- Invoice metadata extraction
- Confidence scoring and quality assessment
"""

from .ocr_engine import run_ocr, extract_text_with_table_awareness, calculate_confidence
from .table_extractor import extract_table_data, extract_line_items_from_text
from .parse_invoice import extract_invoice_metadata, extract_line_items, calculate_confidence

__all__ = [
    'run_ocr',
    'extract_text_with_table_awareness', 
    'calculate_confidence',
    'extract_table_data',
    'extract_line_items_from_text',
    'extract_invoice_metadata',
    'extract_line_items'
] 