# backend/htr/__init__.py
"""
Handwriting Recognition (HTR) Module for Owlin

This module provides offline handwriting recognition capabilities using Kraken
as the primary engine, with graceful fallbacks and comprehensive error handling.

Features:
- Kraken-based HTR with PyLaia fallback support
- Confidence-based routing to review queue
- SQLite sample storage for training data
- Offline-first design with feature toggles
- Comprehensive audit logging
"""

from .base import HTRResult, HTRBlock, HTRConfig, HTRModelType, HTRStatus
from .integration import HTRProcessor, get_htr_processor
from .kraken_driver import KrakenDriver
from .dataset import HTRSampleStorage

__all__ = [
    'HTRResult',
    'HTRBlock', 
    'HTRConfig',
    'HTRModelType',
    'HTRStatus',
    'HTRProcessor',
    'get_htr_processor',
    'KrakenDriver',
    'HTRSampleStorage'
]
