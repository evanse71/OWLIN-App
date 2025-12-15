# -*- coding: utf-8 -*-
"""
PaddleOCR Integration for Per-Block Text Extraction

This module provides high-accuracy OCR processing for each detected layout block,
using PaddleOCR with PP-Structure for structure-aware text extraction.

Features:
- PaddleOCR PP-Structure integration for printed text
- Per-block OCR processing with confidence scoring
- Multilingual support for invoices/receipts
- Tesseract fallback for robust operation
- JSON artifact storage for downstream processing
- Comprehensive error handling and logging
"""

from __future__ import annotations
import json
import logging
import os
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import time

# Import telemetry utilities
from backend.ocr.ocr_telemetry import (
    OCRTelemetryReport, PageTelemetry, BlockTelemetry, OverallTelemetry,
    count_words, determine_engine_mix, categorize_block_type
)

# Import configuration
from backend.config import FEATURE_OCR_V2_LAYOUT, OCR_ARTIFACT_ROOT

# Optional imports with graceful fallback
try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    cv2 = None
    np = None

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    PaddleOCR = None

try:
    import pytesseract
    import os
    # Set Tesseract path for Windows if it exists, otherwise rely on PATH
    default_windows_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(default_windows_path):
        pytesseract.pytesseract.tesseract_cmd = default_windows_path
    # If not found, pytesseract will use PATH (which works if tesseract is installed)
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    pytesseract = None

LOGGER = logging.getLogger("owlin.ocr.processor")
LOGGER.setLevel(logging.INFO)


@dataclass
class OCRResult:
    """Represents OCR result for a single block."""
    type: str
    bbox: Tuple[int, int, int, int]  # x, y, width, height
    ocr_text: str
    confidence: float
    method_used: str  # "paddleocr", "tesseract", "fallback"
    processing_time: float
    field_count: int = 0
    line_count: int = 0
    word_blocks: List[Dict[str, Any]] = None  # Spatial info for table extraction
    psm_mode: Optional[str] = None  # Tesseract PSM mode if used
    preprocessing_path: Optional[str] = None  # Preprocessing path used
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "type": self.type,
            "bbox": list(self.bbox),
            "ocr_text": self.ocr_text,
            "confidence": self.confidence,
            "method_used": self.method_used,
            "processing_time": self.processing_time,
            "field_count": self.field_count,
            "line_count": self.line_count
        }
        if self.word_blocks:
            result["word_blocks"] = self.word_blocks
        return result


@dataclass
class PageOCRResult:
    """Complete OCR result for a page."""
    page_num: int
    blocks: List[OCRResult]
    processing_time: float
    method_used: str
    confidence_avg: float
    low_confidence_blocks: int = 0
    preprocessing_path: Optional[str] = None  # Preprocessing path used for this page
    errors: List[str] = field(default_factory=list)  # Errors encountered during processing
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "page_num": self.page_num,
            "blocks": [block.to_dict() for block in self.blocks],
            "processing_time": self.processing_time,
            "method_used": self.method_used,
            "confidence_avg": self.confidence_avg,
            "low_confidence_blocks": self.low_confidence_blocks
        }


