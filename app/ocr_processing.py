"""
ocr_processing.py
=================

This module defines a helper function ``run_ocr`` that wraps the
OCR process for invoice files.  It attempts to utilise pytesseract
to extract text from images or PDF documents.  If pytesseract is not
available in the environment, the function falls back to a stub
implementation which returns an empty list.  The returned structure
matches the expectations of ``field_extractor.extract_invoice_fields``.

In a production deployment, ensure that pytesseract and its
dependencies (including Tesseract OCR and, optionally, pdf2image for
PDF conversion) are installed and configured correctly.  See
https://github.com/madmaze/pytesseract for installation details.
"""

from __future__ import annotations

import os
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import pytesseract  # type: ignore
    from PIL import Image  # type: ignore
    import pdf2image  # type: ignore
    TESSERACT_AVAILABLE = True
    logger.info("✅ pytesseract and dependencies available")
except ImportError as e:
    pytesseract = None  # type: ignore
    TESSERACT_AVAILABLE = False
    logger.warning(f"⚠️ pytesseract not available: {e}")


def run_ocr(file_path: str) -> List[Dict[str, Any]]:
    """Run OCR on a given invoice file and return recognised text blocks.

    This function supports both images (JPEG, PNG, TIFF) and PDF
    documents.  For images, it directly invokes pytesseract.  For
    PDFs, it uses pdf2image to convert each page to an image before
    OCR.  Each text block in the returned list is a dictionary with
    keys ``text``, ``bbox``, ``confidence`` and ``page_num``.  If
    OCR cannot be performed (e.g. required libraries are not
    available), the function raises a RuntimeError.

    Parameters
    ----------
    file_path: str
        Absolute path to the invoice file on disk.

    Returns
    -------
    List[Dict[str, Any]]
        A list of OCR results ready for field extraction.

    Raises
    ------
    RuntimeError
        If OCR dependencies are missing or processing fails.
    """
    # If pytesseract is not available, fail loudly
    if not TESSERACT_AVAILABLE or pytesseract is None:
        error_msg = "OCR functionality is unavailable: install pytesseract and dependencies"
        logger.error(f"❌ {error_msg}")
        raise RuntimeError(error_msg)
    
    # Determine file type
    ext = os.path.splitext(file_path.lower())[1]
    results: List[Dict[str, Any]] = []
    
    try:
        logger.info(f"🔄 Running Tesseract OCR on {file_path}")
        
        if ext in {".jpg", ".jpeg", ".png", ".tiff"}:
            img = Image.open(file_path)
            ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            n = len(ocr_data["text"])
            
            for i in range(n):
                text = ocr_data["text"][i].strip()
                if not text:
                    continue
                x, y, w, h = (
                    ocr_data["left"][i],
                    ocr_data["top"][i],
                    ocr_data["width"][i],
                    ocr_data["height"][i],
                )
                conf = float(ocr_data["conf"][i]) if ocr_data["conf"][i] != "-1" else 0.0
                results.append(
                    {
                        "text": text,
                        "bbox": [x, y, x + w, y + h],
                        "confidence": conf,
                        "page_num": 1,
                    }
                )
                
        elif ext == ".pdf":
            # Convert PDF pages to images
            logger.info("📄 Converting PDF pages to images for OCR")
            pages = pdf2image.convert_from_path(file_path)
            
            for page_num, page in enumerate(pages, 1):
                logger.info(f"🔄 Processing page {page_num} of {len(pages)}")
                ocr_data = pytesseract.image_to_data(page, output_type=pytesseract.Output.DICT)
                n = len(ocr_data["text"])
                
                for i in range(n):
                    text = ocr_data["text"][i].strip()
                    if not text:
                        continue
                    x, y, w, h = (
                        ocr_data["left"][i],
                        ocr_data["top"][i],
                        ocr_data["width"][i],
                        ocr_data["height"][i],
                    )
                    conf = float(ocr_data["conf"][i]) if ocr_data["conf"][i] != "-1" else 0.0
                    results.append(
                        {
                            "text": text,
                            "bbox": [x, y, x + w, y + h],
                            "confidence": conf,
                            "page_num": page_num,
                        }
                    )
        else:
            logger.warning(f"⚠️ Unsupported file type: {ext}")
            raise RuntimeError(f"Unsupported file type: {ext}. Supported formats: .pdf, .jpg, .jpeg, .png, .tiff")
        
        logger.info(f"✅ Tesseract OCR completed: {len(results)} text blocks found")
        return results
        
    except Exception as e:
        logger.error(f"❌ OCR processing failed for {file_path}: {str(e)}")
        raise RuntimeError(f"OCR processing failed: {str(e)}")


