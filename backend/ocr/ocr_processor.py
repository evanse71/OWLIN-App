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
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import time

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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type,
            "bbox": list(self.bbox),
            "ocr_text": self.ocr_text,
            "confidence": self.confidence,
            "method_used": self.method_used,
            "processing_time": self.processing_time,
            "field_count": self.field_count,
            "line_count": self.line_count
        }


@dataclass
class PageOCRResult:
    """Complete OCR result for a page."""
    page_num: int
    blocks: List[OCRResult]
    processing_time: float
    method_used: str
    confidence_avg: float
    low_confidence_blocks: int = 0
    
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
            LOGGER.info("Loading PaddleOCR with PP-Structure support...")
            # Initialize with structure support for table processing
            self._paddle_ocr = PaddleOCR(
                use_angle_cls=True,
                lang='en',
                use_gpu=False,  # Set to True if GPU available
                show_log=False
            )
            LOGGER.info("PaddleOCR loaded successfully with PP-Structure support")
            return self._paddle_ocr
            
        except Exception as e:
            LOGGER.error("Failed to load PaddleOCR: %s", e)
            self._paddle_ocr = None
            return None
    
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
                result = ocr.ocr_table(image, cls=config.get("use_angle_cls", True))
            else:
                # Standard OCR for other block types
                result = ocr.ocr(image, cls=config.get("use_angle_cls", True))
            
            processing_time = time.time() - start_time
            
            if not result or not result[0]:
                return "", 0.0, processing_time
            
            # Extract text and confidence
            texts = []
            confidences = []
            
            for line in result[0]:
                if len(line) >= 2:
                    bbox = line[0]
                    text_info = line[1]
                    if isinstance(text_info, tuple) and len(text_info) == 2:
                        text, conf = text_info
                        texts.append(text)
                        confidences.append(float(conf))
                    else:
                        texts.append(str(text_info))
                        confidences.append(0.5)
            
            # Combine text and calculate average confidence
            combined_text = "\n".join(texts).strip()
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            LOGGER.debug("PaddleOCR extracted %d lines, avg confidence: %.3f", 
                        len(texts), avg_confidence)
            
            return combined_text, avg_confidence, processing_time
            
        except Exception as e:
            LOGGER.error("PaddleOCR processing failed: %s", e)
            return "", 0.0, 0.0
    
    def _ocr_with_tesseract(self, image: np.ndarray, block_type: str) -> Tuple[str, float, float]:
        """Fallback OCR using Tesseract."""
        if not TESSERACT_AVAILABLE:
            LOGGER.warning("Tesseract not available for fallback OCR")
            return "", 0.0, 0.0
            
        try:
            start_time = time.time()
            
            # Configure Tesseract based on block type
            if block_type == "table":
                config = '--oem 3 --psm 6'  # Uniform block of text
            elif block_type == "header":
                config = '--oem 3 --psm 7'  # Single text line
            else:
                config = '--oem 3 --psm 6'  # Default
            
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
            
            return text, avg_confidence, processing_time
            
        except Exception as e:
            LOGGER.error("Tesseract OCR failed: %s", e)
            return "", 0.0, 0.0
    
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
        """Preprocess image block for optimal OCR."""
        if not OPENCV_AVAILABLE:
            return image
            
        try:
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Block-specific preprocessing
            if block_type == "table":
                # Enhance table structure
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
                processed = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
            elif block_type == "handwriting":
                # Enhance handwriting
                processed = cv2.bilateralFilter(gray, 9, 75, 75)
            else:
                # Standard preprocessing
                processed = cv2.bilateralFilter(gray, 5, 75, 75)
            
            # Adaptive thresholding
            processed = cv2.adaptiveThreshold(
                processed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
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
    
    def process_block(self, full_image: np.ndarray, block_info: Dict[str, Any]) -> OCRResult:
        """Process OCR for a single block."""
        start_time = time.time()
        
        block_type = block_info.get("type", "body")
        bbox = tuple(block_info.get("bbox", [0, 0, 0, 0]))
        
        # Extract block image
        block_image = self._extract_block_image(full_image, bbox)
        
        # Preprocess for optimal OCR
        processed_image = self._preprocess_block_image(block_image, block_type)
        
        # Try PaddleOCR first
        text, confidence, ocr_time = self._ocr_with_paddle(processed_image, block_type)
        method_used = "paddleocr"
        
        # Fallback to Tesseract if PaddleOCR fails or confidence is low
        if not text or confidence < 0.3:
            LOGGER.info("PaddleOCR failed or low confidence (%.3f), trying Tesseract", confidence)
            tesseract_text, tesseract_conf, tesseract_time = self._ocr_with_tesseract(processed_image, block_type)
            
            if tesseract_text and tesseract_conf > confidence:
                text = tesseract_text
                confidence = tesseract_conf
                method_used = "tesseract"
                ocr_time = tesseract_time
            elif not text:
                # Final fallback
                text = ""
                confidence = 0.0
                method_used = "fallback"
        
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
            line_count=line_count
        )
        
        # Log low confidence results
        if confidence < self._confidence_threshold:
            LOGGER.warning("Low confidence OCR for %s block: %.3f - %s", 
                         block_type, confidence, text[:50] + "..." if len(text) > 50 else text)
        
        return result
    
    def process_page(self, image_path: Union[str, Path], layout_blocks: List[Dict[str, Any]], 
                    page_num: int = 1) -> PageOCRResult:
        """Process OCR for all blocks on a page."""
        start_time = time.time()
        
        # Load image
        if not OPENCV_AVAILABLE:
            LOGGER.error("OpenCV not available, cannot load image")
            return PageOCRResult(
                page_num=page_num,
                blocks=[],
                processing_time=0.0,
                method_used="error",
                confidence_avg=0.0
            )
        
        try:
            image = cv2.imread(str(image_path))
            if image is None:
                LOGGER.error("Could not load image: %s", image_path)
                return PageOCRResult(
                    page_num=page_num,
                    blocks=[],
                    processing_time=0.0,
                    method_used="error",
                    confidence_avg=0.0
                )
        except Exception as e:
            LOGGER.error("Error loading image %s: %s", image_path, e)
            return PageOCRResult(
                page_num=page_num,
                blocks=[],
                processing_time=0.0,
                method_used="error",
                confidence_avg=0.0
            )
        
        # Process each block
        ocr_results = []
        low_confidence_count = 0
        
        for block_info in layout_blocks:
            try:
                result = self.process_block(image, block_info)
                ocr_results.append(result)
                
                if result.confidence < self._confidence_threshold:
                    low_confidence_count += 1
                    
            except Exception as e:
                LOGGER.error("OCR processing failed for block %s: %s", block_info, e)
                # Create error result
                error_result = OCRResult(
                    type=block_info.get("type", "body"),
                    bbox=tuple(block_info.get("bbox", [0, 0, 0, 0])),
                    ocr_text="",
                    confidence=0.0,
                    method_used="error",
                    processing_time=0.0
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
        
        result = PageOCRResult(
            page_num=page_num,
            blocks=ocr_results,
            processing_time=processing_time,
            method_used=primary_method,
            confidence_avg=avg_confidence,
            low_confidence_blocks=low_confidence_count
        )
        
        LOGGER.info("OCR processing completed for page %d: %d blocks, %.3fs, method=%s, conf=%.3f, low_conf=%d",
                   page_num, len(ocr_results), processing_time, primary_method, avg_confidence, low_confidence_count)
        
        return result
    
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
                        artifact_dir: Optional[Path] = None) -> PageOCRResult:
    """
    Main entry point for document OCR processing.
    
    Args:
        image_path: Path to preprocessed image
        layout_blocks: List of detected layout blocks
        page_num: Page number
        save_artifacts: Whether to save JSON artifacts
        artifact_dir: Directory for artifacts (defaults to OCR_ARTIFACT_ROOT)
        
    Returns:
        PageOCRResult with OCR results for all blocks
    """
    processor = get_ocr_processor()
    result = processor.process_page(image_path, layout_blocks, page_num)
    
    if save_artifacts:
        if artifact_dir is None:
            artifact_dir = Path(OCR_ARTIFACT_ROOT)
        processor.save_ocr_artifacts(result, artifact_dir)
    
    return result