class OCRProcessor:
    """High-accuracy OCR processor with PaddleOCR and fallbacks."""
    
    def __init__(self):
        self._paddle_ocr = None
        self._tesseract_config = '--oem 3 --psm 6'
        self._confidence_threshold = 0.7
        self._block_type_configs = {
            "header": {"lang": "en", "use_angle_cls": True, "use_gpu": False},
            "table": {"lang": "en", "use_angle_cls": True, "use_gpu": False, "structure": True},
            "footer": {"lang": "en", "use_angle_cls": True, "use_gpu": False},
            "body": {"lang": "en", "use_angle_cls": True, "use_gpu": False},
            "handwriting": {"lang": "en", "use_angle_cls": False, "use_gpu": False}
        }
    
    def _load_paddle_ocr(self) -> Optional[PaddleOCR]:
        """Load PaddleOCR with PP-Structure support."""
        if self._paddle_ocr is not None:
            return self._paddle_ocr
            
        if not PADDLEOCR_AVAILABLE:
            LOGGER.warning("PaddleOCR not available, will use Tesseract fallback")
            return None
            
        try:
            # Set protobuf environment variable before importing/using PaddleOCR
            import os
            os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
            LOGGER.info("Loading PaddleOCR with PP-Structure support...")
            # Initialize with structure support for table processing
            # Note: use_angle_cls and use_gpu are deprecated in newer PaddleOCR versions
            self._paddle_ocr = PaddleOCR(
                use_textline_orientation=True,  # Replaces use_angle_cls
                lang='en'
                # use_gpu and show_log removed (deprecated)
            )
            LOGGER.info("PaddleOCR loaded successfully with PP-Structure support")
            return self._paddle_ocr
            
        except Exception as e:
            LOGGER.error("Failed to load PaddleOCR: %s", e)
            self._paddle_ocr = None
            return None
    
    def _ocr_with_paddle_detailed(self, image: np.ndarray, block_type: str) -> Tuple[str, float, float, List[Dict[str, Any]]]:
        """
        Run PaddleOCR and return detailed word blocks with spatial information.
        This enables spatial clustering for table extraction.
        
        Returns:
            Tuple of (combined_text, avg_confidence, processing_time, word_blocks)
            where word_blocks is a list of dicts with 'text' and 'bbox' keys
        """
        ocr = self._load_paddle_ocr()
        if ocr is None:
            return "", 0.0, 0.0, []
            
        try:
            start_time = time.time()
            
            # Get block-specific configuration
            config = self._block_type_configs.get(block_type, self._block_type_configs["body"])
            
            # Run OCR with appropriate settings
            if block_type == "table" and hasattr(ocr, 'ocr_table'):
                # Use table-specific OCR for better structure understanding
                result = ocr.ocr_table(image)
            else:
                # Standard OCR for other block types
                result = ocr.ocr(image)
            
            processing_time = time.time() - start_time
            
            # DEFENSIVE: Check result structure
            if not result:
                LOGGER.debug("PaddleOCR returned None or empty result")
                return "", 0.0, processing_time, []
            
            if not isinstance(result, (list, tuple)) or len(result) == 0:
                LOGGER.warning("PaddleOCR returned unexpected result type: %s", type(result))
                return "", 0.0, processing_time, []
            
            if not result[0]:
                LOGGER.debug("PaddleOCR result[0] is empty")
                return "", 0.0, processing_time, []
            
            if not isinstance(result[0], (list, tuple)):
                LOGGER.warning("PaddleOCR result[0] is not a list/tuple: %s", type(result[0]))
                return "", 0.0, processing_time, []
            
            # Enable debug logging if environment variable is set
            debug_ocr = os.environ.get("OWLIN_DEBUG_OCR", "0") == "1"
            if debug_ocr:
                LOGGER.info("[DEBUG] PaddleOCR result structure: type=%s, len(result)=%d, len(result[0])=%d", 
                           type(result), len(result), len(result[0]))
            
            # Extract text, confidence, and spatial information
            texts = []
            confidences = []
            word_blocks = []
            malformed_count = 0
            
            for idx, line in enumerate(result[0]):
                # DEFENSIVE: Validate line structure
                if not isinstance(line, (list, tuple)):
                    if debug_ocr:
                        LOGGER.warning("[DEBUG] Line %d is not list/tuple: %s (type=%s)", idx, line, type(line))
                    malformed_count += 1
                    continue
                
                if len(line) < 2:
                    if debug_ocr:
                        LOGGER.warning("[DEBUG] Line %d has < 2 elements: %s", idx, line)
                    malformed_count += 1
                    continue
                
                # DEFENSIVE: Extract bbox and text_info safely
                bbox = line[0]
                text_info = line[1]
                
                # Validate bbox structure
                if not isinstance(bbox, (list, tuple)) or len(bbox) < 4:
                    if debug_ocr:
                        LOGGER.warning("[DEBUG] Line %d has invalid bbox: %s", idx, bbox)
                    malformed_count += 1
                    # Try to continue with text extraction even if bbox is bad
                    bbox = None
                
                # DEFENSIVE: Extract text and confidence from text_info
                text = ""
                conf = 0.5
                
                if isinstance(text_info, tuple) and len(text_info) >= 2:
                    text = str(text_info[0]) if text_info[0] is not None else ""
                    try:
                        conf = float(text_info[1]) if text_info[1] is not None else 0.5
                    except (ValueError, TypeError):
                        conf = 0.5
                elif isinstance(text_info, dict):
                    text = str(text_info.get("text", ""))
                    try:
                        conf = float(text_info.get("confidence", 0.5))
                    except (ValueError, TypeError):
                        conf = 0.5
                elif isinstance(text_info, str):
                    text = text_info
                    conf = 0.5
                else:
                    text = str(text_info) if text_info is not None else ""
                    conf = 0.5
                
                if text:
                    texts.append(text)
                    confidences.append(conf)
                
                # Convert bbox to [x, y, w, h] format (only if bbox is valid)
                if bbox and isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                    try:
                        # bbox is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                        # Validate each point is a list/tuple with 2 elements
                        valid_points = []
                        for pt in bbox:
                            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                                try:
                                    x_val = float(pt[0])
                                    y_val = float(pt[1])
                                    valid_points.append((x_val, y_val))
                                except (ValueError, TypeError, IndexError):
                                    if debug_ocr:
                                        LOGGER.warning("[DEBUG] Invalid bbox point: %s", pt)
                                    continue
                        
                        if len(valid_points) >= 4:
                            x_coords = [pt[0] for pt in valid_points]
                            y_coords = [pt[1] for pt in valid_points]
                            x_min = int(min(x_coords))
                            y_min = int(min(y_coords))
                            x_max = int(max(x_coords))
                            y_max = int(max(y_coords))
                            
                            word_blocks.append({
                                'text': text,
                                'bbox': [x_min, y_min, x_max - x_min, y_max - y_min],
                                'confidence': conf
                            })
                    except Exception as bbox_error:
                        if debug_ocr:
                            LOGGER.warning("[DEBUG] Error processing bbox for line %d: %s", idx, bbox_error)
            
            if malformed_count > 0:
                LOGGER.warning("Skipped %d malformed OCR entries out of %d total", malformed_count, len(result[0]))
            
            # Combine text and calculate average confidence
            combined_text = "\n".join(texts).strip()
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            LOGGER.debug("PaddleOCR extracted %d lines with spatial info, avg confidence: %.3f", 
                        len(texts), avg_confidence)
            
            return combined_text, avg_confidence, processing_time, word_blocks
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            LOGGER.error("PaddleOCR processing failed: %s", e)
            if os.environ.get("OWLIN_DEBUG_OCR", "0") == "1":
                LOGGER.error("[DEBUG] Full traceback:\n%s", error_detail)
            return "", 0.0, 0.0, []
    
    def _ocr_with_paddle(self, image: np.ndarray, block_type: str) -> Tuple[str, float, float]:
        """Run PaddleOCR on image block with type-specific configuration."""
        ocr = self._load_paddle_ocr()
        if ocr is None:
            return "", 0.0, 0.0
            
        try:
            start_time = time.time()
            
            # Get block-specific configuration
            config = self._block_type_configs.get(block_type, self._block_type_configs["body"])
            
            # Run OCR with appropriate settings
            if block_type == "table" and hasattr(ocr, 'ocr_table'):
                # Use table-specific OCR for better structure understanding
                result = ocr.ocr_table(image)
            else:
                # Standard OCR for other block types
                result = ocr.ocr(image)
            
            processing_time = time.time() - start_time
            
            # DEFENSIVE: Check result structure
            if not result:
                LOGGER.debug("PaddleOCR returned None or empty result")
                return "", 0.0, processing_time
            
            if not isinstance(result, (list, tuple)) or len(result) == 0:
                LOGGER.warning("PaddleOCR returned unexpected result type: %s", type(result))
                return "", 0.0, processing_time
            
            if not result[0]:
                LOGGER.debug("PaddleOCR result[0] is empty")
                return "", 0.0, processing_time
            
            if not isinstance(result[0], (list, tuple)):
                LOGGER.warning("PaddleOCR result[0] is not a list/tuple: %s", type(result[0]))
                return "", 0.0, processing_time
            
            # Enable debug logging if environment variable is set
            debug_ocr = os.environ.get("OWLIN_DEBUG_OCR", "0") == "1"
            if debug_ocr:
                LOGGER.info("[DEBUG] PaddleOCR result structure: type=%s, len(result)=%d, len(result[0])=%d", 
                           type(result), len(result), len(result[0]))
            
            # Extract text and confidence
            texts = []
            confidences = []
            malformed_count = 0
            
            for idx, line in enumerate(result[0]):
                # DEFENSIVE: Validate line structure
                if not isinstance(line, (list, tuple)):
                    if debug_ocr:
                        LOGGER.warning("[DEBUG] Line %d is not list/tuple: %s (type=%s)", idx, line, type(line))
                    malformed_count += 1
                    continue
                
                if len(line) < 2:
                    if debug_ocr:
                        LOGGER.warning("[DEBUG] Line %d has < 2 elements: %s", idx, line)
                    malformed_count += 1
                    continue
                
                # DEFENSIVE: Extract text_info safely
                text_info = line[1]
                text = ""
                conf = 0.5
                
                if isinstance(text_info, tuple) and len(text_info) >= 2:
                    text = str(text_info[0]) if text_info[0] is not None else ""
                    try:
                        conf = float(text_info[1]) if text_info[1] is not None else 0.5
                    except (ValueError, TypeError):
                        conf = 0.5
                elif isinstance(text_info, dict):
                    text = str(text_info.get("text", ""))
                    try:
                        conf = float(text_info.get("confidence", 0.5))
                    except (ValueError, TypeError):
                        conf = 0.5
                elif isinstance(text_info, str):
                    text = text_info
                    conf = 0.5
                else:
                    text = str(text_info) if text_info is not None else ""
                    conf = 0.5
                
                if text:
                    texts.append(text)
                    confidences.append(conf)
            
            if malformed_count > 0:
                LOGGER.warning("Skipped %d malformed OCR entries out of %d total", malformed_count, len(result[0]))
            
            # Combine text and calculate average confidence
            combined_text = "\n".join(texts).strip()
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            LOGGER.debug("PaddleOCR extracted %d lines, avg confidence: %.3f", 
                        len(texts), avg_confidence)
            
            return combined_text, avg_confidence, processing_time
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            LOGGER.error("PaddleOCR processing failed: %s", e)
            if os.environ.get("OWLIN_DEBUG_OCR", "0") == "1":
                LOGGER.error("[DEBUG] Full traceback:\n%s", error_detail)
            return "", 0.0, 0.0
    
    def _ocr_with_tesseract(self, image: np.ndarray, block_type: str) -> Tuple[str, float, float, Optional[str]]:
        """Fallback OCR using Tesseract."""
        if not TESSERACT_AVAILABLE:
            LOGGER.warning("Tesseract not available for fallback OCR")
            return "", 0.0, 0.0, None
            
        try:
            start_time = time.time()
            
            # Configure Tesseract based on block type
            if block_type == "table":
                config = '--oem 3 --psm 6'  # Uniform block of text
                psm_mode = "6"
            elif block_type == "header":
                config = '--oem 3 --psm 7'  # Single text line
                psm_mode = "7"
            else:
                config = '--oem 3 --psm 6'  # Default
                psm_mode = "6"
            
            # Run Tesseract OCR
            text = pytesseract.image_to_string(image, config=config).strip()
            
            # Get confidence data
            try:
                data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
                confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                avg_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0
            except:
                avg_confidence = 0.5  # Default confidence if data extraction fails
            
            processing_time = time.time() - start_time
            
            LOGGER.debug("Tesseract extracted text, confidence: %.3f", avg_confidence)
            
            return text, avg_confidence, processing_time, psm_mode
            
        except Exception as e:
            LOGGER.error("Tesseract OCR failed: %s", e)
            return "", 0.0, 0.0, None
    
    def _extract_block_image(self, full_image: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
        """Extract image region for a specific block."""
        x, y, w, h = bbox
        
        # Ensure coordinates are within image bounds
        h_img, w_img = full_image.shape[:2]
        x = max(0, min(x, w_img - 1))
        y = max(0, min(y, h_img - 1))
        w = max(1, min(w, w_img - x))
        h = max(1, min(h, h_img - y))
        
        # Extract region
        block_image = full_image[y:y+h, x:x+w]
        
        # Ensure we have a valid image
        if block_image.size == 0:
            LOGGER.warning("Empty block image extracted at %s", bbox)
            return np.ones((50, 200, 3), dtype=np.uint8) * 255  # Return white image
        
        return block_image
    
    def _preprocess_block_image(self, image: np.ndarray, block_type: str) -> np.ndarray:
        """
        Preprocess image block for optimal OCR.
        
        NOTE: Removed adaptive thresholding - PaddleOCR works better with grayscale images
        that have anti-aliasing. Binary thresholding creates jagged edges that lower confidence.
        The image should already be preprocessed by the main pipeline.
        """
        if not OPENCV_AVAILABLE:
            return image
            
        try:
            # Convert to grayscale if needed (image may already be grayscale from main pipeline)
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Light preprocessing only - main preprocessing already done in pipeline
            # Block-specific light denoise if needed
            if block_type == "handwriting":
                # Slightly more aggressive denoise for handwriting
                processed = cv2.bilateralFilter(gray, 9, 75, 75)
            elif block_type == "table":
                # Very light denoise for tables (preserve structure)
                processed = cv2.bilateralFilter(gray, 5, 50, 50)
            else:
                # Standard light denoise
                processed = cv2.bilateralFilter(gray, 5, 50, 50)
            
            # Return grayscale (NOT binary) - PaddleOCR prefers grayscale with anti-aliasing
            return processed
            
        except Exception as e:
            LOGGER.warning("Image preprocessing failed: %s", e)
            return image
    
    def _analyze_text_structure(self, text: str) -> Tuple[int, int]:
        """Analyze text structure for field and line counts."""
        if not text.strip():
            return 0, 0
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        line_count = len(lines)
        
        # Estimate field count based on common patterns
        field_count = 0
        for line in lines:
            # Look for common invoice/receipt patterns
            if any(pattern in line.lower() for pattern in ['$', 'Â£', 'â‚¬', 'total', 'subtotal', 'tax', 'vat']):
                field_count += 1
            elif any(char.isdigit() for char in line) and any(char.isalpha() for char in line):
                field_count += 1
            else:
                field_count += 1
        
        return field_count, line_count
    
    def process_block(self, full_image: np.ndarray, block_info: Dict[str, Any], 
                     preprocessing_path: Optional[str] = None,
                     force_ocr_engine: Optional[str] = None) -> OCRResult:
        """Process OCR for a single block."""
        start_time = time.time()
        
        block_type = block_info.get("type", "body")
        bbox = tuple(block_info.get("bbox", [0, 0, 0, 0]))
        
        # Extract block image
        block_image = self._extract_block_image(full_image, bbox)
        
        # Preprocess for optimal OCR
        processed_image = self._preprocess_block_image(block_image, block_type)
        
        # Determine OCR engine to use
        word_blocks = []
        psm_mode = None
        text = ""
        confidence = 0.0
        ocr_time = 0.0
        method_used = "unknown"
        
        # If force_ocr_engine is specified, use that engine only
        if force_ocr_engine == "tesseract":
            # Skip PaddleOCR, go directly to Tesseract
            LOGGER.info("[OCR_ENGINE] Forcing Tesseract for block")
            tesseract_text, tesseract_conf, tesseract_time, tesseract_psm = self._ocr_with_tesseract(processed_image, block_type)
            text = tesseract_text or ""
            confidence = tesseract_conf
            ocr_time = tesseract_time
            psm_mode = tesseract_psm
            method_used = "tesseract"
        elif force_ocr_engine == "paddleocr":
            # Use PaddleOCR only, no Tesseract fallback
            LOGGER.info("[OCR_ENGINE] Forcing PaddleOCR for block")
            if block_type == "table":
                text, confidence, ocr_time, word_blocks = self._ocr_with_paddle_detailed(processed_image, block_type)
            else:
                text, confidence, ocr_time = self._ocr_with_paddle(processed_image, block_type)
            method_used = "paddleocr"
        else:
            # Default behavior: Try PaddleOCR first, then Tesseract fallback
            if block_type == "table":
                # Use detailed OCR for tables to enable spatial clustering
                text, confidence, ocr_time, word_blocks = self._ocr_with_paddle_detailed(processed_image, block_type)
            else:
                # Use standard OCR for non-table blocks
                text, confidence, ocr_time = self._ocr_with_paddle(processed_image, block_type)
            
            method_used = "paddleocr"
            
            # Fallback to Tesseract if PaddleOCR fails or confidence is low
            if not text or confidence < 0.3:
                LOGGER.info("PaddleOCR failed or low confidence (%.3f), trying Tesseract", confidence)
                tesseract_text, tesseract_conf, tesseract_time, tesseract_psm = self._ocr_with_tesseract(processed_image, block_type)
                
                if tesseract_text and tesseract_conf > confidence:
                    text = tesseract_text
                    confidence = tesseract_conf
                    method_used = "tesseract"
                    ocr_time = tesseract_time
                    psm_mode = tesseract_psm
                    word_blocks = []  # Tesseract doesn't provide word blocks in this implementation
                elif not text:
                    # Final fallback
                    text = ""
                    confidence = 0.0
                    method_used = "fallback"
                    word_blocks = []
        
        # Analyze text structure
        field_count, line_count = self._analyze_text_structure(text)
        
        processing_time = time.time() - start_time
        
        result = OCRResult(
            type=block_type,
            bbox=bbox,
            ocr_text=text,
            confidence=confidence,
            method_used=method_used,
            processing_time=processing_time,
            field_count=field_count,
            line_count=line_count,
            word_blocks=word_blocks if word_blocks else None,
            psm_mode=psm_mode,
            preprocessing_path=preprocessing_path
        )
        
        # Log low confidence results
        if confidence < self._confidence_threshold:
            LOGGER.warning("Low confidence OCR for %s block: %.3f - %s", 
                         block_type, confidence, text[:50] + "..." if len(text) > 50 else text)
        
        return result
    
    def process_page(self, image_path: Union[str, Path], layout_blocks: List[Dict[str, Any]],
                     force_ocr_engine: Optional[str] = None, 
                    page_num: int = 1, preprocessing_path: Optional[str] = None) -> PageOCRResult:
        """Process OCR for all blocks on a page."""
        start_time = time.time()
        errors = []
        
        # Load image
        if not OPENCV_AVAILABLE:
            error_msg = "OpenCV not available, cannot load image"
            LOGGER.error(error_msg)
            return PageOCRResult(
                page_num=page_num,
                blocks=[],
                processing_time=0.0,
                method_used="error",
                confidence_avg=0.0,
                preprocessing_path=preprocessing_path,
                errors=[error_msg]
            )
        
        try:
            image = cv2.imread(str(image_path))
            if image is None:
                error_msg = f"Could not load image: {image_path}"
                LOGGER.error(error_msg)
                return PageOCRResult(
                    page_num=page_num,
                    blocks=[],
                    processing_time=0.0,
                    method_used="error",
                    confidence_avg=0.0,
                    preprocessing_path=preprocessing_path,
                    errors=[error_msg]
                )
        except Exception as e:
            error_msg = f"Error loading image {image_path}: {e}"
            LOGGER.error(error_msg)
            return PageOCRResult(
                page_num=page_num,
                blocks=[],
                processing_time=0.0,
                method_used="error",
                confidence_avg=0.0,
                preprocessing_path=preprocessing_path,
                errors=[error_msg]
            )
        
        # Process each block
        ocr_results = []
        low_confidence_count = 0
        
        for block_info in layout_blocks:
            try:
                result = self.process_block(image, block_info, preprocessing_path=preprocessing_path, force_ocr_engine=force_ocr_engine)
                ocr_results.append(result)
                
                if result.confidence < self._confidence_threshold:
                    low_confidence_count += 1
                    
            except Exception as e:
                error_msg = f"OCR processing failed for block {block_info}: {e}"
                LOGGER.error(error_msg)
                errors.append(error_msg)
                # Create error result
                error_result = OCRResult(
                    type=block_info.get("type", "body"),
                    bbox=tuple(block_info.get("bbox", [0, 0, 0, 0])),
                    ocr_text="",
                    confidence=0.0,
                    method_used="error",
                    processing_time=0.0,
                    preprocessing_path=preprocessing_path
                )
                ocr_results.append(error_result)
                low_confidence_count += 1
        
        # Calculate statistics
        processing_time = time.time() - start_time
        confidences = [r.confidence for r in ocr_results if r.confidence > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Determine primary method used
        methods = [r.method_used for r in ocr_results]
        primary_method = max(set(methods), key=methods.count) if methods else "unknown"
        
        # #region agent log
        import json
        log_path = Path(__file__).parent.parent.parent.parent / ".cursor" / "debug.log"
        total_text_length = sum(len(r.ocr_text) for r in ocr_results)
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "A", "location": "ocr_processor.py:689", "message": "OCR process_page complete", "data": {"page_num": page_num, "blocks_count": len(ocr_results), "primary_method": primary_method, "avg_confidence": avg_confidence, "total_text_length": total_text_length, "paddleocr_available": PADDLEOCR_AVAILABLE, "tesseract_available": TESSERACT_AVAILABLE}, "timestamp": int(__import__("time").time() * 1000)}) + "\n")
        except: pass
        # #endregion
        
        result = PageOCRResult(
            page_num=page_num,
            blocks=ocr_results,
            processing_time=processing_time,
            method_used=primary_method,
            confidence_avg=avg_confidence,
            low_confidence_blocks=low_confidence_count,
            preprocessing_path=preprocessing_path,
            errors=errors
        )
        
        LOGGER.info("OCR processing completed for page %d: %d blocks, %.3fs, method=%s, conf=%.3f, low_conf=%d",
                   page_num, len(ocr_results), processing_time, primary_method, avg_confidence, low_confidence_count)
        
        return result
    
    def generate_telemetry(self, page_result: PageOCRResult) -> PageTelemetry:
        """Generate telemetry report for a single page."""
        # Calculate word count from all blocks
        total_words = sum(count_words(block.ocr_text) for block in page_result.blocks)
        
        # Determine engine mix
        methods = [block.method_used for block in page_result.blocks]
        engine = determine_engine_mix(methods)
        
        # Get PSM mode if any block used Tesseract
        psm_mode = None
        for block in page_result.blocks:
            if block.psm_mode:
                psm_mode = block.psm_mode
                break
        
        return PageTelemetry(
            page_index=page_result.page_num - 1,  # Convert to 0-based index
            engine=engine,
            psm=psm_mode,
            preprocessing=page_result.preprocessing_path or "unknown",
            confidence=page_result.confidence_avg,
            word_count=total_words,
            duration_ms=page_result.processing_time * 1000.0,  # Convert to milliseconds
            errors=page_result.errors
        )
    
    def generate_block_telemetry(self, page_result: PageOCRResult) -> List[BlockTelemetry]:
        """Generate telemetry for all blocks on a page."""
        block_telemetry = []
        page_index = page_result.page_num - 1  # Convert to 0-based index
        
        for block in page_result.blocks:
            block_telemetry.append(BlockTelemetry(
                page_index=page_index,
                block_type=categorize_block_type(block.type),
                bbox=list(block.bbox),
                confidence=block.confidence,
                word_count=count_words(block.ocr_text)
            ))
        
        return block_telemetry
    
    def save_ocr_artifacts(self, result: PageOCRResult, artifact_dir: Path) -> Path:
        """Save OCR results as JSON artifact."""
        try:
            artifact_dir.mkdir(parents=True, exist_ok=True)
            json_path = artifact_dir / f"ocr_page_{result.page_num:03d}.json"
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
            
            LOGGER.info("OCR artifacts saved to: %s", json_path)
            return json_path
            
        except Exception as e:
            LOGGER.error("Failed to save OCR artifacts: %s", e)
            return Path()


