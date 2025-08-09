"""
Bulletproof Ingestion v3 - Universal Document Processing System

This module provides a comprehensive, resilient document ingestion system that can handle
any upload scenario: invoices, delivery notes, receipts, utility bills, mixed packs,
out-of-order pages, split files, duplicates, and more.

Key Features:
- Universal intake with perceptual hashing and layout fingerprints
- Page classification (Invoice/Delivery/Receipt/Utility/Other)
- Cross-file stitching for split documents
- Deduplication engine
- Canonical entity building
- Advanced parsing with Qwen2.5-VL
- Review UIs for low-confidence cases
- Fully offline processing
"""

from .intake_router import IntakeRouter
from .page_fingerprints import PageFingerprinter
from .page_classifier import PageClassifier
from .cross_file_stitcher import CrossFileStitcher
from .deduper import Deduper
from .canonical_builder import CanonicalBuilder

__all__ = [
    'IntakeRouter',
    'PageFingerprinter', 
    'PageClassifier',
    'CrossFileStitcher',
    'Deduper',
    'CanonicalBuilder'
] 