def run_ocr_with_fallback(file_path: str, use_paddle_first: bool = True) -> List[Dict[str, Any]]:
    """Run OCR with fallback strategy - try PaddleOCR first, then Tesseract.
    
    Parameters
    ----------
    file_path: str
        Absolute path to the invoice file on disk.
    use_paddle_first: bool
        If True, try PaddleOCR first, then fall back to Tesseract.
        If False, use Tesseract only.
        
    Returns
    -------
    List[Dict[str, Any]]
        OCR results from the best available method.
    """
    if use_paddle_first:
        try:
            # Try PaddleOCR first
            from .ocr_engine import run_invoice_ocr
            from PIL import Image
            
            logger.info("🔄 Attempting PaddleOCR first...")
            
            # Convert file to PIL Image for PaddleOCR
            if file_path.lower().endswith('.pdf'):
                from pdf2image import convert_from_path
                pages = convert_from_path(file_path)
                all_results = []
                
                for page_num, page in enumerate(pages, 1):
                    ocr_results = run_invoice_ocr(page, page_num)
                    for result in ocr_results:
                        all_results.append({
                            "text": result.text,
                            "bbox": result.bounding_box,
                            "confidence": result.confidence,
                            "page_num": result.page_number
                        })
                
                if all_results:
                    logger.info(f"✅ PaddleOCR successful: {len(all_results)} text blocks")
                    return all_results
                    
            else:
                img = Image.open(file_path)
                ocr_results = run_invoice_ocr(img, 1)
                results = []
                
                for result in ocr_results:
                    results.append({
                        "text": result.text,
                        "bbox": result.bounding_box,
                        "confidence": result.confidence,
                        "page_num": result.page_number
                    })
                
                if results:
                    logger.info(f"✅ PaddleOCR successful: {len(results)} text blocks")
                    return results
                    
        except Exception as e:
            logger.warning(f"⚠️ PaddleOCR failed, falling back to Tesseract: {e}")
    
    # Fall back to Tesseract
    logger.info("🔄 Using Tesseract OCR fallback...")
    return run_ocr(file_path)


def validate_ocr_results(results: List[Dict[str, Any]]) -> bool:
    """Validate OCR results for quality and completeness.
    
    Parameters
    ----------
    results: List[Dict[str, Any]]
        OCR results to validate
        
    Returns
    -------
    bool
        True if results are valid, False otherwise
    """
    if not results:
        return False
    
    # Check for minimum text content
    total_text = " ".join([r.get("text", "") for r in results])
    if len(total_text.strip()) < 10:  # Minimum 10 characters
        return False
    
    # Check for reasonable confidence scores
    avg_confidence = sum(r.get("confidence", 0) for r in results) / len(results)
    if avg_confidence < 30:  # Minimum 30% average confidence
        return False
    
    return True


def get_ocr_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate a summary of OCR results.
    
    Parameters
    ----------
    results: List[Dict[str, Any]]
        OCR results to summarize
        
    Returns
    -------
    Dict[str, Any]
        Summary statistics
    """
    if not results:
        return {
            "total_blocks": 0,
            "total_text_length": 0,
            "average_confidence": 0.0,
            "pages_processed": 0,
            "quality_score": 0.0
        }
    
    total_blocks = len(results)
    total_text_length = sum(len(r.get("text", "")) for r in results)
    average_confidence = sum(r.get("confidence", 0) for r in results) / total_blocks
    pages_processed = len(set(r.get("page_num", 1) for r in results))
    
    # Calculate quality score (0-100)
    quality_score = min(100, (average_confidence * 0.7) + (min(total_text_length / 100, 30) * 0.3))
    
    return {
        "total_blocks": total_blocks,
        "total_text_length": total_text_length,
        "average_confidence": round(average_confidence, 2),
        "pages_processed": pages_processed,
        "quality_score": round(quality_score, 2)
    } 