# Global processor instance
_processor = None

def get_ocr_processor() -> OCRProcessor:
    """Get global OCR processor instance."""
    global _processor
    if _processor is None:
        _processor = OCRProcessor()
    return _processor


def process_document_ocr(image_path: Union[str, Path], layout_blocks: List[Dict[str, Any]], 
                        page_num: int = 1, save_artifacts: bool = True, 
                        artifact_dir: Optional[Path] = None,
                        preprocessing_path: Optional[str] = None,
                        force_ocr_engine: Optional[str] = None) -> PageOCRResult:
    """
    Main entry point for document OCR processing.
    
    Args:
        image_path: Path to preprocessed image
        layout_blocks: List of detected layout blocks
        page_num: Page number
        save_artifacts: Whether to save JSON artifacts
        artifact_dir: Directory for artifacts (defaults to OCR_ARTIFACT_ROOT)
        preprocessing_path: Preprocessing path used (e.g., "enhanced", "minimal", "dual_path_chosen")
        
    Returns:
        PageOCRResult with OCR results for all blocks
    """
    processor = get_ocr_processor()
    result = processor.process_page(image_path, layout_blocks, page_num, preprocessing_path=preprocessing_path, force_ocr_engine=force_ocr_engine)
    
    if save_artifacts:
        if artifact_dir is None:
            artifact_dir = Path(OCR_ARTIFACT_ROOT)
        processor.save_ocr_artifacts(result, artifact_dir)
    
    return result


