# backend/fallbacks/__init__.py
"""
Fallback Processing Module for Owlin

This module provides fallback processing capabilities for difficult documents
when standard OCR fails or produces low confidence results.

Features:
- Donut model fallback for document parsing
- Confidence-triggered fallback activation
- Safe output mapping to invoice card JSON
- Offline-first design with graceful degradation
- Comprehensive audit logging
"""

from .donut_fallback import DonutFallback, get_donut_fallback
from .mapper import map_donut_to_invoice_card, merge_invoice_cards, validate_invoice_card

__all__ = [
    'DonutFallback',
    'get_donut_fallback',
    'map_donut_to_invoice_card',
    'merge_invoice_cards',
    'validate_invoice_card'
]
