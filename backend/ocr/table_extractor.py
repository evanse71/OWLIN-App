# -*- coding: utf-8 -*-
"""
Structure-Aware Table Extraction Module

This module provides comprehensive table extraction capabilities for invoices and receipts,
including cell detection, OCR processing, and line-item parsing.

Features:
- OpenCV-based table structure detection (lines, contours)
- Cell segmentation and individual OCR processing
- Line-item parsing for invoices and receipts
- Fallback heuristics for broken/merged tables
- JSON artifact storage for downstream processing
- Comprehensive error handling and logging
"""

from __future__ import annotations
import json
import logging
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import time

# Import configuration
from backend.config import OCR_ARTIFACT_ROOT

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

LOGGER = logging.getLogger("owlin.ocr.table")
LOGGER.setLevel(logging.INFO)


@dataclass
class LineItem:
    """Represents a single line item from a table."""
    description: str
    quantity: str
    unit_price: str
    total_price: str
    vat: str
    confidence: float
    row_index: int
    cell_data: Dict[str, str]  # Raw cell data for debugging
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "description": self.description,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "total_price": self.total_price,
            "vat": self.vat,
            "confidence": self.confidence,
            "row_index": self.row_index,
            "cell_data": self.cell_data
        }


@dataclass
class TableResult:
    """Complete table extraction result."""
    type: str
    bbox: Tuple[int, int, int, int]
    line_items: List[LineItem]
    confidence: float
    method_used: str
    processing_time: float
    fallback_used: bool
    cell_count: int
    row_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type,
            "bbox": list(self.bbox),
            "line_items": [item.to_dict() for item in self.line_items],
            "confidence": self.confidence,
            "method_used": self.method_used,
            "processing_time": self.processing_time,
            "fallback_used": self.fallback_used,
            "cell_count": self.cell_count,
            "row_count": self.row_count
        }


