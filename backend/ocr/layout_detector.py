# -*- coding: utf-8 -*-
"""
Robust Layout Segmentation for Invoices and Receipts

This module provides comprehensive layout detection using LayoutParser with EfficientDet PubLayNet
as the primary solution, with OpenCV-based fallback for robust document segmentation.

Features:
- LayoutParser EfficientDet PubLayNet integration
- OpenCV fallback for whitespace-based segmentation
- Block type mapping for invoice/receipt specific regions
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
    import layoutparser as lp
    LAYOUTPARSER_AVAILABLE = True
except ImportError:
    LAYOUTPARSER_AVAILABLE = False
    lp = None

LOGGER = logging.getLogger("owlin.ocr.layout")
LOGGER.setLevel(logging.INFO)


@dataclass
class LayoutBlock:
    """Represents a detected layout block with type, coordinates, and confidence."""
    type: str
    bbox: Tuple[int, int, int, int]  # x, y, width, height
    confidence: float
    source: str  # "layoutparser" or "opencv_fallback"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type,
            "bbox": list(self.bbox),
            "confidence": self.confidence,
            "source": self.source
        }


@dataclass
class LayoutResult:
    """Complete layout detection result for a page."""
    page_num: int
    blocks: List[LayoutBlock]
    processing_time: float
    method_used: str
    confidence_avg: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "page_num": self.page_num,
            "blocks": [block.to_dict() for block in self.blocks],
            "processing_time": self.processing_time,
            "method_used": self.method_used,
            "confidence_avg": self.confidence_avg
        }


class LayoutDetector:
    """Robust layout detector with multiple fallback strategies."""
    
    def __init__(self):
        self._layout_model = None
        self._fallback_enabled = True
        self._block_type_mapping = {
            # PubLayNet to invoice-specific mapping
            "Text": "header",  # Default for text blocks
            "Title": "header",
            "List": "table",
            "Table": "table", 
            "Figure": "footer",  # Often contains totals/signatures
            "Caption": "footer"
        }
    
    def _load_layoutparser_model(self) -> Optional[Any]:
        """Load LayoutParser EfficientDet PubLayNet model with fallbacks."""
        if self._layout_model is not None:
            return self._layout_model
            
        if not LAYOUTPARSER_AVAILABLE:
            LOGGER.warning("LayoutParser not available, will use OpenCV fallback")
            return None
            
        try:
            # Primary: EfficientDet PubLayNet
            LOGGER.info("Loading LayoutParser EfficientDet PubLayNet model...")
            self._layout_model = lp.AutoLayoutModel("lp://EfficientDet/PubLayNet")
            LOGGER.info("LayoutParser EfficientDet PubLayNet model loaded successfully")
            return self._layout_model
            
        except Exception as e:
            LOGGER.warning("Failed to load EfficientDet PubLayNet: %s", e)
            
            try:
                # Fallback 1: Try other LayoutParser models
                LOGGER.info("Trying LayoutParser fallback models...")
                self._layout_model = lp.AutoLayoutModel("lp://PubLayNet/faster_rcnn_R_50_FPN_3x")
                LOGGER.info("LayoutParser fallback model loaded successfully")
                return self._layout_model
                
            except Exception as e2:
                LOGGER.warning("All LayoutParser models failed: %s", e2)
                self._layout_model = None
                return None
    
    def _detect_with_layoutparser(self, image: np.ndarray) -> List[LayoutBlock]:
        """Detect layout using LayoutParser EfficientDet PubLayNet."""
        model = self._load_layoutparser_model()
        if model is None:
            return []
            
        try:
            # Run layout detection
            layout = model.detect(image)
            
            blocks = []
            for element in layout:
                # Extract coordinates and type
                x1, y1, x2, y2 = element.block.coordinates
                block_type = str(element.type)
                confidence = float(element.score) if hasattr(element, 'score') else 0.8
                
                # Map to invoice-specific types
                mapped_type = self._block_type_mapping.get(block_type, "body")
                
                # Convert to our format (x, y, width, height)
                bbox = (int(x1), int(y1), int(x2 - x1), int(y2 - y1))
                
                block = LayoutBlock(
                    type=mapped_type,
                    bbox=bbox,
                    confidence=confidence,
                    source="layoutparser"
                )
                blocks.append(block)
                
            LOGGER.info("LayoutParser detected %d blocks", len(blocks))
            return blocks
            
        except Exception as e:
            LOGGER.error("LayoutParser detection failed: %s", e)
            return []
    
    def _detect_with_opencv_fallback(self, image: np.ndarray) -> List[LayoutBlock]:
        """Fallback layout detection using OpenCV whitespace analysis."""
        if not OPENCV_AVAILABLE:
            LOGGER.error("OpenCV not available for fallback detection")
            return []
            
        try:
            LOGGER.info("Using OpenCV fallback for layout detection")
            
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            h, w = gray.shape
            blocks = []
            
            # Method 1: Horizontal line detection for table rows
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (w//4, 1))
            horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel)
            
            # Method 2: Vertical line detection for table columns  
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, h//4))
            vertical_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel)
            
            # Method 3: Contour-based region detection
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Analyze horizontal lines for table regions
            table_regions = self._find_table_regions(horizontal_lines, w, h)
            for region in table_regions:
                blocks.append(LayoutBlock(
                    type="table",
                    bbox=region,
                    confidence=0.7,
                    source="opencv_fallback"
                ))
            
            # Analyze contours for other regions
            other_regions = self._find_other_regions(contours, w, h, table_regions)
            for region_type, region in other_regions:
                blocks.append(LayoutBlock(
                    type=region_type,
                    bbox=region,
                    confidence=0.6,
                    source="opencv_fallback"
                ))
            
            # Ensure we have at least header, body, footer
            if not blocks:
                # Fallback: split page into thirds
                blocks = [
                    LayoutBlock(type="header", bbox=(0, 0, w, h//3), confidence=0.5, source="opencv_fallback"),
                    LayoutBlock(type="body", bbox=(0, h//3, w, h//3), confidence=0.5, source="opencv_fallback"),
                    LayoutBlock(type="footer", bbox=(0, 2*h//3, w, h//3), confidence=0.5, source="opencv_fallback")
                ]
            
            LOGGER.info("OpenCV fallback detected %d blocks", len(blocks))
            return blocks
            
        except Exception as e:
            LOGGER.error("OpenCV fallback detection failed: %s", e)
            return []
    
    def _find_table_regions(self, horizontal_lines: np.ndarray, w: int, h: int) -> List[Tuple[int, int, int, int]]:
        """Find table regions based on horizontal line density."""
        regions = []
        
        # Find horizontal line positions
        line_positions = []
        for y in range(h):
            if np.sum(horizontal_lines[y, :]) > w * 0.1:  # Significant horizontal line
                line_positions.append(y)
        
        # Group consecutive lines into table regions
        if len(line_positions) >= 3:  # Need at least 3 lines for a table
            start_y = line_positions[0]
            end_y = line_positions[-1]
            regions.append((0, start_y, w, end_y - start_y))
        
        return regions
    
    def _find_other_regions(self, contours: List, w: int, h: int, table_regions: List) -> List[Tuple[str, Tuple[int, int, int, int]]]:
        """Find other regions (header, footer) based on contour analysis."""
        regions = []
        
        # Find large contours that aren't table regions
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > w * h * 0.05:  # Significant region
                x, y, cw, ch = cv2.boundingRect(contour)
                
                # Classify based on position
                if y < h * 0.3:
                    region_type = "header"
                elif y > h * 0.7:
                    region_type = "footer"
                else:
                    region_type = "body"
                
                # Check if overlaps with table regions
                overlaps = False
                for tx, ty, tw, th in table_regions:
                    if not (x + cw < tx or x > tx + tw or y + ch < ty or y > ty + th):
                        overlaps = True
                        break
                
                if not overlaps:
                    regions.append((region_type, (x, y, cw, ch)))
        
        return regions
    
    def detect_layout(self, image_path: Union[str, Path], page_num: int = 1) -> LayoutResult:
        """
        Detect layout for a single page image with comprehensive fallback strategy.
        
        Args:
            image_path: Path to the preprocessed image
            page_num: Page number for result tracking
            
        Returns:
            LayoutResult with detected blocks and metadata
        """
        start_time = time.time()
        image_path = Path(image_path)
        
        if not image_path.exists():
            LOGGER.error("Image file not found: %s", image_path)
            return LayoutResult(
                page_num=page_num,
                blocks=[],
                processing_time=0.0,
                method_used="error",
                confidence_avg=0.0
            )
        
        # Load image
        if not OPENCV_AVAILABLE:
            LOGGER.error("OpenCV not available, cannot load image")
            return LayoutResult(
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
                return LayoutResult(
                    page_num=page_num,
                    blocks=[],
                    processing_time=0.0,
                    method_used="error",
                    confidence_avg=0.0
                )
        except Exception as e:
            LOGGER.error("Error loading image %s: %s", image_path, e)
            return LayoutResult(
                page_num=page_num,
                blocks=[],
                processing_time=0.0,
                method_used="error",
                confidence_avg=0.0
            )
        
        # Try LayoutParser first if enabled
        blocks = []
        method_used = "error"
        
        if FEATURE_OCR_V2_LAYOUT and LAYOUTPARSER_AVAILABLE:
            LOGGER.info("Attempting LayoutParser detection for page %d", page_num)
            blocks = self._detect_with_layoutparser(image)
            if blocks:
                method_used = "layoutparser"
                LOGGER.info("LayoutParser detection successful: %d blocks", len(blocks))
            else:
                LOGGER.warning("LayoutParser detection failed, trying OpenCV fallback")
        
        # Fallback to OpenCV if LayoutParser failed or disabled
        if not blocks and self._fallback_enabled:
            LOGGER.info("Using OpenCV fallback for page %d", page_num)
            blocks = self._detect_with_opencv_fallback(image)
            if blocks:
                method_used = "opencv_fallback"
                LOGGER.info("OpenCV fallback successful: %d blocks", len(blocks))
        
        # Final fallback: single block
        if not blocks:
            LOGGER.warning("All detection methods failed, using single block fallback")
            h, w = image.shape[:2]
            blocks = [LayoutBlock(
                type="body",
                bbox=(0, 0, w, h),
                confidence=0.3,
                source="fallback"
            )]
            method_used = "fallback"
        
        # Calculate average confidence
        confidence_avg = sum(block.confidence for block in blocks) / len(blocks) if blocks else 0.0
        
        processing_time = time.time() - start_time
        
        result = LayoutResult(
            page_num=page_num,
            blocks=blocks,
            processing_time=processing_time,
            method_used=method_used,
            confidence_avg=confidence_avg
        )
        
        LOGGER.info("Layout detection completed for page %d: %d blocks, %.3fs, method=%s, conf=%.3f",
                   page_num, len(blocks), processing_time, method_used, confidence_avg)
        
        return result
    
    def save_layout_artifacts(self, result: LayoutResult, artifact_dir: Path) -> Path:
        """Save layout detection results as JSON artifact."""
        try:
            artifact_dir.mkdir(parents=True, exist_ok=True)
            json_path = artifact_dir / f"layout_page_{result.page_num:03d}.json"
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
            
            LOGGER.info("Layout artifacts saved to: %s", json_path)
            return json_path
            
        except Exception as e:
            LOGGER.error("Failed to save layout artifacts: %s", e)
            return Path()


# Global detector instance
_detector = None

def get_layout_detector() -> LayoutDetector:
    """Get global layout detector instance."""
    global _detector
    if _detector is None:
        _detector = LayoutDetector()
    return _detector


def detect_document_layout(image_path: Union[str, Path], page_num: int = 1, 
                          save_artifacts: bool = True, artifact_dir: Optional[Path] = None) -> LayoutResult:
    """
    Main entry point for layout detection with artifact storage.
    
    Args:
        image_path: Path to preprocessed image
        page_num: Page number
        save_artifacts: Whether to save JSON artifacts
        artifact_dir: Directory for artifacts (defaults to OCR_ARTIFACT_ROOT)
        
    Returns:
        LayoutResult with detected blocks
    """
    detector = get_layout_detector()
    result = detector.detect_layout(image_path, page_num)
    
    if save_artifacts:
        if artifact_dir is None:
            artifact_dir = Path(OCR_ARTIFACT_ROOT)
        detector.save_layout_artifacts(result, artifact_dir)
    
    return result


