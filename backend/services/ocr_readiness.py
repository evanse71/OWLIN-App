# -*- coding: utf-8 -*-
"""
OCR Readiness Check Service

This module provides dependency checking and readiness validation for OCR processing.
It verifies that all required dependencies are available before allowing document processing.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger("owlin.services.ocr_readiness")

# Import feature flags
from backend.config import (
    FEATURE_OCR_V2_LAYOUT,
    FEATURE_OCR_V2_PREPROC,
    FEATURE_OCR_V3_TABLES,
    FEATURE_OCR_PIPELINE_V2
)

@dataclass
class DependencyStatus:
    """Status of a single dependency"""
    name: str
    available: bool
    required: bool
    error: Optional[str] = None

@dataclass
class OCRReadinessResult:
    """Result of OCR readiness check"""
    ready: bool
    dependencies: List[DependencyStatus]
    missing_required: List[str]
    warnings: List[str]
    feature_flags: Dict[str, bool]

def check_pymupdf() -> DependencyStatus:
    """Check if PyMuPDF (fitz) is available"""
    # #region agent log
    import json
    import sys
    from pathlib import Path
    log_path = Path(__file__).parent.parent.parent / ".cursor" / "debug.log"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "ocr_readiness.py:42", "message": "check_pymupdf entry", "data": {"python_exe": sys.executable, "python_path": sys.path[:3]}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
    except: pass
    # #endregion
    try:
        import fitz
        # #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "ocr_readiness.py:45", "message": "fitz import successful", "data": {"fitz_module": str(fitz)}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        except: pass
        # #endregion
        # Try to create a simple document to verify it works
        doc = fitz.open()
        doc.close()
        # #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "ocr_readiness.py:50", "message": "fitz test successful", "data": {}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        except: pass
        # #endregion
        return DependencyStatus(
            name="PyMuPDF",
            available=True,
            required=True
        )
    except ImportError as e:
        # #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "ocr_readiness.py:56", "message": "ImportError caught", "data": {"error": str(e), "error_type": type(e).__name__}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        except: pass
        # #endregion
        return DependencyStatus(
            name="PyMuPDF",
            available=False,
            required=True,
            error="PyMuPDF (fitz) not installed. Install with: pip install PyMuPDF"
        )
    except Exception as e:
        # #region agent log
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "ocr_readiness.py:66", "message": "Exception caught (not ImportError)", "data": {"error": str(e), "error_type": type(e).__name__, "traceback": str(__import__("traceback").format_exc())[:500]}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        except: pass
        # #endregion
        return DependencyStatus(
            name="PyMuPDF",
            available=False,
            required=True,
            error=f"PyMuPDF available but error during test: {str(e)}"
        )

def check_opencv() -> DependencyStatus:
    """Check if OpenCV (cv2) is available"""
    try:
        import cv2
        import numpy as np
        # Try a simple operation to verify it works
        test_img = np.zeros((10, 10, 3), dtype=np.uint8)
        _ = cv2.cvtColor(test_img, cv2.COLOR_BGR2GRAY)
        return DependencyStatus(
            name="OpenCV",
            available=True,
            required=True
        )
    except ImportError:
        return DependencyStatus(
            name="OpenCV",
            available=False,
            required=True,
            error="OpenCV not installed. Install with: pip install opencv-python numpy"
        )
    except Exception as e:
        return DependencyStatus(
            name="OpenCV",
            available=False,
            required=True,
            error=f"OpenCV available but error during test: {str(e)}"
        )

def check_paddleocr() -> DependencyStatus:
    """Check if PaddleOCR is available"""
    try:
        from paddleocr import PaddleOCR
        # Don't initialize the model here (expensive), just check import
        return DependencyStatus(
            name="PaddleOCR",
            available=True,
            required=False  # Not required if Tesseract is available
        )
    except ImportError:
        return DependencyStatus(
            name="PaddleOCR",
            available=False,
            required=False,
            error="PaddleOCR not installed. Install with: pip install paddleocr"
        )
    except Exception as e:
        return DependencyStatus(
            name="PaddleOCR",
            available=False,
            required=False,
            error=f"PaddleOCR import error: {str(e)}"
        )

def check_tesseract() -> DependencyStatus:
    """Check if Tesseract OCR is available"""
    try:
        import pytesseract
        import os
        # Set Tesseract path for Windows if it exists
        default_windows_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        if os.path.exists(default_windows_path):
            pytesseract.pytesseract.tesseract_cmd = default_windows_path
        
        # Try to get version to verify it's actually working
        try:
            version = pytesseract.get_tesseract_version()
            return DependencyStatus(
                name="Tesseract",
                available=True,
                required=False  # Not required if PaddleOCR is available
            )
        except Exception as e:
            return DependencyStatus(
                name="Tesseract",
                available=False,
                required=False,
                error=f"Tesseract installed but not working: {str(e)}. Ensure tesseract binary is in PATH or set pytesseract.pytesseract.tesseract_cmd"
            )
    except ImportError:
        return DependencyStatus(
            name="Tesseract",
            available=False,
            required=False,
            error="pytesseract not installed. Install with: pip install pytesseract"
        )
    except Exception as e:
        return DependencyStatus(
            name="Tesseract",
            available=False,
            required=False,
            error=f"Tesseract check error: {str(e)}"
        )

def check_ocr_readiness() -> OCRReadinessResult:
    """
    Check OCR system readiness by verifying all required dependencies.
    
    Returns:
        OCRReadinessResult with status of all dependencies and overall readiness
    """
    dependencies = []
    missing_required = []
    warnings = []
    
    # Check required dependencies
    pymupdf_status = check_pymupdf()
    dependencies.append(pymupdf_status)
    if not pymupdf_status.available:
        missing_required.append(pymupdf_status.name)
    
    opencv_status = check_opencv()
    dependencies.append(opencv_status)
    if not opencv_status.available:
        missing_required.append(opencv_status.name)
    
    # Check OCR engines (at least one must be available)
    paddleocr_status = check_paddleocr()
    dependencies.append(paddleocr_status)
    
    tesseract_status = check_tesseract()
    dependencies.append(tesseract_status)
    
    # At least one OCR engine must be available
    ocr_engines_available = paddleocr_status.available or tesseract_status.available
    if not ocr_engines_available:
        missing_required.append("OCR Engine (PaddleOCR or Tesseract)")
        warnings.append("No OCR engine available. At least one of PaddleOCR or Tesseract must be installed.")
    
    # Check feature flags
    feature_flags = {
        "FEATURE_OCR_PIPELINE_V2": FEATURE_OCR_PIPELINE_V2,
        "FEATURE_OCR_V2_LAYOUT": FEATURE_OCR_V2_LAYOUT,
        "FEATURE_OCR_V2_PREPROC": FEATURE_OCR_V2_PREPROC,
        "FEATURE_OCR_V3_TABLES": FEATURE_OCR_V3_TABLES
    }
    
    # Warn about disabled critical features
    if not FEATURE_OCR_V2_LAYOUT:
        warnings.append("FEATURE_OCR_V2_LAYOUT is disabled - layout detection will not work")
    if not FEATURE_OCR_V2_PREPROC:
        warnings.append("FEATURE_OCR_V2_PREPROC is disabled - advanced preprocessing will not work")
    if not FEATURE_OCR_V3_TABLES:
        warnings.append("FEATURE_OCR_V3_TABLES is disabled - table extraction will not work")
    
    # System is ready if no required dependencies are missing
    ready = len(missing_required) == 0
    
    return OCRReadinessResult(
        ready=ready,
        dependencies=dependencies,
        missing_required=missing_required,
        warnings=warnings,
        feature_flags=feature_flags
    )

def get_readiness_summary() -> Dict[str, Any]:
    """
    Get a summary of OCR readiness status suitable for API responses.
    
    Returns:
        Dictionary with readiness status and details
    """
    result = check_ocr_readiness()
    
    return {
        "ready": result.ready,
        "status": "ready" if result.ready else "not_ready",
        "missing_required": result.missing_required,
        "warnings": result.warnings,
        "dependencies": {
            dep.name: {
                "available": dep.available,
                "required": dep.required,
                "error": dep.error
            }
            for dep in result.dependencies
        },
        "feature_flags": result.feature_flags
    }