class TableExtractor:
    """Structure-aware table extraction with comprehensive fallbacks."""
    
    def __init__(self):
        self._paddle_ocr = None
        self._confidence_threshold = 0.7
        self._min_cell_size = (20, 20)  # Minimum cell dimensions
        self._line_threshold = 50  # Minimum line length for table detection
        
        # Common patterns for invoice/receipt parsing
        self._price_patterns = [
            r'\$[\d,]+\.?\d*',  # $123.45
            r'Â£[\d,]+\.?\d*',   # Â£123.45
            r'â‚¬[\d,]+\.?\d*',   # â‚¬123.45
            r'[\d,]+\.?\d*',    # 123.45
        ]
        
        self._quantity_patterns = [
            r'\d+\.?\d*',       # 123 or 123.45
            r'\d+x',            # 123x
            r'\d+\s*units?',   # 123 units
        ]
    
    def _load_paddle_ocr(self) -> Optional[PaddleOCR]:
        """Load PaddleOCR for cell-level OCR processing."""
        if self._paddle_ocr is not None:
            return self._paddle_ocr
            
        if not PADDLEOCR_AVAILABLE:
            LOGGER.warning("PaddleOCR not available for table extraction")
            return None
            
        try:
            LOGGER.info("Loading PaddleOCR for table extraction...")
            self._paddle_ocr = PaddleOCR(
                use_angle_cls=True,
                lang='en',
                use_gpu=False,
                show_log=False
            )
            LOGGER.info("PaddleOCR loaded successfully for table extraction")
            return self._paddle_ocr
            
        except Exception as e:
            LOGGER.error("Failed to load PaddleOCR for table extraction: %s", e)
            self._paddle_ocr = None
            return None
    
    def _detect_table_structure(self, image: np.ndarray) -> Tuple[List[Tuple[int, int, int, int]], bool]:
        """Detect table structure using OpenCV line detection."""
        if not OPENCV_AVAILABLE:
            return [], False
            
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            
            # Detect horizontal lines
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (gray.shape[1]//4, 1))
            horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel)
            
            # Detect vertical lines
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, gray.shape[0]//4))
            vertical_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel)
            
            # Combine lines
            table_mask = cv2.addWeighted(horizontal_lines, 0.5, vertical_lines, 0.5, 0.0)
            
            # Find contours (potential cells)
            contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter contours by size and shape
            cells = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if w > self._min_cell_size[0] and h > self._min_cell_size[1]:
                    # Check if it's roughly rectangular (table cell)
                    area = cv2.contourArea(contour)
                    rect_area = w * h
                    if area / rect_area > 0.7:  # 70% filled
                        cells.append((x, y, w, h))
            
            # Sort cells by position (top to bottom, left to right)
            cells.sort(key=lambda cell: (cell[1], cell[0]))
            
            LOGGER.info("Detected %d potential table cells", len(cells))
            return cells, True
            
        except Exception as e:
            LOGGER.error("Table structure detection failed: %s", e)
            return [], False
    
    def _extract_cell_text(self, image: np.ndarray, cell_bbox: Tuple[int, int, int, int]) -> Tuple[str, float]:
        """Extract text from a single table cell."""
        x, y, w, h = cell_bbox
        
        # Extract cell region
        cell_img = image[y:y+h, x:x+w]
        
        if cell_img.size == 0:
            return "", 0.0
        
        # Try PaddleOCR first
        ocr = self._load_paddle_ocr()
        if ocr is not None:
            try:
                result = ocr.ocr(cell_img, cls=True)
                if result and result[0]:
                    texts = []
                    confidences = []
                    for line in result[0]:
                        if len(line) >= 2:
                            text_info = line[1]
                            if isinstance(text_info, tuple) and len(text_info) == 2:
                                text, conf = text_info
                                texts.append(text)
                                confidences.append(float(conf))
                            else:
                                texts.append(str(text_info))
                                confidences.append(0.5)
                    
                    combined_text = " ".join(texts).strip()
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
                    return combined_text, avg_confidence
            except Exception as e:
                LOGGER.debug("PaddleOCR failed for cell: %s", e)
        
        # Fallback to Tesseract
        if TESSERACT_AVAILABLE:
            try:
                text = pytesseract.image_to_string(cell_img, config='--oem 3 --psm 8').strip()
                # Get confidence data
                data = pytesseract.image_to_data(cell_img, config='--oem 3 --psm 8', output_type=pytesseract.Output.DICT)
                confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.5
                return text, confidence
            except Exception as e:
                LOGGER.debug("Tesseract failed for cell: %s", e)
        
        return "", 0.0
    
    def _group_cells_into_rows(self, cells: List[Tuple[int, int, int, int]], 
                              cell_texts: List[str]) -> List[List[Tuple[int, int, int, int, str]]]:
        """Group cells into table rows based on their vertical positions."""
        if not cells:
            return []
        
        # Sort cells by y-coordinate (top to bottom)
        sorted_cells = sorted(zip(cells, cell_texts), key=lambda x: x[0][1])
        
        rows = []
        current_row = []
        current_y = sorted_cells[0][0][1]
        row_tolerance = 20  # Pixels tolerance for same row
        
        for (x, y, w, h), text in sorted_cells:
            if abs(y - current_y) <= row_tolerance:
                # Same row
                current_row.append((x, y, w, h, text))
            else:
                # New row
                if current_row:
                    # Sort current row by x-coordinate (left to right)
                    current_row.sort(key=lambda cell: cell[0])
                    rows.append(current_row)
                current_row = [(x, y, w, h, text)]
                current_y = y
        
        # Add the last row
        if current_row:
            current_row.sort(key=lambda cell: cell[0])
            rows.append(current_row)
        
        return rows
    
    def _parse_line_item(self, row_cells: List[Tuple[int, int, int, int, str]], 
                        row_index: int) -> LineItem:
        """Parse a row of cells into a line item."""
        # Initialize with empty values
        description = ""
        quantity = ""
        unit_price = ""
        total_price = ""
        vat = ""
        confidence = 0.0
        cell_data = {}
        
        # Extract text from each cell
        for i, (x, y, w, h, text) in enumerate(row_cells):
            cell_data[f"cell_{i}"] = text
            if not text.strip():
                continue
            
            # Try to identify cell content based on position and content
            if i == 0 or "description" in text.lower() or "item" in text.lower():
                description = text.strip()
            elif any(re.search(pattern, text) for pattern in self._quantity_patterns):
                quantity = text.strip()
            elif any(re.search(pattern, text) for pattern in self._price_patterns):
                if not unit_price:
                    unit_price = text.strip()
                else:
                    total_price = text.strip()
            elif "vat" in text.lower() or "tax" in text.lower():
                vat = text.strip()
            else:
                # Default to description if not identified
                if not description:
                    description = text.strip()
        
        # Calculate confidence based on how many fields we found
        found_fields = sum(1 for field in [description, quantity, unit_price, total_price] if field)
        confidence = found_fields / 4.0 if found_fields > 0 else 0.0
        
        return LineItem(
            description=description,
            quantity=quantity,
            unit_price=unit_price,
            total_price=total_price,
            vat=vat,
            confidence=confidence,
            row_index=row_index,
            cell_data=cell_data
        )
    
    def _fallback_line_grouping(self, image: np.ndarray, ocr_text: str) -> List[LineItem]:
        """Fallback method using OCR text grouping when table structure detection fails."""
        LOGGER.info("Using fallback line grouping for table extraction")
        
        lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]
        line_items = []
        
        for i, line in enumerate(lines):
            # Skip header lines
            if any(keyword in line.lower() for keyword in ['item', 'description', 'quantity', 'price', 'total']):
                continue
            
            # Try to extract structured data from line
            words = line.split()
            description = ""
            quantity = ""
            unit_price = ""
            total_price = ""
            
            # Look for price patterns
            prices = []
            for word in words:
                if any(re.search(pattern, word) for pattern in self._price_patterns):
                    prices.append(word)
            
            # Look for quantity patterns
            quantities = []
            for word in words:
                if any(re.search(pattern, word) for pattern in self._quantity_patterns):
                    quantities.append(word)
            
            # Assign values based on patterns found
            if prices:
                if len(prices) >= 2:
                    unit_price = prices[0]
                    total_price = prices[-1]
                else:
                    total_price = prices[0]
            
            if quantities:
                quantity = quantities[0]
            
            # Everything else is description
            non_price_words = [word for word in words if not any(re.search(pattern, word) for pattern in self._price_patterns + self._quantity_patterns)]
            description = " ".join(non_price_words)
            
            # Calculate confidence
            found_fields = sum(1 for field in [description, quantity, unit_price, total_price] if field)
            confidence = found_fields / 4.0 if found_fields > 0 else 0.0
            
            line_item = LineItem(
                description=description,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price,
                vat="",
                confidence=confidence,
                row_index=i,
                cell_data={"raw_line": line}
            )
            
            line_items.append(line_item)
        
        return line_items
    
    def extract_table(self, image: np.ndarray, bbox: Tuple[int, int, int, int], 
                     ocr_text: str = "") -> TableResult:
        """Extract table structure and line items from a table block."""
        start_time = time.time()
        
        x, y, w, h = bbox
        table_img = image[y:y+h, x:x+w]
        
        if table_img.size == 0:
            LOGGER.warning("Empty table image provided")
            return TableResult(
                type="table",
                bbox=bbox,
                line_items=[],
                confidence=0.0,
                method_used="error",
                processing_time=0.0,
                fallback_used=True,
                cell_count=0,
                row_count=0
            )
        
        try:
            # Try structure-aware extraction first
            cells, structure_detected = self._detect_table_structure(table_img)
            
            if structure_detected and cells:
                LOGGER.info("Using structure-aware table extraction")
                
                # Extract text from each cell
                cell_texts = []
                for cell_bbox in cells:
                    text, confidence = self._extract_cell_text(table_img, cell_bbox)
                    cell_texts.append(text)
                
                # Group cells into rows
                rows = self._group_cells_into_rows(cells, cell_texts)
                
                # Parse each row into line items
                line_items = []
                for i, row_cells in enumerate(rows):
                    if len(row_cells) > 0:  # Skip empty rows
                        line_item = self._parse_line_item(row_cells, i)
                        line_items.append(line_item)
                
                processing_time = time.time() - start_time
                avg_confidence = sum(item.confidence for item in line_items) / len(line_items) if line_items else 0.0
                
                result = TableResult(
                    type="table",
                    bbox=bbox,
                    line_items=line_items,
                    confidence=avg_confidence,
                    method_used="structure_aware",
                    processing_time=processing_time,
                    fallback_used=False,
                    cell_count=len(cells),
                    row_count=len(rows)
                )
                
                LOGGER.info("Structure-aware extraction: %d line items, %.3f confidence", 
                           len(line_items), avg_confidence)
                
                return result
            
            else:
                # Fallback to line grouping
                LOGGER.info("Structure detection failed, using fallback line grouping")
                line_items = self._fallback_line_grouping(table_img, ocr_text)
                
                processing_time = time.time() - start_time
                avg_confidence = sum(item.confidence for item in line_items) / len(line_items) if line_items else 0.0
                
                result = TableResult(
                    type="table",
                    bbox=bbox,
                    line_items=line_items,
                    confidence=avg_confidence,
                    method_used="fallback_line_grouping",
                    processing_time=processing_time,
                    fallback_used=True,
                    cell_count=0,
                    row_count=len(line_items)
                )
                
                LOGGER.info("Fallback extraction: %d line items, %.3f confidence", 
                           len(line_items), avg_confidence)
                
                return result
                
        except Exception as e:
            LOGGER.error("Table extraction failed: %s", e)
            
            processing_time = time.time() - start_time
            
            return TableResult(
                type="table",
                bbox=bbox,
                line_items=[],
                confidence=0.0,
                method_used="error",
                processing_time=processing_time,
                fallback_used=True,
                cell_count=0,
                row_count=0
            )
    
    def save_table_artifacts(self, result: TableResult, artifact_dir: Path) -> Path:
        """Save table extraction results as JSON artifact."""
        try:
            artifact_dir.mkdir(parents=True, exist_ok=True)
            json_path = artifact_dir / f"table_extraction_{int(time.time())}.json"
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
            
            LOGGER.info("Table extraction artifacts saved to: %s", json_path)
            return json_path
            
        except Exception as e:
            LOGGER.error("Failed to save table extraction artifacts: %s", e)
            return Path()


# Global extractor instance
_extractor = None

def get_table_extractor() -> TableExtractor:
    """Get global table extractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = TableExtractor()
    return _extractor


def extract_table_from_block(image: np.ndarray, block_info: Dict[str, Any], 
                           ocr_text: str = "") -> TableResult:
    """
    Main entry point for table extraction from a single block.
    
    Args:
        image: Full document image
        block_info: Block information with type and bbox
        ocr_text: OCR text from the block (optional)
    
    Returns:
        TableResult with extracted line items
    """
    extractor = get_table_extractor()
    
    if block_info.get("type") != "table":
        LOGGER.warning("Block is not a table type: %s", block_info.get("type"))
        return TableResult(
            type=block_info.get("type", "unknown"),
            bbox=tuple(block_info.get("bbox", [0, 0, 0, 0])),
            line_items=[],
            confidence=0.0,
            method_used="not_table",
            processing_time=0.0,
            fallback_used=False,
            cell_count=0,
            row_count=0
        )
    
    bbox = tuple(block_info.get("bbox", [0, 0, 0, 0]))
    return extractor.extract_table(image, bbox, ocr_text)

