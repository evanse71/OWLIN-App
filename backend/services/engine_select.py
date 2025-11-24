# -*- coding: utf-8 -*-
"""
OCR Engine Selection Module

This module implements the engine selection logic as specified in the System Bible
Section 2.4 (lines 168-173).

Selection Priority:
1. Tesseract - for thermal receipts
2. docTR - for table-dense layouts (layout_score > 0.6)
3. PaddleOCR - default for multi-language PDFs
4. Calamari - optional fallback for printed legacy docs
"""

from __future__ import annotations
import logging
from typing import Any, Dict, Optional
from backend.services.ocr_engine_doctr import is_doctr_available
from backend.services.ocr_engine_calamari import is_calamari_available

LOGGER = logging.getLogger("owlin.ocr.engine_select")
LOGGER.setLevel(logging.INFO)

# Check availability of engines at module load
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    pytesseract = None

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    PaddleOCR = None


def select_engine(
    doc_type: Optional[str] = None,
    layout_score: float = 0.0,
    is_receipt: bool = False,
    is_legacy: bool = False
) -> str:
    """
    Select the appropriate OCR engine based on document characteristics.
    
    Implements the logic from System Bible Section 2.4:
    - if is_receipt: engine = "tesseract"
    - elif layout_score > 0.6: engine = "doctr"
    - else: engine = "paddleocr"
    
    Args:
        doc_type: Document type (e.g., "invoice", "receipt", "delivery_note")
        layout_score: Layout complexity score (0.0-1.0), >0.6 indicates table-dense
        is_receipt: Whether document is a thermal receipt
        is_legacy: Whether document is a legacy printed document
    
    Returns:
        Engine name: "tesseract", "doctr", "paddleocr", or "calamari"
    """
    # Priority 1: Thermal receipts → Tesseract
    if is_receipt or (doc_type and doc_type.lower() in ["receipt", "thermal_receipt"]):
        if TESSERACT_AVAILABLE:
            LOGGER.debug("Selected Tesseract for receipt document")
            return "tesseract"
        else:
            LOGGER.warning("Tesseract requested but not available, falling back to PaddleOCR")
            return "paddleocr" if PADDLEOCR_AVAILABLE else "fallback"
    
    # Priority 2: Table-dense layouts → docTR
    if layout_score > 0.6:
        if is_doctr_available():
            LOGGER.debug("Selected docTR for table-dense layout (score=%.2f)", layout_score)
            return "doctr"
        else:
            LOGGER.warning("docTR requested but not available (layout_score=%.2f), falling back to PaddleOCR", layout_score)
            return "paddleocr" if PADDLEOCR_AVAILABLE else "tesseract" if TESSERACT_AVAILABLE else "fallback"
    
    # Priority 3: Legacy printed documents → Calamari (optional)
    if is_legacy:
        if is_calamari_available():
            LOGGER.debug("Selected Calamari for legacy printed document")
            return "calamari"
        else:
            LOGGER.debug("Calamari not available for legacy doc, using PaddleOCR")
            return "paddleocr" if PADDLEOCR_AVAILABLE else "tesseract" if TESSERACT_AVAILABLE else "fallback"
    
    # Priority 4: Default → PaddleOCR
    if PADDLEOCR_AVAILABLE:
        LOGGER.debug("Selected PaddleOCR as default engine")
        return "paddleocr"
    
    # Fallback chain
    if TESSERACT_AVAILABLE:
        LOGGER.warning("PaddleOCR not available, falling back to Tesseract")
        return "tesseract"
    
    if is_doctr_available():
        LOGGER.warning("PaddleOCR and Tesseract not available, falling back to docTR")
        return "doctr"
    
    if is_calamari_available():
        LOGGER.warning("Other engines not available, falling back to Calamari")
        return "calamari"
    
    LOGGER.error("No OCR engines available!")
    return "fallback"


def get_config(engine_name: str) -> Dict[str, Any]:
    """
    Get engine-specific configuration.
    
    Args:
        engine_name: Name of the OCR engine
    
    Returns:
        Configuration dictionary for the engine
    """
    configs = {
        "tesseract": {
            "config": "--oem 3 --psm 6",
            "lang": "eng",
            "use_gpu": False,
            "description": "Tesseract 5.x for thermal receipts and monochrome scans"
        },
        "doctr": {
            "model": "db_resnet50",
            "pretrained": True,
            "use_gpu": False,
            "description": "docTR for table-dense and multi-column layouts"
        },
        "paddleocr": {
            "lang": "en",
            "use_angle_cls": True,
            "use_gpu": False,
            "show_log": False,
            "description": "PaddleOCR VL-0.9B for multi-language PDFs"
        },
        "calamari": {
            "model": "latin_printed",
            "use_gpu": False,
            "description": "Calamari for printed legacy documents"
        },
        "fallback": {
            "description": "No OCR engine available - fallback mode"
        }
    }
    
    return configs.get(engine_name, configs["fallback"])


def get_available_engines() -> Dict[str, bool]:
    """
    Get status of all OCR engines.
    
    Returns:
        Dictionary mapping engine names to availability status
    """
    return {
        "paddleocr": PADDLEOCR_AVAILABLE,
        "tesseract": TESSERACT_AVAILABLE,
        "doctr": is_doctr_available(),
        "calamari": is_calamari_available()
    }


def validate_engine_selection(engine_name: str) -> bool:
    """
    Validate that the selected engine is available.
    
    Args:
        engine_name: Name of the OCR engine to validate
    
    Returns:
        True if engine is available, False otherwise
    """
    available = get_available_engines()
    return available.get(engine_name, False)


def get_fallback_chain(primary_engine: str) -> list[str]:
    """
    Get fallback chain for a given primary engine.
    
    Args:
        primary_engine: Primary engine name
    
    Returns:
        List of engine names in fallback order
    """
    chains = {
        "paddleocr": ["paddleocr", "doctr", "tesseract", "calamari"],
        "doctr": ["doctr", "paddleocr", "tesseract", "calamari"],
        "tesseract": ["tesseract", "paddleocr", "doctr", "calamari"],
        "calamari": ["calamari", "paddleocr", "tesseract", "doctr"]
    }
    
    return chains.get(primary_engine, ["paddleocr", "tesseract", "doctr", "calamari"])

