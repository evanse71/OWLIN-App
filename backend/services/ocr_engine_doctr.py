# -*- coding: utf-8 -*-
"""
docTR OCR Engine Integration

This module provides docTR (Document Text Recognition) integration for table-dense
and multi-column document OCR processing, as specified in the System Bible Section 2.4.

docTR is triggered when layout_score > 0.6 (table-dense or multi-column layouts).
"""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional, Tuple
import time
import numpy as np

# Optional import with graceful fallback
try:
    from doctr.io import DocumentFile
    from doctr.models import ocr_predictor
    DOCTR_AVAILABLE = True
except ImportError:
    DOCTR_AVAILABLE = False
    DocumentFile = None
    ocr_predictor = None

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    cv2 = None

LOGGER = logging.getLogger("owlin.ocr.doctr")
LOGGER.setLevel(logging.INFO)


class DocTREngine:
    """docTR OCR engine for table-dense and multi-column documents."""
    
    def __init__(self):
        self._model = None
        self._initialized = False
    
    def _load_model(self) -> bool:
        """Load docTR OCR model (lazy initialization)."""
        if self._model is not None:
            return True
        
        if not DOCTR_AVAILABLE:
            LOGGER.warning("docTR not available. Install with: pip install python-doctr")
            return False
        
        try:
            LOGGER.info("Loading docTR OCR model...")
            # Use db_resnet50 for document recognition
            self._model = ocr_predictor(pretrained=True)
            self._initialized = True
            LOGGER.info("docTR model loaded successfully")
            return True
        except Exception as e:
            LOGGER.error("Failed to load docTR model: %s", e)
            self._model = None
            self._initialized = False
            return False
    
    def is_available(self) -> bool:
        """Check if docTR is available and initialized."""
        if not DOCTR_AVAILABLE:
            return False
        return self._load_model()
    
    def process_page(self, image: np.ndarray, config: Optional[Dict[str, Any]] = None) -> Tuple[str, float, Dict[str, Any]]:
        """
        Process a single page/image with docTR OCR.
        
        Args:
            image: Input image as numpy array (BGR format from OpenCV)
            config: Optional configuration dict (not used by docTR, kept for API compatibility)
        
        Returns:
            Tuple of (text, confidence, metadata)
            - text: Extracted text from the page
            - confidence: Average confidence score (0.0-1.0)
            - metadata: Additional information (word boxes, line boxes, etc.)
        """
        if not self.is_available():
            return ("", 0.0, {})
        
        if not OPENCV_AVAILABLE or image is None:
            return ("", 0.0, {})
        
        try:
            start_time = time.time()
            
            # Convert BGR to RGB (docTR expects RGB)
            if len(image.shape) == 3 and image.shape[2] == 3:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                image_rgb = image
            
            # Create DocumentFile from numpy array
            # docTR can work with numpy arrays directly
            doc = DocumentFile.from_images([image_rgb])
            
            # Run OCR prediction
            result = self._model(doc)
            
            # Extract text and confidence from result
            text_parts = []
            confidences = []
            word_boxes = []
            line_boxes = []
            
            # Parse docTR result structure
            # Result structure: result.pages[0].blocks -> lines -> words
            if result and len(result.pages) > 0:
                page = result.pages[0]
                
                for block in page.blocks:
                    for line in block.lines:
                        line_text_parts = []
                        line_confs = []
                        
                        for word in line.words:
                            word_text = word.value
                            word_conf = word.confidence if hasattr(word, 'confidence') else 0.8
                            
                            line_text_parts.append(word_text)
                            line_confs.append(word_conf)
                            
                            # Store word box coordinates
                            if hasattr(word, 'geometry'):
                                word_boxes.append({
                                    "text": word_text,
                                    "confidence": word_conf,
                                    "bbox": self._extract_bbox(word.geometry) if hasattr(word, 'geometry') else None
                                })
                        
                        line_text = " ".join(line_text_parts)
                        if line_text:
                            text_parts.append(line_text)
                            if line_confs:
                                confidences.extend(line_confs)
                            
                            # Store line box coordinates
                            if hasattr(line, 'geometry'):
                                line_boxes.append({
                                    "text": line_text,
                                    "bbox": self._extract_bbox(line.geometry) if hasattr(line, 'geometry') else None
                                })
            
            # Combine all text
            full_text = "\n".join(text_parts)
            
            # Calculate average confidence
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            processing_time = time.time() - start_time
            
            metadata = {
                "engine": "doctr",
                "processing_time": processing_time,
                "word_count": len(word_boxes),
                "line_count": len(line_boxes),
                "word_boxes": word_boxes[:100],  # Limit to first 100 for storage
                "line_boxes": line_boxes[:50],   # Limit to first 50 for storage
                "model": "db_resnet50"
            }
            
            LOGGER.debug("docTR processed page: %d words, %.3f confidence, %.3fs", 
                        len(word_boxes), avg_confidence, processing_time)
            
            return (full_text, avg_confidence, metadata)
            
        except Exception as e:
            LOGGER.error("docTR processing failed: %s", e)
            return ("", 0.0, {"error": str(e)})
    
    def _extract_bbox(self, geometry) -> Optional[List[float]]:
        """Extract bounding box coordinates from docTR geometry object."""
        try:
            if hasattr(geometry, 'bbox'):
                bbox = geometry.bbox
                if hasattr(bbox, 'xmin') and hasattr(bbox, 'ymin') and hasattr(bbox, 'xmax') and hasattr(bbox, 'ymax'):
                    return [float(bbox.xmin), float(bbox.ymin), float(bbox.xmax), float(bbox.ymax)]
            elif isinstance(geometry, (list, tuple)) and len(geometry) >= 4:
                return [float(x) for x in geometry[:4]]
        except Exception:
            pass
        return None
    
    def process_blocks(self, image: np.ndarray, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process multiple blocks from a page (for table-dense layouts).
        
        Args:
            image: Full page image
            blocks: List of block dictionaries with 'bbox' and 'type' keys
        
        Returns:
            List of OCR results for each block
        """
        results = []
        
        if not self.is_available():
            return results
        
        for block in blocks:
            bbox = block.get("bbox", [0, 0, 0, 0])
            block_type = block.get("type", "body")
            
            # Extract block image
            x1, y1, x2, y2 = map(int, bbox)
            block_image = image[y1:y2, x1:x2]
            
            if block_image.size == 0:
                results.append({
                    "type": block_type,
                    "bbox": bbox,
                    "text": "",
                    "confidence": 0.0,
                    "method": "doctr"
                })
                continue
            
            # Process block
            text, confidence, metadata = self.process_page(block_image)
            
            results.append({
                "type": block_type,
                "bbox": bbox,
                "text": text,
                "confidence": confidence,
                "method": "doctr",
                "metadata": metadata
            })
        
        return results


# Singleton instance
_doctr_engine: Optional[DocTREngine] = None


def get_doctr_engine() -> DocTREngine:
    """Get or create singleton docTR engine instance."""
    global _doctr_engine
    if _doctr_engine is None:
        _doctr_engine = DocTREngine()
    return _doctr_engine


def is_doctr_available() -> bool:
    """Check if docTR is available."""
    return get_doctr_engine().is_available()

