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
from collections import defaultdict

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
    pack_size: Optional[str] = None  # Pack size (e.g., "12L", "11G") for hospitality invoices
    bbox: Optional[List[int]] = None  # [x, y, w, h] for visual verification
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "description": self.description,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "total_price": self.total_price,
            "vat": self.vat,
            "confidence": self.confidence,
            "row_index": self.row_index,
            "cell_data": self.cell_data
        }
        if self.pack_size:
            result["pack_size"] = self.pack_size
        if self.bbox:
            result["bbox"] = self.bbox
        return result


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
        # Updated to handle 0-4 decimal places (UK B2B invoices often use 3-4 decimals for unit prices)
        self._price_patterns = [
            r'[£$€]\s?[\d,]+\.(\d{2}|\d{3}|\d{4})\b',  # Currency + 2-4 decimals: £123.4567
            r'[£$€]\s?[\d,]+\b',                        # Currency + integer: £123
            r'\$[\d,]+\.?\d*',                          # $123.45 (legacy)
            r'£[\d,]+\.?\d*',                           # £123.45 (UK currency, legacy)
            r'Â£[\d,]+\.?\d*',                          # Â£123.45 (encoded, legacy)
            r'â‚¬[\d,]+\.?\d*',                          # â‚¬123.45 (legacy)
            r'[\d,]+\.\d{2,4}\b',                       # 123.45 or 123.456 or 123.4567 (decimal format)
            r'[\d,]+\.?\d*',                            # 123.45 or 123 (fallback)
        ]
        
        self._quantity_patterns = [
            r'\d+\.?\d*',       # 123 or 123.45
            r'\d+x',            # 123x
            r'\d+\s*units?',   # 123 units
        ]
        
        # Header/meta keywords that should not be treated as line items
        self._header_meta_keywords = [
            "vat registration", "vat reg", "vat registration no", "vat registration number",
            "invoice to", "ship to", "bill to", "deliver to",
            "invoice no", "invoice number", "invoice date", "due date", "payment terms",
            "vat summary", "total due", "balance due", "amount due",
            "company registration", "company reg", "reg no", "registration no", "registration number",
            "registered office", "sort code", "account number", "account no", "bacs payment", "bank transfer",
            # Footer/contact markers
            "tel", "telephone", "phone", "email", "website",
            "delivered in containers", "we do not accept returns", "unless previously agreed in writing",
            "payment info", "payment information", "bank details", "signature", "name:", "date:",
            # Address-related keywords
            "road", "street", "estate", "industrial", "betws y coed", "ruthin", "denbighshire",
            "holyhead", "royal oak", "ll15", "ll24", "postcode", "post code"
        ]
        
        # Product keywords for hospitality invoices (expanded to cover all beverage categories)
        self._product_keywords = [
            # Beer categories
            "beer", "lager", "ale", "cider", "stout",
            # Containers/packaging
            "keg", "cask", "bottle", "draught", "firkin", "pin", "bbl", "kilderkin",
            # Beer styles
            "ipa", "pale", "pilsner", "kolsch", "bock", "porter",
            # Sizes/volumes
            "30l", "50l", "litre", "ltr", "l",
            # Juices
            "juice", "orange", "apple", "cranberry",
            # Soft drinks
            "lemonade", "cola", "pepsi", "coke", "tonic",
            # Mixers and other beverages
            "mixer", "soda", "syrup", "water", "sparkling",
            # Drink categories
            "soft drink", "energy drink", "cordial"
        ]
        
        # Configurable thresholds for sanity checks
        self._max_quantity_threshold = 100  # Reject quantities > 100
        self._min_price_threshold = 0.0  # Minimum valid price
        self._max_price_threshold = 1000.0  # Maximum valid price for single line item
        
        # UK postcode pattern: e.g., LL15 1NJ, LL24 OAY, SW1A 1AA
        self._postcode_pattern = re.compile(r"\b[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}\b")
        
        # PHASE 4 - Module D: Supplier-specific pattern cache (in-memory)
        self._supplier_patterns: Dict[str, Dict[str, Any]] = {}
    
    def _detect_price_grid_from_ocr_blocks(self, ocr_blocks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        MODULE 1: Detect price grid / right-edge alignment from OCR word blocks.
        
        Analyzes numeric tokens and their X-coordinates to find right-aligned price columns.
        This is advisory only - doesn't prevent parsing if grid detection fails.
        
        Args:
            ocr_blocks: List of OCR word blocks with 'text' and 'bbox' [x, y, w, h]
            
        Returns:
            Optional dict with grid structure:
            {
                "price_column_x": int,  # X position of rightmost price column
                "unit_price_column_x": Optional[int],  # X position of unit price column (if detected)
                "confidence": float,  # Confidence in grid detection (0.0 to 1.0)
                "column_width": int  # Estimated column width
            }
        """
        if not ocr_blocks:
            return None
        
        # Extract numeric tokens with their X positions
        numeric_tokens = []
        for block in ocr_blocks:
            text = block.get('text', '')
            bbox = block.get('bbox', [0, 0, 0, 0])
            
            if len(bbox) >= 4:
                x, y, w, h = bbox[0], bbox[1], bbox[2], bbox[3]
                x_center = x + w // 2
                x_right = x + w  # Right edge of token
                
                # Check if text is numeric (price-like)
                # Match patterns like: "69.31", "123.45", "1,234.56", "£123.45"
                if re.match(r'^[£$€]?\s*[\d,]+\.?\d{0,2}\s*$', text.strip()):
                    try:
                        # Try to parse as float to validate
                        cleaned = text.replace('£', '').replace('$', '').replace('€', '').replace(',', '').strip()
                        price_val = float(cleaned)
                        if 0 < price_val < 100000:  # Sanity check
                            numeric_tokens.append({
                                'text': text,
                                'x_center': x_center,
                                'x_right': x_right,
                                'y': y,
                                'value': price_val
                            })
                    except (ValueError, TypeError):
                        pass
        
        if len(numeric_tokens) < 3:  # Need at least 3 numeric tokens to detect a pattern
            return None
        
        # Cluster X positions to find price columns
        # Use right edge (x_right) for right-aligned columns
        x_right_positions = [token['x_right'] for token in numeric_tokens]
        
        # Simple clustering: find the most common X position (within tolerance)
        tolerance = 30  # Pixels tolerance for column alignment
        clusters = defaultdict(list)
        
        for token in numeric_tokens:
            x_right = token['x_right']
            # Find existing cluster within tolerance
            matched_cluster = None
            for cluster_x in clusters.keys():
                if abs(x_right - cluster_x) <= tolerance:
                    matched_cluster = cluster_x
                    break
            
            if matched_cluster is not None:
                clusters[matched_cluster].append(token)
            else:
                clusters[x_right].append(token)
        
        if not clusters:
            return None
        
        # Find the rightmost cluster (likely total price column)
        rightmost_x = max(clusters.keys())
        rightmost_cluster = clusters[rightmost_x]
        
        # Calculate confidence based on cluster size and consistency
        total_tokens = len(numeric_tokens)
        cluster_size = len(rightmost_cluster)
        confidence = min(0.95, 0.5 + (cluster_size / total_tokens) * 0.45)
        
        # Estimate column width from cluster spread
        if rightmost_cluster:
            x_positions = [token['x_right'] for token in rightmost_cluster]
            column_width = max(x_positions) - min(x_positions) + 50  # Add padding
        else:
            column_width = 100
        
        # Try to find a second column (unit price) - look for cluster to the left
        unit_price_x = None
        if len(clusters) > 1:
            # Sort clusters by X position (right to left)
            sorted_clusters = sorted(clusters.items(), key=lambda x: x[0], reverse=True)
            if len(sorted_clusters) >= 2:
                # Second rightmost cluster might be unit price
                second_x, second_cluster = sorted_clusters[1]
                # Check if it's significantly to the left (at least 50 pixels)
                if rightmost_x - second_x >= 50 and len(second_cluster) >= 2:
                    unit_price_x = int(second_x)
        
        LOGGER.debug(f"[PRICE_GRID] Detected price grid: price_column_x={rightmost_x}, "
                    f"unit_price_x={unit_price_x}, confidence={confidence:.3f}, "
                    f"cluster_size={cluster_size}/{total_tokens}")
        
        return {
            "price_column_x": int(rightmost_x),
            "unit_price_column_x": unit_price_x,
            "confidence": confidence,
            "column_width": column_width
        }
    
    def _reconcile_line_items(self, line_items: List[LineItem], invoice_total: Optional[float], strictness: Dict[str, Any]) -> Tuple[List[LineItem], Dict[str, Any]]:
        """
        MODULE 7: Reconciliation / parity-aware post-processing.
        
        After parsing raw line_items, add post-processing reconciliation:
        - Calculate sum_line_total
        - Compare with invoice_grand_total
        - Try to infer missing totals for lines with unit price but no total
        - Use SUBTOTAL hints
        
        Args:
            line_items: List of parsed LineItem objects
            invoice_total: Invoice grand total (or subtotal if grand total missing)
            strictness: Parsing strictness config from MODULE 6
            
        Returns:
            Tuple of (reconciled_line_items, reconciliation_info)
        """
        reconciliation_info = {
            "sum_line_total_before": 0.0,
            "sum_line_total_after": 0.0,
            "invoice_total": invoice_total,
            "mismatch_before": None,
            "mismatch_after": None,
            "items_improved": 0,
            "items_with_inferred_total": 0,
            "value_coverage": 0.0,  # PHASE 6: Value coverage
            "inference_notes": [],  # PHASE 6: Track all inferences
            "capped_totals_count": 0  # PHASE 6: Count of capped totals
        }
        
        if not line_items:
            return (line_items, reconciliation_info)
        
        # Calculate sum_line_total before reconciliation
        sum_before = 0.0
        for item in line_items:
            if item.total_price:
                try:
                    total_str = item.total_price.replace('£', '').replace('$', '').replace('€', '').replace(',', '').strip()
                    total_val = float(total_str)
                    if total_val > 0:
                        sum_before += total_val
                except (ValueError, TypeError):
                    pass
        
        reconciliation_info["sum_line_total_before"] = sum_before
        
        # Calculate mismatch before
        if invoice_total and invoice_total > 0:
            mismatch_before = abs(invoice_total - sum_before) / invoice_total
            reconciliation_info["mismatch_before"] = mismatch_before
        
        # PHASE 6: Initialize inference tracking
        inference_notes = []
        capped_totals_count = 0
        
        # If parity is poor (> 50% mismatch), try to improve
        reconciled_items = []
        items_improved = 0
        items_with_inferred_total = 0
        
        for item in line_items:
            # PHASE 6: Cap absurd totals (> 100,000 per line item)
            if item.total_price:
                try:
                    total_str = item.total_price.replace('£', '').replace('$', '').replace('€', '').replace(',', '').strip()
                    total_val = float(total_str)
                    if total_val > 100000:
                        # Cap to 100,000 and log
                        item.total_price = "100000.00"
                        capped_totals_count += 1
                        note = f"Capped absurd total: {total_val:.2f} → 100000.00 for '{item.description[:50]}'"
                        inference_notes.append(note)
                        LOGGER.warning(f"[RECONCILE] {note}")
                        
                        # Mark in cell_data
                        if not item.cell_data:
                            item.cell_data = {}
                        item.cell_data["total_capped"] = True
                        item.cell_data["original_total"] = total_val
                except (ValueError, TypeError, AttributeError):
                    pass
            
            # Try to infer missing total_price from qty × unit_price
            if not item.total_price or item.total_price == "" or item.total_price == "0":
                if item.quantity and item.unit_price:
                    try:
                        qty_str = item.quantity.replace(',', '').strip()
                        unit_str = item.unit_price.replace('£', '').replace('$', '').replace('€', '').replace(',', '').strip()
                        qty_val = float(qty_str)
                        unit_val = float(unit_str)
                        
                        # Safety checks
                        if qty_val > 0 and unit_val > 0 and qty_val <= 100 and unit_val < 15000:
                            inferred_total = qty_val * unit_val
                            # PHASE 6: Cap inferred totals too
                            if inferred_total > 100000:
                                inferred_total = 100000.0
                                capped_totals_count += 1
                                note = f"Capped inferred total: {qty_val} × {unit_val} = {inferred_total:.2f} for '{item.description[:50]}'"
                                inference_notes.append(note)
                                LOGGER.warning(f"[RECONCILE] {note}")
                            
                            if inferred_total < 100000:
                                item.total_price = f"{inferred_total:.2f}"
                                items_with_inferred_total += 1
                                
                                # PHASE 6: Track inference
                                note = f"Inferred total_price: {qty_val} × {unit_val} = {inferred_total:.2f} for '{item.description[:50]}'"
                                inference_notes.append(note)
                                
                                # Mark in cell_data
                                if not item.cell_data:
                                    item.cell_data = {}
                                item.cell_data["total_inferred"] = True
                                item.cell_data["inference_method"] = "qty_times_unit"
                                if "inference_notes" not in item.cell_data:
                                    item.cell_data["inference_notes"] = []
                                item.cell_data["inference_notes"].append(note)
                                
                                # Slightly lower confidence for inferred values
                                item.confidence = item.confidence * 0.95
                                
                                LOGGER.debug(f"[RECONCILE] {note}")
                    except (ValueError, TypeError, AttributeError):
                        pass
            
            reconciled_items.append(item)
        
        # Calculate sum_line_total after reconciliation
        sum_after = 0.0
        for item in reconciled_items:
            if item.total_price:
                try:
                    total_str = item.total_price.replace('£', '').replace('$', '').replace('€', '').replace(',', '').strip()
                    total_val = float(total_str)
                    if total_val > 0:
                        sum_after += total_val
                except (ValueError, TypeError):
                    pass
        
        reconciliation_info["sum_line_total_after"] = sum_after
        reconciliation_info["items_with_inferred_total"] = items_with_inferred_total
        reconciliation_info["inference_notes"] = inference_notes
        reconciliation_info["capped_totals_count"] = capped_totals_count
        
        # PHASE 6: Calculate value_coverage = sum(line totals) / invoice total
        value_coverage = 0.0
        if invoice_total and invoice_total > 0:
            value_coverage = min(1.0, sum_after / invoice_total)  # Cap at 1.0 (100%)
            reconciliation_info["value_coverage"] = value_coverage
            LOGGER.info(f"[RECONCILE] Value coverage: {value_coverage*100:.1f}% (sum={sum_after:.2f}, invoice_total={invoice_total:.2f})")
        else:
            reconciliation_info["value_coverage"] = 0.0
        
        # Calculate mismatch after
        if invoice_total and invoice_total > 0:
            mismatch_after = abs(invoice_total - sum_after) / invoice_total
            reconciliation_info["mismatch_after"] = mismatch_after
            
            # Check if we improved
            if mismatch_before and mismatch_after < mismatch_before:
                items_improved = items_with_inferred_total
                LOGGER.info(f"[RECONCILE] Improved parity: mismatch {mismatch_before*100:.1f}% → {mismatch_after*100:.1f}% "
                           f"(inferred {items_with_inferred_total} totals, value_coverage={value_coverage*100:.1f}%)")
        
        reconciliation_info["items_improved"] = items_improved
        
        return (reconciled_items, reconciliation_info)
    
    def _get_parsing_strictness(self, base_confidence: float) -> Dict[str, Any]:
        """
        MODULE 6: Get parsing strictness configuration based on OCR confidence.
        
        Args:
            base_confidence: Base OCR confidence (0.0 to 1.0)
            
        Returns:
            Dict with strictness settings:
            - min_description_length: Minimum description length
            - require_alphabetic: Require alphabetic characters in description
            - require_product_keyword: Require product keywords
            - min_price_threshold: Minimum price threshold
            - max_price_threshold: Maximum price threshold
            - qty_1_evidence_required: Evidence required for qty=1 assumption
            - decimal_tolerance: Tolerance for decimal quirks
        """
        if base_confidence >= 0.90:
            # High confidence: Stricter rules, less likely to mis-parse noise
            return {
                "min_description_length": 5,
                "require_alphabetic": True,
                "require_product_keyword": False,  # Still allow valid prices
                "min_price_threshold": 0.01,
                "max_price_threshold": 10000.0,
                "qty_1_evidence_required": "strong",  # Need drink keyword + price
                "decimal_tolerance": 0.01,  # Very strict
                "confidence_boost": 1.0  # No boost needed
            }
        elif base_confidence < 0.80:
            # Low confidence: Relaxed heuristics, accept more quirks
            return {
                "min_description_length": 3,  # More lenient
                "require_alphabetic": True,  # Still require some text
                "require_product_keyword": False,  # More lenient
                "min_price_threshold": 0.0,
                "max_price_threshold": 15000.0,  # Slightly higher
                "qty_1_evidence_required": "weak",  # Accept qty=1 with weaker evidence
                "decimal_tolerance": 0.05,  # More tolerant
                "confidence_boost": 0.9  # Slight boost for low confidence
            }
        else:
            # Medium confidence: Balanced
            return {
                "min_description_length": 4,
                "require_alphabetic": True,
                "require_product_keyword": False,
                "min_price_threshold": 0.01,
                "max_price_threshold": 10000.0,
                "qty_1_evidence_required": "medium",  # Moderate evidence
                "decimal_tolerance": 0.02,
                "confidence_boost": 0.95
            }
    
    def _clean_description(self, text: str) -> str:
        """
        Clean description text by removing leading garbage, normalizing spaces.
        
        Args:
            text: Raw description text
            
        Returns:
            Cleaned description text
        """
        if not text:
            return ""
        
        # Strip leading/trailing whitespace
        cleaned = text.strip()
        
        # Remove leading garbage characters: quotes, punctuation, stray symbols
        # Pattern: leading quotes, bullets, asterisks, dots, etc.
        cleaned = re.sub(r'^[\'"`\u2018\u2019\u201C\u201D\u2022\u2023\u25E6\u2043\u2219\*\^\~\`\.\s]+', '', cleaned)
        
        # Normalize repeated spaces to single space
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Remove trailing punctuation that might be OCR noise
        cleaned = re.sub(r'[\s\.\-\_]+$', '', cleaned)
        
        return cleaned.strip()
    
    def _detect_line_structure(self, lines: List[str], sample_size: int = 20, word_blocks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        PHASE 4 - Module A + PHASE 5 - Module C: Line-Structure Modeling with Bounding Box Support
        
        Detects invoice item structure by analyzing patterns across multiple lines.
        Uses bounding boxes when available for more robust column detection.
        Infers column positions for quantity, description, price, and pack-size.
        
        Args:
            lines: List of OCR text lines
            sample_size: Number of lines to analyze (default: 20)
            word_blocks: Optional list of word blocks with bbox info for spatial analysis
            
        Returns:
            Dict with structure info:
            {
                "qty_pos": Optional[int],  # Token index where quantity appears (0-based)
                "price_pos": Optional[int],  # Token index where price appears (from right, 0=rightmost)
                "desc_window": [start_idx, end_idx],  # Token indices for description region
                "pack_pos": Optional[int],  # Token index where pack-size appears
                "confidence": float  # Confidence in structure detection (0.0 to 1.0)
            }
        """
        if not lines or len(lines) < 3:
            return {
                "qty_pos": None,
                "price_pos": None,
                "desc_window": [0, -1],
                "pack_pos": None,
                "confidence": 0.0
            }
        
        # Analyze sample of lines (focus on lines that look like items)
        sample_lines = []
        for line in lines[:sample_size]:
            line_stripped = line.strip()
            # Skip empty, very short, or header-like lines
            if len(line_stripped) < 5:
                continue
            line_lower = line_stripped.lower()
            # Skip obvious headers/footers
            if any(kw in line_lower for kw in ['subtotal', 'total', 'vat', 'invoice', 'date']):
                continue
            sample_lines.append(line_stripped)
        
        if len(sample_lines) < 3:
            return {
                "qty_pos": None,
                "price_pos": None,
                "desc_window": [0, -1],
                "pack_pos": None,
                "confidence": 0.0
            }
        
        # Tokenize each line and analyze patterns
        token_patterns = {
            "qty_at_start": 0,  # Count lines with number at start
            "price_at_end": 0,  # Count lines with price-like pattern at end
            "pack_size_patterns": 0,  # Count lines with pack-size patterns (12L, 30L, 24x330ml)
            "two_prices": 0,  # Count lines with two price-like numbers
        }
        
        qty_positions = []  # Track where quantities appear (token index from left)
        price_positions = []  # Track where prices appear (token index from right)
        pack_positions = []  # Track where pack-sizes appear
        desc_starts = []  # Track where descriptions typically start
        desc_ends = []  # Track where descriptions typically end
        
        # PHASE 5 - Module C: Bounding box-based structure detection
        bbox_qty_x_positions = []  # X positions of quantity tokens from bboxes
        bbox_price_x_positions = []  # X positions of price tokens from bboxes
        bbox_confidence = 0.0
        
        if word_blocks and len(word_blocks) > 0:
            # Group word blocks by approximate Y position (same line)
            y_tolerance = 10  # Pixels tolerance for same line
            lines_by_y = defaultdict(list)
            for wb in word_blocks:
                if isinstance(wb, dict):
                    bbox = wb.get('bbox', [])
                    text = wb.get('text', '')
                    conf = wb.get('confidence', 0.5)
                else:
                    bbox = getattr(wb, 'bbox', [])
                    text = getattr(wb, 'text', '')
                    conf = getattr(wb, 'confidence', 0.5)
                
                if len(bbox) >= 4 and text:
                    x, y, w, h = bbox[0], bbox[1], bbox[2], bbox[3]
                    # Round Y to group by line
                    rounded_y = (y // y_tolerance) * y_tolerance
                    lines_by_y[rounded_y].append({
                        'x': x,
                        'text': text,
                        'confidence': conf
                    })
            
            # Analyze each line's X positions
            numeric_pattern = re.compile(r'^\d+\.?\d*$')
            price_pattern_bbox = re.compile(r'[\d,]+\.\d{2}')
            
            for y_pos, words in lines_by_y.items():
                if len(words) < 2:  # Need at least 2 words for structure
                    continue
                
                # Sort words by X position (left to right)
                words_sorted = sorted(words, key=lambda w: w['x'])
                
                # Find quantity (usually first numeric token)
                for i, word in enumerate(words_sorted):
                    text = word['text'].strip()
                    if numeric_pattern.match(text) and float(text) <= 100:  # Reasonable qty
                        bbox_qty_x_positions.append(word['x'])
                        break
                
                # Find prices (usually rightmost tokens with decimal)
                for i in range(len(words_sorted) - 1, -1, -1):
                    word = words_sorted[i]
                    text = word['text'].strip()
                    if price_pattern_bbox.search(text):
                        bbox_price_x_positions.append(word['x'])
                        break
            
            # Cluster X positions to find column positions
            if bbox_qty_x_positions:
                # Find mode X position (with tolerance)
                qty_x_clusters = defaultdict(int)
                tolerance = 30  # Pixels tolerance for column alignment
                for x in bbox_qty_x_positions:
                    # Find existing cluster within tolerance
                    cluster_x = None
                    for cluster in qty_x_clusters.keys():
                        if abs(x - cluster) <= tolerance:
                            cluster_x = cluster
                            break
                    if cluster_x is None:
                        cluster_x = x
                    qty_x_clusters[cluster_x] += 1
                
                if qty_x_clusters:
                    bbox_qty_mode_x = max(qty_x_clusters.items(), key=lambda x: x[1])[0]
                    bbox_confidence += 0.3  # Boost confidence if bbox qty found
            
            if bbox_price_x_positions:
                # Find mode X position for prices
                price_x_clusters = defaultdict(int)
                tolerance = 30
                for x in bbox_price_x_positions:
                    cluster_x = None
                    for cluster in price_x_clusters.keys():
                        if abs(x - cluster) <= tolerance:
                            cluster_x = cluster
                            break
                    if cluster_x is None:
                        cluster_x = x
                    price_x_clusters[cluster_x] += 1
                
                if price_x_clusters:
                    bbox_price_mode_x = max(price_x_clusters.items(), key=lambda x: x[1])[0]
                    bbox_confidence += 0.3  # Boost confidence if bbox price found
        
        # Pack-size patterns: 12L, 30L, 24x330ml, 11G, etc.
        pack_pattern = re.compile(r'\b\d+[xX]?\d*\s*(?:L|G|ML|ml|litre|litres|gallon|gallons)\b', re.IGNORECASE)
        # Price pattern: numbers with 2 decimal places or currency symbols
        price_pattern = re.compile(r'[£$€]?\s*[\d,]+\.\d{2}\b')
        # Quantity pattern: number at start of line (possibly with prefix noise)
        qty_pattern = re.compile(r'^[\W\s]*?(\d+)[\s\.\)\^]+')
        
        for line in sample_lines:
            tokens = line.split()
            if not tokens:
                continue
            
            # Check for quantity at start
            qty_match = qty_pattern.match(line)
            if qty_match:
                token_pos = len(line[:qty_match.end()].split()) - 1
                qty_positions.append(token_pos)
                token_patterns["qty_at_start"] += 1
                desc_starts.append(token_pos + 1)  # Description starts after qty
            
            # Check for prices (from right)
            prices = price_pattern.findall(line)
            if prices:
                token_patterns["price_at_end"] += 1
                # Find rightmost price token position
                last_price = prices[-1]
                price_start = line.rfind(last_price)
                price_tokens = line[:price_start].split()
                price_pos = len(line.split()) - len(price_tokens) - 1
                price_positions.append(price_pos)
                
                if len(prices) >= 2:
                    token_patterns["two_prices"] += 1
            
            # Check for pack-size patterns
            pack_match = pack_pattern.search(line)
            if pack_match:
                token_patterns["pack_size_patterns"] += 1
                pack_start = pack_match.start()
                pack_tokens = line[:pack_start].split()
                pack_pos = len(pack_tokens)
                pack_positions.append(pack_pos)
            
            # Estimate description end (before prices)
            if prices:
                last_price_start = line.rfind(prices[-1])
                desc_end_tokens = line[:last_price_start].split()
                desc_ends.append(len(desc_end_tokens))
        
        # Infer structure from patterns
        structure = {
            "qty_pos": None,
            "price_pos": None,
            "desc_window": [0, -1],
            "pack_pos": None,
            "confidence": 0.0
        }
        
        total_lines = len(sample_lines)
        confidence_factors = []
        
        # PHASE 5 - Module C: Hybrid detection (bbox + text-based)
        # Use bbox positions if confidence is high, otherwise use text-based
        
        # Quantity position (from left, usually 0 or 1)
        qty_text_confidence = 0.0
        if qty_positions:
            qty_pos_mode = max(set(qty_positions), key=qty_positions.count)
            qty_text_confidence = qty_positions.count(qty_pos_mode) / total_lines
            # Lower threshold for bbox-based (20%) vs text-based (30%)
            threshold = 0.20 if bbox_confidence > 0.6 else 0.30
            if qty_text_confidence >= threshold:
                structure["qty_pos"] = qty_pos_mode
                confidence_factors.append(qty_text_confidence)
        
        # If bbox detected qty and text didn't, use bbox info to boost confidence
        if bbox_qty_x_positions and not structure["qty_pos"]:
            # Try to map bbox X position to token position
            # This is approximate - we'd need to map bbox to text tokens
            # For now, just boost confidence if bbox found something
            if bbox_confidence > 0.3:
                # Assume qty is at position 0 if bbox found it
                structure["qty_pos"] = 0
                confidence_factors.append(0.4)  # Moderate confidence from bbox
        
        # Price position (from right, usually 0 or 1)
        price_text_confidence = 0.0
        if price_positions:
            price_pos_mode = max(set(price_positions), key=price_positions.count)
            price_text_confidence = price_positions.count(price_pos_mode) / total_lines
            threshold = 0.20 if bbox_confidence > 0.6 else 0.30
            if price_text_confidence >= threshold:
                structure["price_pos"] = price_pos_mode
                confidence_factors.append(price_text_confidence)
        
        # If bbox detected price and text didn't, use bbox info
        if bbox_price_x_positions and not structure["price_pos"]:
            if bbox_confidence > 0.3:
                # Assume price is at rightmost position (0 from right) if bbox found it
                structure["price_pos"] = 0
                confidence_factors.append(0.4)  # Moderate confidence from bbox
        
        # Pack-size position
        if pack_positions:
            pack_pos_mode = max(set(pack_positions), key=pack_positions.count)
            pack_confidence = pack_positions.count(pack_pos_mode) / total_lines
            if pack_confidence >= 0.2:  # Lower threshold for pack-size (less common)
                structure["pack_pos"] = pack_pos_mode
                confidence_factors.append(pack_confidence * 0.5)  # Lower weight
        
        # Description window
        if desc_starts and desc_ends:
            desc_start_mode = max(set(desc_starts), key=desc_starts.count) if desc_starts else 0
            desc_end_mode = max(set(desc_ends), key=desc_ends.count) if desc_ends else -1
            structure["desc_window"] = [desc_start_mode, desc_end_mode]
        
        # Overall confidence (combine text-based and bbox-based)
        if confidence_factors:
            text_confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.0
            # Weighted combination: 70% text, 30% bbox (if bbox available)
            if bbox_confidence > 0.3:
                structure["confidence"] = min(0.95, 0.7 * text_confidence + 0.3 * bbox_confidence)
            else:
                structure["confidence"] = min(0.95, text_confidence)
        elif bbox_confidence > 0.3:
            # Only bbox confidence available
            structure["confidence"] = min(0.95, bbox_confidence * 0.7)  # Slightly lower weight for bbox-only
        
        LOGGER.debug(f"[LINE_STRUCTURE] Detected structure: qty_pos={structure['qty_pos']}, "
                    f"price_pos={structure['price_pos']}, pack_pos={structure['pack_pos']}, "
                    f"desc_window={structure['desc_window']}, confidence={structure['confidence']:.3f} "
                    f"(bbox_conf={bbox_confidence:.3f})")
        
        return structure
    
    def _line_has_quantity_and_product_words(self, text: str) -> bool:
        """
        Check if a line has both quantity-like tokens and product words.
        
        This is used to override header/meta classification - if a line has
        a quantity AND product words, it's almost certainly an item line.
        
        Args:
            text: Line text to check
            
        Returns:
            True if line has quantity candidate AND product words, False otherwise
        """
        if not text or not text.strip():
            return False
        
        text_lower = text.lower()
        
        # Find quantity candidates (integers 1-120)
        numeric_pattern = re.compile(r'\b(\d+)\b')
        quantity_candidates = []
        for match in numeric_pattern.finditer(text):
            try:
                value = int(match.group(1))
                if 1 <= value <= 120:
                    quantity_candidates.append(value)
            except (ValueError, AttributeError):
                continue
        
        if not quantity_candidates:
            return False
        
        # Check for product words (not meta words)
        meta_keywords = ['invoice', 'no', 'number', 'account', 'statement', 'vat', 
                        'total', 'date', 'page', 'due', 'payment', 'terms']
        has_meta_word = any(keyword in text_lower for keyword in meta_keywords)
        
        # Check for product keywords
        has_product_keyword = any(keyword in text_lower for keyword in self._product_keywords)
        
        # Also check for common product indicators (not in product_keywords list)
        product_indicators = ['pepsi', 'coke', 'cola', 'lemonade', 'connector', 
                            'litre', 'ltr', 'gallon', 'pack', 'case', 'bottle', 'can']
        has_product_indicator = any(indicator in text_lower for indicator in product_indicators)
        
        # Has quantity AND (product keyword OR product indicator) AND not dominated by meta words
        if quantity_candidates and (has_product_keyword or has_product_indicator):
            # If it has strong product signal, override meta words
            if has_product_keyword or (has_product_indicator and not has_meta_word):
                return True
        
        return False
    
    def _is_header_or_meta_description(self, desc: str, price_value: Optional[float] = None, line_index: Optional[int] = None, items_region: Optional[Tuple[int, int]] = None) -> bool:
        """
        Check if a description is header/meta information, not a real line item.
        
        EARLY ESCAPE: If line has quantity + product words, immediately return False
        (i.e., NOT header/meta).
        
        Args:
            desc: Description text to check
            price_value: Optional numeric price value to check for unrealistic values
            line_index: Optional line index for position-based filtering
            items_region: Optional tuple (y_min, y_max) for items region filtering
            
        Returns:
            True if this looks like header/meta, False if it could be a real item
        """
        if not desc:
            return True
        
        desc_lower = desc.lower().strip()
        
        # EARLY ESCAPE: If line has quantity + product words, it's NOT header/meta
        if self._line_has_quantity_and_product_words(desc):
            LOGGER.debug(f"[HEADER_FILTER] Overriding header/meta check: '{desc}' has quantity + product words")
            return False
        
        # Check if description contains header/meta keywords
        for keyword in self._header_meta_keywords:
            if keyword in desc_lower:
                LOGGER.debug(f"[HEADER_FILTER] Rejecting header/meta: '{desc}' (keyword: '{keyword}')")
                return True
        
        # Check for UK postcode pattern (e.g., LL15 1NJ, LL24 OAY)
        if self._postcode_pattern.search(desc):
            LOGGER.debug(f"[HEADER_FILTER] Rejecting postcode/address: '{desc}'")
            return True
        
        # Check if price is unrealistically large (likely an ID/registration number)
        if price_value is not None and price_value > 1_000_000:
            LOGGER.debug(f"[HEADER_FILTER] Rejecting due to unrealistic price: '{desc}' (price: {price_value})")
            return True
        
        # If items_region is detected and line_index is provided, check if line is outside region
        # Note: This requires y-position info which may not always be available
        # For now, we'll rely on keyword matching primarily
        
        return False
    
    def parse_qty_and_pack_size(self, text: str) -> Tuple[Optional[int], Optional[str], str]:
        """
        Parse quantity and pack size from text patterns common in hospitality invoices.
        
        Handles patterns like:
        - "12 LITRE PEPSI (pink connector)" → (None, "12L", "PEPSI (pink connector)")
          Note: Returns None for quantity since caller should use outer quantity
        - "4x11G CARLING" → (4, "11G", "CARLING")
        - "30LTR COCA COLA" → (None, "30L", "COCA COLA")
        - "24.79 Gwynt Black Dragon" → (None, None, "24.79 Gwynt Black Dragon") (no pack size)
        
        Args:
            text: Input text that may contain pack size (and optionally quantity)
            
        Returns:
            Tuple of (quantity, pack_size, cleaned_description)
            - quantity: Integer quantity or None (caller should use outer quantity from line start)
            - pack_size: Normalized pack size (e.g., "12L", "11G") or None
            - cleaned_description: Description with pack size removed
        """
        if not text or not text.strip():
            return (None, None, text)
        
        text = text.strip()
        
        # MODULE 2: Enhanced pattern matching for two numeric values near start
        # Pattern 1a: "1 30L" or "6 12L" - two numbers, second is pack size
        # This handles cases where outer quantity might not have been extracted
        pattern1a = r'^(\d+)\s+(\d+)(L|G|LTR|GAL)\s+(.+)$'
        match1a = re.match(pattern1a, text, re.IGNORECASE)
        if match1a:
            # First number could be quantity or part of pack size - prefer as pack size if second is unit
            pack_num = match1a.group(2)
            unit = match1a.group(3).upper()
            desc = match1a.group(4).strip()
            
            # Normalize units
            if unit in ['LTR', 'L']:
                pack_size = f"{pack_num}L"
            elif unit in ['GAL', 'G']:
                pack_size = f"{pack_num}G"
            else:
                pack_size = f"{pack_num}{unit}"
            
            # Return None for quantity - caller should use outer quantity from line start
            return (None, pack_size, desc)
        
        # Pattern 1: "12 LITRE PEPSI" or "12 LTR PEPSI" 
        # Matches: number + space + unit + space + description (this is pack size, not quantity)
        # For "i 6 12 LITRE PEPSI", the outer quantity is 6, and "12 LITRE" is pack size
        pattern1 = r'^(\d+)\s+(LITRE|LTR|LTRS|GALLON|GAL)\s+(.+)$'
        match1 = re.match(pattern1, text, re.IGNORECASE)
        if match1:
            pack_num = match1.group(1)
            unit = match1.group(2).upper()
            desc = match1.group(3).strip()
            
            # Normalize units
            if unit in ['LITRE', 'LTR', 'LTRS', 'L']:
                pack_size = f"{pack_num}L"
            elif unit in ['GALLON', 'GAL', 'G']:
                pack_size = f"{pack_num}G"
            else:
                pack_size = f"{pack_num}{unit}"
            
            # Return None for quantity - caller should use outer quantity from line start
            return (None, pack_size, desc)
        
        # Pattern 2: "12L PEPSI" or "11G CARLING" (compact format, no space before unit)
        # Matches: number + unit (no space) + description
        pattern2 = r'^(\d+)(L|G|LTR|GAL)\s+(.+)$'
        match2 = re.match(pattern2, text, re.IGNORECASE)
        if match2:
            pack_num = match2.group(1)
            unit = match2.group(2).upper()
            desc = match2.group(3).strip()
            
            # Normalize units
            if unit in ['LTR', 'L']:
                pack_size = f"{pack_num}L"
            elif unit in ['GAL', 'G']:
                pack_size = f"{pack_num}G"
            else:
                pack_size = f"{pack_num}{unit}"
            
            # Return None for quantity - caller should use outer quantity from line start
            return (None, pack_size, desc)
        
        # Pattern 3: "4x11G CARLING" or "4x11L CARLING"
        # Matches: qty + x + number + unit + description
        # This pattern includes quantity, so we return it
        pattern3 = r'^(\d+)x(\d+)(L|G|LTR|GAL)\s+(.+)$'
        match3 = re.match(pattern3, text, re.IGNORECASE)
        if match3:
            qty = int(match3.group(1))
            pack_num = match3.group(2)
            unit = match3.group(3).upper()
            desc = match3.group(4).strip()
            
            # Normalize units
            if unit in ['LTR', 'L']:
                pack_size = f"{pack_num}L"
            elif unit in ['GAL', 'G']:
                pack_size = f"{pack_num}G"
            else:
                pack_size = f"{pack_num}{unit}"
            
            return (qty, pack_size, desc)
        
        # No pack size pattern found
        # Return None for both quantity and pack_size
        # Caller should use outer quantity from line start
        return (None, None, text)
    
    def _load_paddle_ocr(self) -> Optional[PaddleOCR]:
        """Load PaddleOCR for cell-level OCR processing."""
        if self._paddle_ocr is not None:
            return self._paddle_ocr
            
        if not PADDLEOCR_AVAILABLE:
            LOGGER.warning("PaddleOCR not available for table extraction")
            return None
            
        try:
            # Set protobuf environment variable before importing/using PaddleOCR
            import os
            os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
            LOGGER.info("Loading PaddleOCR for table extraction...")
            # Note: use_angle_cls, use_gpu, show_log are deprecated in newer PaddleOCR
            self._paddle_ocr = PaddleOCR(
                use_textline_orientation=True,  # Replaces use_angle_cls
                lang='en'
                # use_gpu and show_log removed (deprecated)
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
            # Convert to grayscale if needed
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            
            # Apply binary threshold ONLY for structure detection (not for OCR)
            # This helps OpenCV find lines/contours but would hurt PaddleOCR
            gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                        cv2.THRESH_BINARY, 31, 9)
            
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
                result = ocr.ocr(cell_img)
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
    
    def _cluster_columns_by_x_position_with_profiling(self, words_with_positions: List[Tuple[str, int, int]], is_receipt_mode: bool = False) -> Optional[Tuple[List[int], Dict[int, str]]]:
        """
        Cluster columns by X-position AND identify roles using statistical profiling.
        This handles layout variance (e.g., [Qty][Desc] vs [Desc][Qty]).
        
        Returns:
            Tuple of (column_boundaries, column_roles) or None if clustering fails
            where column_roles maps column_index to role name
        """
        if not words_with_positions:
            return None
        
        # Extract X-centers of numeric words (likely qty/price/total)
        numeric_x_coords = []
        all_x_coords = []
        for text, x, y in words_with_positions:
            all_x_coords.append(x)
            # Check if word is numeric (quantity or price)
            if re.search(r'\d', text):
                numeric_x_coords.append(x)
        
        if len(numeric_x_coords) < 2:  # Need at least 2 numeric columns
            return None
        
        # Calculate image dimensions
        image_width = max(all_x_coords) - min(all_x_coords) if all_x_coords else 1000
        image_height = max([y for _, _, y in words_with_positions]) - min([y for _, _, y in words_with_positions])
        
        # Find column boundaries using gap detection
        sorted_x = sorted(numeric_x_coords)
        
        # For receipts: Relax threshold (columns are tight, use 1% instead of 2%)
        if is_receipt_mode:
            gap_threshold = max(15, int(image_width * 0.01))  # Receipts: tighter columns
            LOGGER.debug(f"[SPATIAL_CLUSTER] Receipt Mode: Relaxed gap_threshold for tight columns")
        else:
            gap_threshold = max(30, int(image_width * 0.02))  # Standard invoices
        
        LOGGER.debug(f"[SPATIAL_CLUSTER] Image: {image_width}x{image_height}px, gap_threshold: {gap_threshold}px")
        
        # Start with left edge
        column_boundaries = [0]
        
        # Find leftmost numeric word and add boundary before it
        first_numeric_x = sorted_x[0]
        padding = 50
        first_numeric_boundary = max(0, first_numeric_x - padding)
        
        if first_numeric_boundary > 50:
            column_boundaries.append(first_numeric_boundary)
        
        # Find gaps between numeric clusters
        for i in range(1, len(sorted_x)):
            if sorted_x[i] - sorted_x[i-1] > gap_threshold:
                boundary = (sorted_x[i-1] + sorted_x[i]) // 2
                column_boundaries.append(boundary)
        
        # Add right edge
        column_boundaries.append(sorted_x[-1] + 100)
        
        LOGGER.info(f"[SPATIAL_CLUSTER] Detected {len(column_boundaries)-1} columns at X-boundaries: {column_boundaries}")
        
        # Gather sample words for each column (first 5 rows)
        column_samples = defaultdict(list)
        rows_sampled = 0
        current_y = None
        y_tolerance = max(20, int(image_height * 0.01))
        
        for text, x, y in words_with_positions:
            # Track rows (for sampling limit)
            if current_y is None or abs(y - current_y) > y_tolerance:
                rows_sampled += 1
                current_y = y
            
            if rows_sampled > 5:  # Only sample first 5 rows
                break
            
            # Assign to column index
            col_idx = self._assign_word_to_column_by_index(x, column_boundaries)
            if col_idx >= 0:
                column_samples[col_idx].append(text)
        
        # Identify column roles using statistical profiling
        column_roles = self._identify_column_roles(column_samples)
        
        if not column_roles:
            LOGGER.warning("[SPATIAL_CLUSTER] Column role identification failed")
            return None
        
        return (column_boundaries, column_roles)
    
    def _cluster_columns_by_x_position(self, words_with_positions: List[Tuple[str, int, int]], is_receipt_mode: bool = False) -> Dict[str, List[int]]:
        """
        Cluster word X-positions into columns using histogram peak detection.
        
        Args:
            words_with_positions: List of (text, x_center, y_center) tuples
            
        Returns:
            Dict mapping column names to X-coordinate ranges: {"description": [0, 200], "qty": [200, 300], ...}
        """
        if not words_with_positions:
            return {}
        
        # Extract X-centers of numeric words (likely qty/price/total)
        numeric_x_coords = []
        all_x_coords = []
        for text, x, y in words_with_positions:
            all_x_coords.append(x)
            # Check if word is numeric (quantity or price)
            if re.search(r'\d', text):
                numeric_x_coords.append(x)
        
        if len(numeric_x_coords) < 3:
            # Not enough data for clustering
            return {}
        
        # Calculate image width from word positions
        image_width = max(all_x_coords) - min(all_x_coords) if all_x_coords else 1000
        
        # Simple histogram-based clustering
        # Sort and find gaps to identify column boundaries
        sorted_x = sorted(numeric_x_coords)
        
        # Find gaps larger than threshold (indicates column boundary)
        # Make threshold resolution-agnostic: 2% of image width, minimum 30px
        # At 300 DPI: typical invoice width ~2500px → 50px threshold
        # At 150 DPI: typical invoice width ~1250px → 30px threshold (minimum)
        # For receipts: Relax threshold (columns are tight, use 1% instead of 2%)
        if is_receipt_mode:
            gap_threshold = max(15, int(image_width * 0.01))  # Receipts: tighter columns
            LOGGER.debug(f"[SPATIAL_CLUSTER] Receipt Mode: Relaxed gap_threshold for tight columns")
        else:
            gap_threshold = max(30, int(image_width * 0.02))  # Standard invoices
        LOGGER.debug(f"[SPATIAL_CLUSTER] Image width: {image_width}px, gap_threshold: {gap_threshold}px")
        
        # CRITICAL FIX: Start column boundaries at 0 for description column
        # Then add boundaries BEFORE each numeric cluster (not at 0)
        column_boundaries = [0]  # Description always starts at left edge
        
        # Find the leftmost numeric word - this is where the first numeric column starts
        # Add padding to ensure description text to the left is captured
        first_numeric_x = sorted_x[0]
        padding = 50  # Leave 50px padding before first numeric column
        first_numeric_boundary = max(0, first_numeric_x - padding)
        
        # Only add this boundary if it's significantly different from 0
        if first_numeric_boundary > 50:
            column_boundaries.append(first_numeric_boundary)
        
        # Now find gaps between numeric clusters
        for i in range(1, len(sorted_x)):
            if sorted_x[i] - sorted_x[i-1] > gap_threshold:
                # Found a gap - this is a column boundary
                boundary = (sorted_x[i-1] + sorted_x[i]) // 2
                column_boundaries.append(boundary)
        
        # Add right edge
        if sorted_x:
            column_boundaries.append(sorted_x[-1] + 100)
        
        # Assign column roles based on position
        # Typical invoice layout: [Description (wide)] [Qty (narrow)] [Unit Price (narrow)] [Total (narrow)]
        column_ranges = {}
        
        if len(column_boundaries) >= 4:
            # We have at least 3 numeric columns
            column_ranges["description"] = [column_boundaries[0], column_boundaries[1]]
            column_ranges["qty"] = [column_boundaries[1], column_boundaries[2]]
            column_ranges["unit_price"] = [column_boundaries[2], column_boundaries[3]]
            column_ranges["total"] = [column_boundaries[3], column_boundaries[-1]]
        elif len(column_boundaries) >= 3:
            # We have 2 numeric columns (likely qty and total, or unit_price and total)
            column_ranges["description"] = [column_boundaries[0], column_boundaries[1]]
            column_ranges["qty_or_unit"] = [column_boundaries[1], column_boundaries[2]]
            column_ranges["total"] = [column_boundaries[2], column_boundaries[-1]]
        else:
            # Fallback: just description and one numeric column
            column_ranges["description"] = [column_boundaries[0], column_boundaries[1]]
            column_ranges["total"] = [column_boundaries[1], column_boundaries[-1]]
        
        LOGGER.info(f"[SPATIAL_CLUSTER] Detected {len(column_ranges)} columns at X-boundaries: {column_boundaries}")
        LOGGER.info(f"[SPATIAL_CLUSTER] Column assignments: {list(column_ranges.keys())}")
        for col_name, (x_min, x_max) in column_ranges.items():
            LOGGER.info(f"[SPATIAL_CLUSTER]   {col_name}: X=[{x_min}, {x_max})")
        
        return column_ranges
    
    def _calculate_union_bbox(self, word_blocks: List[Dict[str, Any]]) -> Optional[List[int]]:
        """
        Calculate the union bounding box that encloses all word blocks.
        
        Args:
            word_blocks: List of dicts with 'bbox' key [x, y, w, h]
            
        Returns:
            Union bbox as [x, y, w, h] or None if no valid blocks
        """
        if not word_blocks:
            return None
        
        valid_bboxes = []
        for block in word_blocks:
            bbox = block.get('bbox')
            if bbox and len(bbox) >= 4:
                valid_bboxes.append(bbox)
        
        if not valid_bboxes:
            return None
        
        # Calculate union rectangle
        min_x = min(bbox[0] for bbox in valid_bboxes)
        min_y = min(bbox[1] for bbox in valid_bboxes)
        max_x = max(bbox[0] + bbox[2] for bbox in valid_bboxes)
        max_y = max(bbox[1] + bbox[3] for bbox in valid_bboxes)
        
        # Return as [x, y, w, h]
        union_bbox = [
            int(min_x),
            int(min_y),
            int(max_x - min_x),
            int(max_y - min_y)
        ]
        
        return union_bbox
    
    def _identify_column_roles(self, column_samples: Dict[int, List[str]]) -> Dict[int, str]:
        """
        Identify column roles using statistical profiling.
        This handles layout variance (e.g., [Qty][Desc] vs [Desc][Qty]).
        
        Args:
            column_samples: Dict mapping column_index to list of sample words
            
        Returns:
            Dict mapping column_index to role ('description', 'qty', 'unit_price', 'total')
        """
        if not column_samples:
            return {}
        
        # Calculate "Text Score" for each column
        column_scores = {}
        for col_idx, words in column_samples.items():
            if not words:
                column_scores[col_idx] = 0.0
                continue
            
            # Calculate metrics
            total_chars = 0
            letter_chars = 0
            total_length = 0
            
            for word in words:
                word_str = str(word)
                total_length += len(word_str)
                for char in word_str:
                    total_chars += 1
                    if char.isalpha():
                        letter_chars += 1
            
            # Text Score = (average length) × (letter percentage)
            avg_length = total_length / len(words) if words else 0
            letter_pct = (letter_chars / total_chars) if total_chars > 0 else 0
            text_score = avg_length * letter_pct
            
            column_scores[col_idx] = text_score
            LOGGER.debug(f"[COLUMN_PROFILE] Col {col_idx}: avg_len={avg_length:.1f}, letter_pct={letter_pct:.2f}, score={text_score:.2f}")
        
        # Find column with highest text score = DESCRIPTION
        if not column_scores:
            return {}
        
        desc_col_idx = max(column_scores.items(), key=lambda x: x[1])[0]
        LOGGER.info(f"[COLUMN_PROFILE] Description column identified: Col {desc_col_idx} (score={column_scores[desc_col_idx]:.2f})")
        
        # Assign roles based on description position
        sorted_cols = sorted(column_scores.keys())
        roles = {}
        
        # Columns LEFT of description = qty (or date)
        left_cols = [c for c in sorted_cols if c < desc_col_idx]
        # Columns RIGHT of description = unit_price, total
        right_cols = [c for c in sorted_cols if c > desc_col_idx]
        
        # Assign description
        roles[desc_col_idx] = 'description'
        
        # Assign left columns (typically qty, sometimes date)
        if len(left_cols) >= 1:
            roles[left_cols[-1]] = 'qty'  # Rightmost left column is usually qty
        
        # Assign right columns
        if len(right_cols) >= 2:
            roles[right_cols[0]] = 'unit_price'
            roles[right_cols[-1]] = 'total'  # Rightmost is always total
        elif len(right_cols) == 1:
            roles[right_cols[0]] = 'total'  # Only one numeric column = total
        
        LOGGER.info(f"[COLUMN_PROFILE] Role assignments: {roles}")
        return roles
    
    def _assign_word_to_column(self, x_center: int, column_ranges: Dict[str, List[int]]) -> str:
        """Assign a word to a column based on its X-coordinate."""
        for col_name, (x_min, x_max) in column_ranges.items():
            if x_min <= x_center < x_max:
                return col_name
        return "unknown"
    
    def _assign_word_to_column_by_index(self, x_center: int, column_boundaries: List[int]) -> int:
        """Assign a word to a column index based on its X-coordinate."""
        for i in range(len(column_boundaries) - 1):
            if column_boundaries[i] <= x_center < column_boundaries[i + 1]:
                return i
        return -1  # Unknown column
    
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
        
        # Ensure cell_data contains raw values for debugging
        if not cell_data:
            cell_data = {}
        cell_data.setdefault("raw_quantity", quantity)
        cell_data.setdefault("raw_unit_price", unit_price)
        cell_data.setdefault("raw_total_price", total_price)
        
        # Validation: ensure quantity and total_price are not empty strings if we have a description
        # If description exists but quantity/total are empty, try to infer or set defaults
        if description and description.strip():
            if not quantity or quantity.strip() == "":
                LOGGER.warning(f"[TABLE_EXTRACTOR] Empty quantity for item '{description[:50]}...' - cell_data: {cell_data}")
                # Try to extract quantity from cell_data if available
                for key, value in cell_data.items():
                    if value and isinstance(value, str):
                        # Look for numeric patterns in cell values
                        qty_match = re.search(r'(\d+\.?\d*)', value)
                        if qty_match and float(qty_match.group(1)) <= 1000:  # Reasonable quantity
                            quantity = qty_match.group(1)
                            LOGGER.info(f"[TABLE_EXTRACTOR] Inferred quantity '{quantity}' from cell_data[{key}]='{value}'")
                            break
                # If still empty, default to "1" for items with description
                if not quantity or quantity.strip() == "":
                    quantity = "1"
                    LOGGER.info(f"[TABLE_EXTRACTOR] Defaulting quantity to '1' for item '{description[:50]}...'")
            
            if not total_price or total_price.strip() == "":
                LOGGER.warning(f"[TABLE_EXTRACTOR] Empty total_price for item '{description[:50]}...' - cell_data: {cell_data}")
                # Try to extract price from cell_data if available
                for key, value in cell_data.items():
                    if value and isinstance(value, str):
                        # Look for price patterns in cell values
                        # Match currency symbols or decimal numbers
                        price_match = re.search(r'[£$€]?\s*(\d+\.?\d*)', value.replace(',', ''))
                        if price_match:
                            total_price = price_match.group(1)
                            LOGGER.info(f"[TABLE_EXTRACTOR] Inferred total_price '{total_price}' from cell_data[{key}]='{value}'")
                            break
                # If still empty and we have unit_price and quantity, calculate total
                if (not total_price or total_price.strip() == "") and unit_price and quantity:
                    try:
                        unit_val = float(str(unit_price).replace('£', '').replace('$', '').replace('€', '').replace(',', '').strip())
                        qty_val = float(str(quantity).replace(',', '').strip())
                        if unit_val > 0 and qty_val > 0:
                            total_price = f"{unit_val * qty_val:.2f}"
                            LOGGER.info(f"[TABLE_EXTRACTOR] Calculated total_price '{total_price}' = {qty_val} × {unit_val}")
                    except (ValueError, AttributeError):
                        pass
        
        # Ensure cell_data contains the final values
        cell_data.setdefault("raw_quantity", quantity)
        cell_data.setdefault("raw_unit_price", unit_price)
        cell_data.setdefault("raw_total_price", total_price)
        
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
    
    def _fallback_line_grouping_spatial(self, image: np.ndarray, ocr_blocks: List[Dict[str, Any]], is_receipt_mode: bool = False) -> List[LineItem]:
        """
        Spatial-aware fallback using word positions from OCR blocks.
        This is the ARCHITECTURAL WIN - we use X/Y coordinates to identify columns.
        
        Args:
            image: Table image (for reference)
            ocr_blocks: List of OCR word blocks with bbox and text
            
        Returns:
            List of LineItem objects
        """
        LOGGER.info("[SPATIAL_FALLBACK] Using spatial-aware line grouping")
        
        if not ocr_blocks:
            LOGGER.warning("[SPATIAL_FALLBACK] No OCR blocks provided")
            return []
        
        # Extract words with positions
        words_with_positions = []
        for block in ocr_blocks:
            text = block.get('text', '')
            bbox = block.get('bbox', [0, 0, 0, 0])
            if len(bbox) >= 4:
                x, y, w, h = bbox[0], bbox[1], bbox[2], bbox[3]
                x_center = x + w // 2
                y_center = y + h // 2
                words_with_positions.append((text, x_center, y_center))
        
        # Cluster columns by X-position (get boundaries)
        # Pass receipt mode flag to relax gap_threshold for tight receipt columns
        column_boundaries_result = self._cluster_columns_by_x_position_with_profiling(words_with_positions, is_receipt_mode=is_receipt_mode)
        
        if not column_boundaries_result:
            # Fallback to text-based parsing if clustering fails
            LOGGER.warning("[SPATIAL_FALLBACK] Column clustering failed, falling back to text-based parsing")
            ocr_text = "\n".join([block.get('text', '') for block in ocr_blocks])
            return self._fallback_line_grouping(image, ocr_text)
        
        column_boundaries, column_roles = column_boundaries_result
        
        # Group words into rows by Y-position
        image_height = max([y for _, _, y in words_with_positions]) - min([y for _, _, y in words_with_positions]) if words_with_positions else 1000
        y_tolerance = max(20, int(image_height * 0.01))
        LOGGER.debug(f"[SPATIAL_FALLBACK] Image height: {image_height}px, y_tolerance: {y_tolerance}px")
        
        rows_dict = defaultdict(list)
        
        for text, x, y in words_with_positions:
            # Find or create row
            row_key = None
            for existing_y in rows_dict.keys():
                if abs(y - existing_y) <= y_tolerance:
                    row_key = existing_y
                    break
            
            if row_key is None:
                row_key = y
            
            # Assign word to column INDEX (not role yet)
            col_idx = self._assign_word_to_column_by_index(x, column_boundaries)
            rows_dict[row_key].append((text, x, y, col_idx))
        
        # Sort rows by Y-position (top to bottom)
        sorted_rows = sorted(rows_dict.items(), key=lambda item: item[0])
        
        # Parse each row into a line item
        line_items = []
        for row_y, words in sorted_rows:
            # Group words by column INDEX and preserve positions
            columns_by_index = defaultdict(list)
            word_positions = defaultdict(list)  # Track positions for bbox calculation
            
            for text, x, y, col_idx in words:
                if col_idx >= 0:
                    columns_by_index[col_idx].append(text)
                    # Store word position for bbox calculation
                    word_positions[col_idx].append({'text': text, 'bbox': [x - 10, y - 10, len(text) * 12, 20]})
            
            # Map column indices to roles
            columns_data = {}
            for col_idx, col_words in columns_by_index.items():
                role = column_roles.get(col_idx, 'unknown')
                if role not in columns_data:
                    columns_data[role] = []
                columns_data[role].extend(col_words)
            
            # DEBUG: Log what we found in each column for this row
            LOGGER.debug(f"[SPATIAL_FALLBACK] Row at Y={row_y}: columns={dict(columns_data)}")
            
            # Extract fields
            description = " ".join(columns_data.get("description", []))
            
            # CRITICAL: Also capture any words in "unknown" column (likely description overflow)
            unknown_words = columns_data.get("unknown", [])
            if unknown_words:
                # Check if these are text words (not numbers)
                text_words = [w for w in unknown_words if not re.match(r'^[\d.,£$€]+$', w)]
                if text_words:
                    if description:
                        description = description + " " + " ".join(text_words)
                    else:
                        description = " ".join(text_words)
                    LOGGER.debug(f"[SPATIAL_FALLBACK] Added unknown words to description: {text_words}")
            
            # Try to parse qty and pack size from description
            pack_size = None
            parsed_qty, parsed_pack_size, cleaned_desc = self.parse_qty_and_pack_size(description)
            if parsed_qty is not None:
                # Update description with cleaned version (without qty/pack-size)
                description = cleaned_desc
                pack_size = parsed_pack_size
                # If quantity wasn't set from columns, use parsed quantity
                if not quantity:
                    quantity = str(parsed_qty)
            
            # For quantity, unit_price, total - take the first numeric value in each column
            qty_words = columns_data.get("qty", [])
            quantity = ""
            for word in qty_words:
                if re.search(r'^\d+\.?\d*$', word):
                    quantity = word
                    break
            
            unit_price_words = columns_data.get("unit_price", [])
            unit_price = ""
            for word in unit_price_words:
                if re.search(r'[\d,]+\.?\d*', word):
                    unit_price = word
                    break
            
            total_words = columns_data.get("total", [])
            total_price = ""
            for word in total_words:
                if re.search(r'[\d,]+\.?\d*', word):
                    total_price = word
                    break
            
            # Handle case where we only have qty_or_unit and total
            if not quantity and not unit_price:
                qty_or_unit_words = columns_data.get("qty_or_unit", [])
                for word in qty_or_unit_words:
                    if re.search(r'^\d+$', word):  # Integer = quantity
                        quantity = word
                    elif re.search(r'[\d,]+\.\d+', word):  # Decimal = unit price
                        unit_price = word
            
            # CRITICAL FIX: Calculate unit price from total/qty if missing
            # This prevents £0.00 unit prices in the UI when we have valid qty and total
            if (not unit_price or unit_price == "0" or unit_price == "0.00") and total_price and quantity:
                try:
                    # Robust price cleaning function
                    def clean_price(price_str):
                        """Remove currency symbols and parse to float."""
                        if not price_str:
                            return 0.0
                        cleaned = str(price_str).replace('£', '').replace('€', '').replace('$', '').replace('Â£', '').replace(',', '').strip()
                        return float(cleaned) if cleaned else 0.0
                    
                    # Clean and parse values
                    total_val = clean_price(total_price)
                    qty_val = clean_price(quantity)  # Also clean quantity (may have commas)
                    
                    if qty_val > 0 and total_val > 0:
                        calculated_unit = total_val / qty_val
                        unit_price = f"{calculated_unit:.2f}"
                        LOGGER.info(f"[SPATIAL_FALLBACK] Calculated unit price: {total_price} / {quantity} = £{unit_price}")
                    else:
                        LOGGER.debug(f"[SPATIAL_FALLBACK] Invalid values for calculation: total={total_val}, qty={qty_val}")
                except (ValueError, ZeroDivisionError, TypeError) as e:
                    LOGGER.warning(f"[SPATIAL_FALLBACK] Could not calculate unit price: {e} (total='{total_price}', qty='{quantity}')")
                    pass
            
            # Validation: must have description and at least one price
            if not description or (not unit_price and not total_price):
                continue
            
            # Skip if description is too short or doesn't contain letters
            if len(description) < 5 or not re.search(r'[A-Za-z]', description):
                continue
            
            # Ensure quantity and total_price are not empty strings - default to "0" if empty for better parsing
            if not quantity or quantity.strip() == "":
                LOGGER.warning(f"[SPATIAL_FALLBACK] Empty quantity extracted for '{description[:50]}...' - columns_data: {columns_data}")
                quantity = "0"  # Set to "0" so parsing functions can handle it
            if not total_price or total_price.strip() == "":
                LOGGER.warning(f"[SPATIAL_FALLBACK] Empty total_price extracted for '{description[:50]}...' - columns_data: {columns_data}")
                total_price = "0"  # Set to "0" so parsing functions can handle it
            
            # Calculate confidence
            found_fields = sum(1 for field in [description, quantity, unit_price, total_price] if field)
            confidence = min(0.95, 0.4 + (found_fields * 0.15))
            
            # Calculate union bounding box for the entire row
            all_word_blocks = []
            for col_idx in columns_by_index.keys():
                if col_idx in word_positions:
                    all_word_blocks.extend(word_positions[col_idx])
            
            row_bbox = self._calculate_union_bbox(all_word_blocks) if all_word_blocks else None
            
            # Ensure cell_data contains raw values for debugging
            cell_data_dict = {
                "spatial_method": True,
                "row_y": row_y,
                "raw_quantity": quantity,
                "raw_unit_price": unit_price,
                "raw_total_price": total_price,
                "columns_data": columns_data  # Include full columns_data for debugging
            }
            
            line_item = LineItem(
                description=description,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price,
                vat="",
                confidence=confidence,
                row_index=len(line_items),
                cell_data=cell_data_dict,
                pack_size=pack_size,  # Include pack size if found
                bbox=row_bbox  # ← NEW: Include bounding box for visual verification
            )
            
            line_items.append(line_item)
            LOGGER.info(f"[SPATIAL_FALLBACK] Extracted item {len(line_items)}: {description[:50]}... (qty={quantity}, unit={unit_price}, total={total_price})")
        
        LOGGER.info(f"[SPATIAL_FALLBACK] Extracted {len(line_items)} line items using spatial clustering")
        return line_items
    
    def _extract_by_row_patterns(self, ocr_text: str, is_receipt_mode: bool = False) -> List[LineItem]:
        """
        WORLD CLASS: Semantic row-pattern extraction.
        Ignores column boundaries - uses aggressive regex to parse each line.
        This handles cases where columns are merged or too tight for geometric clustering.
        
        Args:
            ocr_text: Raw OCR text (line-separated)
            
        Returns:
            List of LineItem objects extracted using semantic patterns
        """
        LOGGER.info("[ROW_PATTERNS] Using semantic row-pattern extraction")
        
        lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]
        line_items = []
        
        # Find line items section (between header and summary)
        start_idx = -1
        end_idx = len(lines)
        header_keywords = ['product', 'item', 'description', 'qty', 'quantity', 'rate', 'price', 'amount']
        summary_keywords = ['subtotal', 'sub-total', 'vat total', 'grand total', 'total', 'balance due', 'amount due']
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Find start
            if start_idx == -1:
                header_count = sum(1 for kw in header_keywords if kw in line_lower)
                if header_count >= 2:
                    start_idx = i + 1
                    LOGGER.info(f"[ROW_PATTERNS] Found line items section starting at line {start_idx}")
            
            # Find end
            if start_idx != -1:
                for kw in summary_keywords:
                    if line_lower.startswith(kw) or line_lower == kw:
                        end_idx = i
                        LOGGER.info(f"[ROW_PATTERNS] Found line items section ending at line {end_idx}")
                        break
                if end_idx < len(lines):
                    break
        
        # Extract section
        if start_idx != -1 and end_idx > start_idx:
            lines = lines[start_idx:end_idx]
            LOGGER.info(f"[ROW_PATTERNS] Processing {len(lines)} lines in items section")
        
        # Handle wraparound text for receipts (Line 1: Description, Line 2: Price)
        # This is common in narrow receipt layouts
        if is_receipt_mode:
            processed_lines = []
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # Check if current line is price-only and previous line was description
                if i > 0:
                    prev_line = lines[i - 1]
                    # If current line is just a price and previous line has text
                    if re.match(r'^[\s]*[£$€]?\s*[\d,]+\.\d{2}\s*[A-Z]?$', line.strip()):
                        if re.search(r'[A-Za-z]', prev_line) and not re.match(r'^[\d\s.,£$€%]+$', prev_line):
                            # Merge: description from prev_line + price from current line
                            merged_line = f"{prev_line.strip()} {line.strip()}"
                            processed_lines[-1] = merged_line  # Replace previous line
                            i += 1
                            continue
                
                processed_lines.append(line)
                i += 1
            
            lines = processed_lines
            if len(lines) != len(lines[start_idx:end_idx] if start_idx != -1 else []):
                LOGGER.info(f"[ROW_PATTERNS] Merged wraparound text: {len(lines)} lines after merging")
        
        # Battery of aggressive regex patterns
        # Add receipt-specific patterns if in receipt mode
        patterns = [
            # Pattern A: Qty First (Red Dragon format)
            # Example: "6  12 LITTRE PEPSI  78.49"
            (r'^\s*(\d{1,4})\s+(.+?)\s+([£$€]?\s*[\d,]+\.?\d{0,4})\s*$', 'qty_first'),
            
            # Pattern B: Qty Middle (with unit price and total)
            # Example: "PEPSI COLA  12  4.50  54.00"
            (r'^(.+?)\s+(\d{1,4})\s+([£$€]?\s*[\d,]+\.?\d{0,4})\s+([£$€]?\s*[\d,]+\.?\d{0,4})\s*$', 'qty_middle_full'),
            
            # Pattern C: Description First with Qty and Price
            # Example: "CRATE OF BEER  12  78.49"
            (r'^(.+?)\s+(\d{1,4})\s+([£$€]?\s*[\d,]+\.?\d{0,4})\s*$', 'desc_qty_price'),
            
            # Pattern D: Implicit Qty (Description and Price only)
            # Example: "DELIVERY CHARGE  15.00"
            (r'^(.+?)\s+([£$€]?\s*[\d,]+\.?\d{0,4})\s*$', 'desc_price_only'),
        ]
        
        # RECEIPT PATTERNS: Add specialized patterns for narrow receipt layouts
        if is_receipt_mode:
            LOGGER.info("[ROW_PATTERNS] Adding receipt-specific patterns")
            receipt_patterns = [
                # Receipt Pattern 1: Description + Price (implied Qty=1) - Enhanced for UK receipts
                # Example: "MILK 1.20" or "BREAD £1.20" or "MILK 2.50"
                # Handles both comma and period decimal separators: "1,20" or "1.20"
                (r'^(.+?)\s+([£$€]?\s*[\d,]+[.,]\d{2})\s*[A-Z]?$', 'receipt_desc_price'),
                
                # Receipt Pattern 2: Description with optional VAT code
                # Example: "COFFEE 3.50 S" (S = Standard rate)
                (r'^(.+?)\s+([£$€]?\s*[\d,]+[.,]\d{2})\s*([A-Z]|VAT)?$', 'receipt_desc_price_vat'),
                
                # Receipt Pattern 3: Simple description + price (no currency symbol)
                # Example: "MILK 1.20" - matches user's requested pattern exactly
                (r'^(.+?)\s+([£$€]?\d+[.,]\d{2})$', 'receipt_desc_price_simple'),
                
                # Receipt Pattern 4: Wraparound text (Line 1: Description, Line 2: Price)
                # This is handled by checking if current line is price-only and previous was description
            ]
            # Insert receipt patterns at the beginning (higher priority)
            patterns = receipt_patterns + patterns
        
        for line in lines:
            # Skip very short lines
            if len(line) < 5:
                continue
            
            # Skip lines that are just numbers
            if re.match(r'^[\d\s.,£$€%]+$', line):
                continue
            
            # Try each pattern
            matched = False
            for pattern, pattern_type in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    description = ""
                    quantity = ""
                    unit_price = ""
                    total_price = ""
                    
                    if pattern_type == 'qty_first':
                        # Pattern A: Qty First
                        quantity = match.group(1)
                        description_raw = match.group(2).strip()
                        total_price = match.group(3).replace('£', '').replace('$', '').replace('€', '').replace(',', '').strip()
                        
                        # Try to parse qty and pack size from description
                        parsed_qty, parsed_pack_size, cleaned_desc = self.parse_qty_and_pack_size(description_raw)
                        if parsed_qty is not None:
                            # If we found a qty in the description, use it (might be more accurate)
                            # But keep the original quantity from the pattern match
                            description = cleaned_desc
                            pack_size = parsed_pack_size
                        else:
                            description = description_raw
                            pack_size = None
                        
                    elif pattern_type == 'qty_middle_full':
                        # Pattern B: Desc Qty Unit Total
                        description = match.group(1).strip()
                        quantity = match.group(2)
                        unit_price = match.group(3).replace('£', '').replace('$', '').replace('€', '').replace(',', '').strip()
                        total_price = match.group(4).replace('£', '').replace('$', '').replace('€', '').replace(',', '').strip()
                        
                    elif pattern_type == 'desc_qty_price':
                        # Pattern C: Desc Qty Price
                        description = match.group(1).strip()
                        quantity = match.group(2)
                        total_price = match.group(3).replace('£', '').replace('$', '').replace('€', '').replace(',', '').strip()
                        
                    elif pattern_type == 'desc_price_only':
                        # Pattern D: Desc Price (implicit qty=1)
                        description = match.group(1).strip()
                        quantity = "1"
                        total_price = match.group(2).replace('£', '').replace('$', '').replace('€', '').replace(',', '').strip()
                    
                    elif pattern_type == 'receipt_desc_price':
                        # Receipt Pattern 1: Description + Price (implied Qty=1)
                        description = match.group(1).strip()
                        quantity = "1"
                        total_price = match.group(2).replace('£', '').replace('$', '').replace('€', '').replace(',', '').strip()
                    
                    elif pattern_type == 'receipt_desc_price_vat':
                        # Receipt Pattern 2: Description + Price + optional VAT code
                        description = match.group(1).strip()
                        quantity = "1"
                        total_price = match.group(2).replace('£', '').replace('$', '').replace('€', '').replace(',', '.').strip()
                        # VAT code in match.group(3) - can be stored in vat field if needed
                    
                    elif pattern_type == 'receipt_desc_price_simple':
                        # Receipt Pattern 3: Simple description + price (no currency symbol)
                        # Example: "MILK 1.20" - matches user's requested pattern exactly
                        description = match.group(1).strip()
                        quantity = "1"
                        # Handle both comma and period decimal separators
                        price_str = match.group(2).replace(',', '.').strip()
                        total_price = price_str
                    
                    # Validate description has letters
                    if not re.search(r'[A-Za-z]', description):
                        continue
                    
                    # Validate description is substantial
                    if len(description) < 3:
                        continue
                    
                    # Check if this is header/meta information (before creating LineItem)
                    price_value = None
                    if total_price:
                        try:
                            price_value = float(total_price.replace(',', ''))
                        except (ValueError, TypeError):
                            pass
                    
                    if self._is_header_or_meta_description(description, price_value):
                        LOGGER.debug(f"[ROW_PATTERNS] Skipping header/meta line: '{description}'")
                        continue
                    
                    # Calculate unit price if missing
                    if not unit_price and total_price and quantity:
                        try:
                            unit_val = float(total_price) / float(quantity)
                            unit_price = f"{unit_val:.2f}"
                        except (ValueError, ZeroDivisionError):
                            pass
                    
                    # Try to parse qty and pack size from description if not already done
                    if pattern_type != 'qty_first':  # Already parsed for qty_first above
                        parsed_qty, parsed_pack_size, cleaned_desc = self.parse_qty_and_pack_size(description)
                        if parsed_qty is not None:
                            # Update description with cleaned version
                            description = cleaned_desc
                            pack_size = parsed_pack_size
                            # If quantity wasn't set, use parsed quantity
                            if not quantity:
                                quantity = str(parsed_qty)
                        else:
                            pack_size = None
                    
                    # Calculate confidence based on pattern type and fields found
                    confidence_map = {
                        'qty_first': 0.85,
                        'qty_middle_full': 0.95,
                        'desc_qty_price': 0.90,
                        'desc_price_only': 0.75,
                        'receipt_desc_price': 0.80,  # Receipt patterns
                        'receipt_desc_price_vat': 0.85,
                        'receipt_desc_price_simple': 0.82,  # Simple receipt pattern
                    }
                    confidence = confidence_map.get(pattern_type, 0.70)
                    
                    # Estimate bbox for semantic extraction (we don't have exact positions)
                    # Use line index to estimate Y position
                    estimated_y = 100 + (len(line_items) * 30)  # Rough estimate
                    estimated_bbox = [50, estimated_y, 500, 25]  # Approximate row bbox
                    
                    line_item = LineItem(
                        description=description,
                        quantity=quantity,
                        unit_price=unit_price,
                        total_price=total_price,
                        vat="",
                        confidence=confidence,
                        row_index=len(line_items),
                        cell_data={"pattern": pattern_type, "raw_line": line},
                        pack_size=pack_size,  # Include pack size if found
                        bbox=estimated_bbox  # Estimated bbox for semantic extraction
                    )
                    
                    line_items.append(line_item)
                    LOGGER.info(f"[ROW_PATTERNS] Extracted item {len(line_items)} via {pattern_type}: {description[:50]}... (qty={quantity}, unit={unit_price}, total={total_price})")
                    matched = True
                    break
            
            if not matched:
                LOGGER.debug(f"[ROW_PATTERNS] No pattern matched for line: {line[:80]}")
        
        LOGGER.info(f"[ROW_PATTERNS] Extracted {len(line_items)} line items using semantic patterns")
        return line_items
    
    def _fallback_line_grouping(self, image: np.ndarray, ocr_text: str) -> List[LineItem]:
        """Fallback method using OCR text grouping when table structure detection fails."""
        LOGGER.info("Using fallback line grouping for table extraction")
        
        lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]
        line_items = []
        
        # Find the line items section (between "PRODUCT" header and "SUBTOTAL")
        start_idx = -1
        end_idx = len(lines)
        header_keywords = ['product', 'item', 'description', 'qty', 'quantity', 'rate', 'price', 'amount']
        
        # STRICT summary keywords - these lines are NEVER line items
        summary_keywords = [
            'subtotal', 'sub-total', 'sub total',
            'vat total', 'vat summary', 'vat @',
            'total', 'grand total',
            'balance due', 'balance', 'amount due',
            'net', 'gross',
            'payment', 'paid', 'owing'
        ]
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Find start (PRODUCT/QTY/RATE header row)
            if start_idx == -1:
                # Check if it's a header row (contains multiple header keywords)
                header_keyword_count = sum(1 for keyword in header_keywords if keyword in line_lower)
                if header_keyword_count >= 2:
                    start_idx = i + 1  # Start after header
                    LOGGER.info(f"[TABLE_FALLBACK] Found line items section starting at line {start_idx}")
            
            # Find end (SUBTOTAL/TOTAL) - must be after start
            if start_idx != -1:
                # Check if this line is a summary line (starts with or is exactly a summary keyword)
                is_summary = False
                for keyword in summary_keywords:
                    # Check if line starts with keyword or is just the keyword
                    if line_lower.startswith(keyword) or line_lower == keyword:
                        is_summary = True
                        break
                
                if is_summary:
                    end_idx = i
                    LOGGER.info(f"[TABLE_FALLBACK] Found line items section ending at line {end_idx} (summary: '{line[:50]}')")
                    break
        
        # If we found a section, only process lines within it
        if start_idx != -1 and end_idx > start_idx:
            original_count = len(lines)
            lines = lines[start_idx:end_idx]
            LOGGER.info(f"[TABLE_FALLBACK] Extracted line items region: lines {start_idx}-{end_idx} ({len(lines)} lines from {original_count} total)")
        else:
            LOGGER.warning(f"[TABLE_FALLBACK] No clear line items section found (start={start_idx}, end={end_idx})")
        
        # HARD exclusion list - skip lines that are clearly not line items
        # IMPORTANT: Only include EXACT phrases that would NEVER appear in product names
        # Removed generic words like 'unit', 'rate', 'description', 'product' which could be in product names
        # (e.g., "Storage Unit", "Shelving Unit", "Rate Card", "Product Display")
        exclusion_keywords = [
            # Invoice metadata (exact phrases only)
            'invoice no', 'invoice number', 'invoice to', 'invoice from', 'invoice date',
            'vat registration', 'vat registration no', 'vat registration number',
            'due date', 'payment terms', 'trade@', 'email:', 'phone:', 'tel:',
            # Company/location info (exact phrases that would never be products)
            'ltd.', 'limited.', 'plc.', 'inc.',
            # Summary lines (double-check in case section detection missed them)
            'subtotal', 'sub-total', 'sub total',
            'vat total', 'vat summary', 'vat @',
            'grand total', 'net total', 'gross total',
            'balance due', 'amount due', 'dalance due',
            'payment due', 'amount paid', 'appreciate your business',
            'bacs payment', 'bank transfer', 'sort code:', 'account number:', 'account no:'
        ]
        
        # Handle multi-line line items: group consecutive lines that form a single line item
        # Pattern: Product name on one line, then numbers (qty, rate, total) on following lines
        i = 0
        while i < len(lines):
            line = lines[i]
            line_lower = line.lower().strip()
            
            # HARD SKIP: Check if line contains any exclusion keywords
            # Use exact matching or startswith for safety (avoid false positives)
            should_skip = False
            for keyword in exclusion_keywords:
                # For short keywords, require exact match or word boundary
                if len(keyword) < 10:
                    # Check if it's the whole line or starts the line
                    if line_lower == keyword or line_lower.startswith(keyword + ' ') or line_lower.startswith(keyword + ':'):
                        LOGGER.debug(f"[TABLE_FALLBACK] Skipping line (exclusion keyword '{keyword}'): {line[:50]}")
                        should_skip = True
                        break
                else:
                    # For longer phrases, substring match is safe
                    if keyword in line_lower:
                        LOGGER.debug(f"[TABLE_FALLBACK] Skipping line (exclusion keyword '{keyword}'): {line[:50]}")
                        should_skip = True
                        break
            
            if should_skip:
                i += 1
                continue
            
            # Skip very short lines (likely OCR artifacts)
            if len(line.strip()) < 5:
                i += 1
                continue
            
            # Skip lines that are just numbers (likely misplaced column data)
            if re.match(r'^[\d\s\.,£$€%]+$', line.strip()):
                LOGGER.debug(f"[TABLE_FALLBACK] Skipping line (numbers only): {line[:50]}")
                i += 1
                continue
            
            # Skip if line is all uppercase and short (likely a section header)
            if line.isupper() and len(line.strip()) < 30:
                LOGGER.debug(f"[TABLE_FALLBACK] Skipping line (uppercase header): {line[:50]}")
                i += 1
                continue
            
            # If it's a product line, try to combine with following lines that contain numbers
            combined_line = line
            j = i + 1
            lines_combined = 1
            while j < len(lines) and j < i + 4 and lines_combined < 4:  # Look ahead up to 3 more lines (4 total)
                next_line = lines[j]
                next_line_lower = next_line.lower()
                
                # Stop if we hit a summary line
                if any(keyword in next_line_lower for keyword in summary_keywords):
                    break
                
                # If next line contains numbers (likely qty/price), include it
                if re.search(r'\d', next_line) and len(next_line.strip()) < 50:
                    combined_line += " " + next_line
                    j += 1
                    lines_combined += 1
                elif len(next_line.strip()) < 20 and not any(keyword in next_line_lower for keyword in exclusion_keywords):
                    # Short line that might be part of product name
                    combined_line += " " + next_line
                    j += 1
                    lines_combined += 1
                else:
                    break
            
            # Enhanced parsing for invoice line items
            # Pattern: Description [Qty] [Rate] [VAT%] [Total]
            # Example: "Gwynt Black Dragon case of 12 8 24.79 20.0% 5 198.32"
            # Or multi-line: "Gwynt Black Dragon case of 12." "8" "24.79" "198.32"
            
            # Extract all numbers and prices from the combined line
            # Price pattern: £X.XX or X.XX (with 2 decimal places)
            price_pattern = r'£?[\d,]+\.\d{2}'
            prices = re.findall(price_pattern, combined_line)
            
            # Quantity pattern: standalone numbers (likely quantities)
            # Look for numbers that are not prices (no decimal or different format)
            quantity_pattern = r'\b\d+\b'
            all_numbers = re.findall(quantity_pattern, combined_line)
            
            # VAT percentage pattern
            vat_pattern = r'(\d+\.?\d*)%'
            vat_matches = re.findall(vat_pattern, combined_line)
            
            description = ""
            quantity = ""
            unit_price = ""
            total_price = ""
            vat = ""
            
            # IMPROVED: Extract quantity first (should be a small integer, typically 1-999)
            potential_quantities = []
            for num in all_numbers:
                # Skip if part of a price (has .XX after it)
                if re.search(rf'\b{num}\.\d{{2}}\b', combined_line):
                    continue
                # Skip if part of VAT percentage
                if re.search(rf'\b{num}%', combined_line):
                    continue
                # Skip large numbers (likely dates, invoice numbers, etc.)
                try:
                    num_val = int(num)
                    if 1 <= num_val <= 999:  # Reasonable quantity range
                        potential_quantities.append(num)
                except ValueError:
                    continue
            
            if potential_quantities:
                # First reasonable number is likely the quantity
                quantity = potential_quantities[0]
            
            # IMPROVED: Extract prices with better logic
            if prices:
                # Clean prices (remove £ and commas)
                clean_prices = [p.replace('£', '').replace(',', '').replace('$', '').replace('€', '') for p in prices]
                
                if len(clean_prices) >= 2:
                    # Multiple prices: likely unit price and line total
                    # Typically: smaller value = unit price, larger = total
                    try:
                        price_values = [float(p) for p in clean_prices]
                        # Sort to find unit price (smaller) and total (larger)
                        sorted_prices = sorted(zip(price_values, clean_prices))
                        unit_price = sorted_prices[0][1]  # Smallest
                        total_price = sorted_prices[-1][1]  # Largest
                    except ValueError:
                        # Fallback: first is unit, last is total
                        unit_price = clean_prices[0]
                        total_price = clean_prices[-1]
                        
                elif len(clean_prices) == 1:
                    # Only one price: treat as line total
                    total_price = clean_prices[0]
                    # Try to derive unit price from total / quantity
                    if quantity and total_price:
                        try:
                            qty_val = float(quantity)
                            total_val = float(total_price)
                            if qty_val > 0:
                                unit_price = f"{total_val / qty_val:.2f}"
                        except (ValueError, ZeroDivisionError):
                            pass
            
            # Extract VAT
            if vat_matches:
                vat = f"{vat_matches[0]}%"
            
            # Extract description (everything except prices, quantities, VAT)
            # Remove prices, quantities, and VAT from the combined line
            description_line = combined_line
            for price in prices:
                description_line = description_line.replace(price, '', 1)
            for num in all_numbers[:3]:  # Remove first few numbers (likely qty/rate)
                description_line = re.sub(rf'\b{num}\b', '', description_line, count=1)
            if vat:
                description_line = description_line.replace(vat, '')
            
            # Clean up description
            description = ' '.join(description_line.split()).strip()
            
            # VALIDATION: Must have description and at least one price
            if not description or (not unit_price and not total_price):
                LOGGER.debug(f"[TABLE_FALLBACK] Skipping row (no description or price): desc='{description[:30] if description else ''}', unit={unit_price}, total={total_price}")
                i = j  # Skip to after the combined lines
                continue
            
            # VALIDATION: Description must contain letters (not just numbers/symbols)
            if not re.search(r'[A-Za-z]', description):
                LOGGER.debug(f"[TABLE_FALLBACK] Skipping row (no letters in description): {description[:50]}")
                i = j
                continue
            
            # VALIDATION: Description must be substantial
            if len(description.strip()) < 5:
                LOGGER.debug(f"[TABLE_FALLBACK] Skipping row (description too short): {description}")
                i = j
                continue
            
            # VALIDATION: Skip if description matches common non-item text
            desc_upper = description.upper().strip()
            if desc_upper in ['PRODUCT', 'QTY', 'RATE', 'AMOUNT', 'VAT', 'TOTAL', 'SUBTOTAL', 'DESCRIPTION', 'ITEM']:
                LOGGER.debug(f"[TABLE_FALLBACK] Skipping row (header text): {description}")
                i = j
                continue
            
            # VALIDATION: Quantity should be reasonable if present
            if quantity:
                try:
                    qty_val = float(quantity)
                    if qty_val <= 0 or qty_val > 9999:
                        # CHANGED: Instead of skipping, cap extreme quantities
                        if qty_val > 9999:
                            quantity = "1"  # Cap to safe value
                            LOGGER.warning(f"[TABLE_FALLBACK] Capped unreasonable quantity {qty_val} to 1: {description[:50]}")
                        # Continue processing (don't skip)
                    else:
                        # Quantity is reasonable, continue
                        pass
                except ValueError:
                    pass  # Keep the row even if quantity is non-numeric
            
            # VALIDATION: Prices should be reasonable
            if unit_price:
                try:
                    price_val = float(unit_price)
                    if price_val < 0 or price_val > 999999:
                        LOGGER.debug(f"[TABLE_FALLBACK] Skipping row (unreasonable unit price {price_val}): {description[:50]}")
                        i = j
                        continue
                except ValueError:
                    pass
            
            if total_price:
                try:
                    total_val = float(total_price)
                    if total_val < 0 or total_val > 999999:
                        LOGGER.debug(f"[TABLE_FALLBACK] Skipping row (unreasonable total {total_val}): {description[:50]}")
                        i = j
                        continue
                except ValueError:
                    pass
            
            # Calculate confidence based on fields found
            found_fields = sum(1 for field in [description, quantity, unit_price, total_price] if field)
            confidence = min(0.9, 0.3 + (found_fields * 0.15))  # Base 0.3, +0.15 per field
            
            line_item = LineItem(
                description=description,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price,
                vat=vat,
                confidence=confidence,
                row_index=len(line_items),
                cell_data={"raw_line": combined_line, "prices_found": len(prices), "numbers_found": len(all_numbers)}
            )
            
            line_items.append(line_item)
            LOGGER.info(f"[TABLE_FALLBACK] Extracted line item {len(line_items)}: {description[:50]}... (qty={quantity}, price={unit_price}, total={total_price})")
            
            # Move to after the combined lines
            i = j
        
        LOGGER.info(f"[TABLE_FALLBACK] Extracted {len(line_items)} line items from {len(lines)} lines")
        return line_items
    
    def extract_table(self, image: np.ndarray, bbox: Tuple[int, int, int, int], 
                     ocr_text: str = "", ocr_blocks: Optional[List[Dict[str, Any]]] = None) -> TableResult:
        """Extract table structure and line items from a table block."""
        start_time = time.time()
        
        # Diagnostic logging
        LOGGER.info(f"[TABLE_DETECT] Input: bbox={bbox}, image_shape={image.shape if image is not None else 'None'}")
        
        x, y, w, h = bbox
        table_img = image[y:y+h, x:x+w]
        
        # Detect "Receipt Mode" - tall/narrow aspect ratio (Height > 2.0 * Width)
        # Receipts are typically narrow strips with tight columns
        # Lowered threshold from 2.5 to 2.0 to catch more receipt-like documents
        img_h, img_w = table_img.shape[:2] if len(table_img.shape) == 2 else table_img.shape[:2]
        aspect_ratio = img_h / img_w if img_w > 0 else 1.0
        is_receipt_mode = aspect_ratio > 2.0
        
        if is_receipt_mode:
            LOGGER.info(f"[TABLE_DETECT] Receipt Mode detected (aspect_ratio={aspect_ratio:.2f}, H={img_h}, W={img_w})")
        
        if table_img.size == 0:
            LOGGER.warning("[TABLE_DETECT] Empty table image provided (size=0)")
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
        
        LOGGER.info(f"[TABLE_DETECT] Table image extracted: {table_img.shape}, size={table_img.size/1e6:.2f}MB")
        
        try:
            # HYBRID PIPELINE: Try both geometric and semantic, use best result
            spatial_result = None
            semantic_result = None
            
            # PRIORITY 1: Try spatial clustering (geometric)
            # For receipts, use relaxed gap_threshold (columns are tight)
            if ocr_blocks and len(ocr_blocks) > 5:
                LOGGER.info(f"[TABLE_DETECT] OCR blocks available ({len(ocr_blocks)} blocks), trying spatial clustering")
                try:
                    # Pass receipt mode flag to spatial clustering
                    spatial_items = self._fallback_line_grouping_spatial(table_img, ocr_blocks, is_receipt_mode=is_receipt_mode)
                    spatial_conf = sum(item.confidence for item in spatial_items) / len(spatial_items) if spatial_items else 0.0
                    spatial_result = (spatial_items, spatial_conf, "spatial_clustering")
                    LOGGER.info(f"[TABLE_DETECT] Spatial clustering: {len(spatial_items)} items, conf={spatial_conf:.3f}")
                except Exception as e:
                    LOGGER.warning(f"[TABLE_DETECT] Spatial clustering failed: {e}")
            
            # PRIORITY 2: Try semantic row patterns (robust fallback)
            # Receipts benefit from specialized patterns
            if ocr_text and len(ocr_text.strip()) > 50:
                LOGGER.info(f"[TABLE_DETECT] OCR text available ({len(ocr_text)} chars), trying semantic patterns")
                try:
                    semantic_items = self._extract_by_row_patterns(ocr_text, is_receipt_mode=is_receipt_mode)
                    semantic_conf = sum(item.confidence for item in semantic_items) / len(semantic_items) if semantic_items else 0.0
                    semantic_result = (semantic_items, semantic_conf, "semantic_row_patterns")
                    LOGGER.info(f"[TABLE_DETECT] Semantic patterns: {len(semantic_items)} items, conf={semantic_conf:.3f}")
                except Exception as e:
                    LOGGER.warning(f"[TABLE_DETECT] Semantic pattern extraction failed: {e}")
            
            # THE "MAX" LOGIC: Choose best result
            chosen_result = None
            
            if spatial_result and semantic_result:
                spatial_items, spatial_conf, spatial_method = spatial_result
                semantic_items, semantic_conf, semantic_method = semantic_result
                
                # Use spatial if it has good results (>= 2 items, conf > 0.5)
                if len(spatial_items) >= 2 and spatial_conf > 0.5:
                    chosen_result = spatial_result
                    LOGGER.info(f"[TABLE_DETECT] MAX LOGIC: Using spatial (items={len(spatial_items)}, conf={spatial_conf:.3f})")
                # Otherwise use semantic if it has results
                elif len(semantic_items) >= 1:
                    chosen_result = semantic_result
                    LOGGER.info(f"[TABLE_DETECT] MAX LOGIC: Using semantic (items={len(semantic_items)}, conf={semantic_conf:.3f})")
                # Fallback to whichever has more items
                else:
                    chosen_result = spatial_result if len(spatial_items) >= len(semantic_items) else semantic_result
                    LOGGER.info(f"[TABLE_DETECT] MAX LOGIC: Using fallback (spatial={len(spatial_items)}, semantic={len(semantic_items)})")
            
            elif spatial_result:
                chosen_result = spatial_result
                LOGGER.info(f"[TABLE_DETECT] Using spatial (only option)")
            elif semantic_result:
                chosen_result = semantic_result
                LOGGER.info(f"[TABLE_DETECT] Using semantic (only option)")
            
            if chosen_result:
                line_items, avg_confidence, method_used = chosen_result
                processing_time = time.time() - start_time
                
                result = TableResult(
                    type="table",
                    bbox=bbox,
                    line_items=line_items,
                    confidence=avg_confidence,
                    method_used=method_used,
                    processing_time=processing_time,
                    fallback_used=(method_used != "spatial_clustering"),
                    cell_count=len(ocr_blocks) if ocr_blocks else 0,
                    row_count=len(line_items)
                )
                
                LOGGER.info(f"[TABLE_DETECT] Final result: {len(line_items)} items, method={method_used}, conf={avg_confidence:.3f}")
                return result
            
            # PRIORITY 2: If we have OCR text, use text-based parsing
            elif ocr_text and len(ocr_text.strip()) > 50:  # Substantial OCR text available
                LOGGER.info(f"[TABLE_DETECT] OCR text available ({len(ocr_text)} chars), using text-based parsing")
                line_items = self._fallback_line_grouping(table_img, ocr_text)
                
                processing_time = time.time() - start_time
                avg_confidence = sum(item.confidence for item in line_items) / len(line_items) if line_items else 0.0
                
                result = TableResult(
                    type="table",
                    bbox=bbox,
                    line_items=line_items,
                    confidence=avg_confidence,
                    method_used="text_based_parsing",
                    processing_time=processing_time,
                    fallback_used=False,
                    cell_count=0,
                    row_count=len(line_items)
                )
                
                LOGGER.info("Text-based extraction: %d line items, %.3f confidence", 
                           len(line_items), avg_confidence)
                
                return result
            
            # Try structure-aware extraction first (fallback if no OCR text)
            LOGGER.info(f"[TABLE_DETECT] Attempting structure-aware extraction...")
            cells, structure_detected = self._detect_table_structure(table_img)
            LOGGER.info(f"[TABLE_DETECT] Structure detected: {structure_detected}, cells found: {len(cells) if cells else 0}")
            
            if structure_detected and cells and len(cells) >= 4:  # Need at least 4 cells for a valid table
                LOGGER.info(f"[TABLE_DETECT] Using structure-aware extraction with {len(cells)} cells")
                
                # Extract text from each cell
                cell_texts = []
                for cell_bbox in cells:
                    text, confidence = self._extract_cell_text(table_img, cell_bbox)
                    cell_texts.append(text)
                
                # Group cells into rows
                rows = self._group_cells_into_rows(cells, cell_texts)
                
                # Parse each row into line items
                line_items = []
                LOGGER.info(f"[TABLE_DETECT] Parsing {len(rows)} rows into line items...")
                for i, row_cells in enumerate(rows):
                    if len(row_cells) > 0:  # Skip empty rows
                        line_item = self._parse_line_item(row_cells, i)
                        line_items.append(line_item)
                LOGGER.info(f"[TABLE_DETECT] Extracted {len(line_items)} line items from structure-aware method")
                
                # If structure-aware found very few items, fall back to text parsing
                if len(line_items) < 2 and ocr_text:
                    LOGGER.info(f"[TABLE_DETECT] Structure-aware found only {len(line_items)} items, falling back to text parsing")
                    line_items = self._fallback_line_grouping(table_img, ocr_text)
                    method_used = "structure_aware_with_fallback"
                    fallback_used = True
                else:
                    method_used = "structure_aware"
                    fallback_used = False
                
                processing_time = time.time() - start_time
                avg_confidence = sum(item.confidence for item in line_items) / len(line_items) if line_items else 0.0
                
                result = TableResult(
                    type="table",
                    bbox=bbox,
                    line_items=line_items,
                    confidence=avg_confidence,
                    method_used=method_used,
                    processing_time=processing_time,
                    fallback_used=fallback_used,
                    cell_count=len(cells),
                    row_count=len(line_items)
                )
                
                LOGGER.info("Structure-aware extraction: %d line items, %.3f confidence", 
                           len(line_items), avg_confidence)
                
                return result
            
            else:
                # Fallback to line grouping (structure detection failed or found too few cells)
                if not structure_detected:
                    LOGGER.info("Structure detection failed, using fallback line grouping")
                else:
                    LOGGER.info(f"Structure detection found only {len(cells)} cells (need >=4), using fallback line grouping")
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
    
    def _fuzzy_reconstruct_line(self, line: str) -> str:
        """
        PHASE 5 - Module B: Aggressive fuzzy line reconstruction.
        
        Handles merged tokens, broken spacing, and fused symbols common in messy OCR.
        
        Args:
            line: Raw OCR line text
            
        Returns:
            Reconstructed line with proper spacing and separated tokens
        """
        if not line or len(line) < 3:
            return line
        
        reconstructed = line
        
        # 1. Regex fuzzing: Fix common merged patterns
        
        # Pattern 1: Number followed by uppercase word (e.g., "6PEPSI" → "6 PEPSI")
        # Matches: "6PEPSI", "12LITRE", "24COKE"
        reconstructed = re.sub(r'(\d+)([A-Z][a-z]+)', r'\1 \2', reconstructed)
        
        # Pattern 2: Lowercase letter followed by number (e.g., "L12" → "L 12")
        # Matches: "L12", "x24", "G30"
        reconstructed = re.sub(r'([a-z])(\d+)', r'\1 \2', reconstructed, flags=re.IGNORECASE)
        
        # Pattern 3: Two prices merged together (e.g., "69.3169.31" → "69.31 69.31")
        # This is handled in _extract_prices_from_line_end, but we can also fix it here
        reconstructed = re.sub(r'(\d{2,3}\.\d{2})(\d{2,3}\.\d{2})', r'\1 \2', reconstructed)
        
        # Pattern 4: Number followed by hyphenated word (e.g., "6PEPSIMAX-12L" → "6 PEPSIMAX-12L")
        reconstructed = re.sub(r'(\d+)([A-Z][a-z]+-[A-Za-z0-9]+)', r'\1 \2', reconstructed)
        
        # Pattern 5: Word followed by number without space (e.g., "PEPSI12L" → "PEPSI 12L")
        reconstructed = re.sub(r'([A-Za-z]+)(\d+[A-Za-z]*)', r'\1 \2', reconstructed)
        
        # 2. Character window scanning: Handle fused symbols and broken prices
        # Scan for patterns like "CC' S94 '7." → extract "94.7" or "7.00"
        # This is more complex and handled during price extraction, but we can fix spacing here
        
        # Fix spacing around quotes and special chars that might fuse with numbers
        reconstructed = re.sub(r"([A-Za-z])'(\s*)([A-Za-z0-9])", r"\1' \3", reconstructed)
        reconstructed = re.sub(r"([A-Za-z0-9])(\s*)'([A-Za-z])", r"\1 ' \3", reconstructed)
        
        # Fix spacing around dots that might be decimal points
        # Pattern: letter/number followed by dot followed by number (potential decimal)
        reconstructed = re.sub(r'([A-Za-z])(\.)(\d)', r'\1 \2\3', reconstructed)
        
        # 3. Token re-segmentation: Split tokens on case boundaries and digit boundaries
        
        # Split on case boundaries within words (e.g., "PEPSIMAX" → "PEPSI MAX")
        # Only if the word is all caps and longer than 5 chars
        def split_case_boundary(match):
            word = match.group(0)
            if len(word) > 5 and word.isupper():
                # Find case boundaries (but preserve common abbreviations)
                # Simple heuristic: split if we have 2+ consecutive uppercase letters followed by more
                parts = re.findall(r'[A-Z][a-z]*|[A-Z]+', word)
                if len(parts) > 1:
                    return ' '.join(parts)
            return word
        
        reconstructed = re.sub(r'\b[A-Z]{4,}\b', split_case_boundary, reconstructed)
        
        # Split on digit boundaries within words (e.g., "12Lpink" → "12L pink")
        # Pattern: number+letter followed by lowercase letters
        reconstructed = re.sub(r'(\d+[A-Za-z]+)([a-z]{2,})', r'\1 \2', reconstructed)
        
        # Normalize multiple spaces to single space
        reconstructed = re.sub(r'\s+', ' ', reconstructed).strip()
        
        if reconstructed != line:
            LOGGER.debug(f"[FUZZY_RECONSTRUCT] Reconstructed line: '{line[:60]}' → '{reconstructed[:60]}'")
        
        return reconstructed
    
    def _normalise_price_token(self, token: str) -> Optional[float]:
        """
        PHASE 6 - Module 2: Robust price token normalization.
        
        Normalizes price strings with various formats and handles OCR confusion.
        Handles: 12.00, £12.00, 12,00, 12.00€, 12 00, O0.00 (OCR confusion)
        
        Args:
            token: Price token string to normalize
            
        Returns:
            Normalized float value or None if not a valid price
        """
        if not token or not token.strip():
            return None
        
        # Remove currency symbols
        cleaned = token.replace('£', '').replace('$', '').replace('€', '').strip()
        
        # Handle OCR character confusion: O→0, l→1, I→1, S→5, etc.
        # Common OCR mistakes in prices
        ocr_fixes = {
            'O': '0',  # Letter O confused with zero
            'o': '0',  # Lowercase o
            'l': '1',  # Lowercase L confused with one
            'I': '1',  # Capital I confused with one
            'S': '5',  # S confused with 5
            's': '5',  # Lowercase s
        }
        
        # Apply OCR fixes to numeric parts only (preserve separators)
        for wrong, correct in ocr_fixes.items():
            # Only replace if it's in a numeric context (not in currency symbol)
            cleaned = re.sub(
                rf'([\d,\.\s]){wrong}([\d,\.\s])',
                lambda m, corr=correct: f"{m.group(1)}{corr}{m.group(2)}",
                cleaned
            )
            # Also handle at start/end
            if cleaned.startswith(wrong):
                cleaned = correct + cleaned[1:]
            if cleaned.endswith(wrong):
                cleaned = cleaned[:-1] + correct
        
        # Handle trailing punctuation: "12.00." or ".12.00" → clean
        # Remove trailing dots/commas that are clearly punctuation
        cleaned = re.sub(r'\.+$', '', cleaned)  # Remove trailing dots
        cleaned = re.sub(r',+$', '', cleaned)   # Remove trailing commas
        
        # Handle leading dots: ".12.00" → "12.00"
        cleaned = re.sub(r'^\.+', '', cleaned)
        
        # Normalize separators: handle both comma and space as thousands separators
        # Pattern: "12 00" or "12,00" → "12.00" (if looks like decimal)
        # But "1,234.50" → keep as is (thousands separator)
        
        # Check if it looks like European format (comma as decimal): "12,00"
        if re.match(r'^\d+,\d{2}$', cleaned):
            cleaned = cleaned.replace(',', '.')
        # Check if it looks like space-separated decimal: "12 00" (two digits after space)
        elif re.match(r'^\d+\s+\d{2}$', cleaned):
            cleaned = cleaned.replace(' ', '.')
        else:
            # Remove spaces and commas (treat as thousands separators)
            cleaned = cleaned.replace(' ', '').replace(',', '')
        
        # Try to parse as float
        try:
            price_val = float(cleaned)
            # Validate: reasonable price range (0 < price < 100,000)
            if 0 < price_val < 100000:
                return round(price_val, 2)
        except (ValueError, TypeError):
            pass
        
        return None
    
    def _extract_prices_from_line_end(self, line: str, pack_size: Optional[str] = None) -> Tuple[Optional[float], Optional[float]]:
        """
        Extract unit_price and total_price from the end of a line.
        
        Patterns to match:
        - "69.31 69.31" → (69.31, 69.31)
        - "69.3169.31" → (69.31, 69.31) [merged numbers - MODULE 3]
        - "x 12.00" → (12.00, None) [multiplier pattern - MODULE 3]
        - "6 x 12.00" → (12.00, 72.00) [qty × unit, compute total - MODULE 3]
        - "£1,234.50" → (None, 1234.50)
        - "50.00 200.00" → (50.00, 200.00)
        - "$123.45" → (None, 123.45)
        - "123" → (None, 123.00) [whole numbers]
        - "1,234" → (None, 1234.00) [whole numbers with commas]
        
        Args:
            line: Full line text
            pack_size: Optional pack size (e.g., "12L") to exclude from price extraction
        
        Returns:
            Tuple of (unit_price, total_price) where either may be None
        """
        # PHASE 6 - Module 2: Enhanced merged price detection
        # Check for merged number patterns (e.g., "69.3169.31", "12.0012.00")
        merged_pattern = re.search(r'(\d{1,3}(?:[,\s]\d{3})*\.\d{2})(\d{1,3}(?:[,\s]\d{3})*\.\d{2})', line)
        if merged_pattern:
            # Use normalization to handle OCR confusion in merged prices
            price1_token = merged_pattern.group(1)
            price2_token = merged_pattern.group(2)
            price1 = self._normalise_price_token(price1_token)
            price2 = self._normalise_price_token(price2_token)
            
            # Validate both prices are within sane bounds
            if price1 is not None and price2 is not None and 0 < price1 < 10000 and 0 < price2 < 10000:
                LOGGER.debug(f"[PRICE_EXTRACT] Detected merged numbers: {price1} + {price2} from '{line[-50:]}'")
                # Return as unit and total (rightmost is usually total)
                return (price1, price2)
        
        # MODULE 3: Check for multiplier patterns: "x 12.00" or "6 x 12.00"
        multiplier_pattern = re.search(r'(\d+)\s*x\s*([\d,]+\.?\d{0,2})', line, re.IGNORECASE)
        if multiplier_pattern:
            try:
                qty = int(multiplier_pattern.group(1))
                unit_price_token = multiplier_pattern.group(2)
                # PHASE 6: Use normalization for price token
                unit_price = self._normalise_price_token(unit_price_token)
                if unit_price is not None and 0 < unit_price < 10000 and 0 < qty <= 100:
                    total_price = qty * unit_price
                    if total_price < 100000:
                        LOGGER.debug(f"[PRICE_EXTRACT] Detected multiplier pattern: {qty} x {unit_price} = {total_price}")
                        return (unit_price, total_price)
            except (ValueError, TypeError):
                pass  # Fall through to normal extraction
        
        # Also check for standalone "x 12.00" pattern (no quantity)
        standalone_multiplier = re.search(r'\bx\s*([\d,]+\.?\d{0,2})', line, re.IGNORECASE)
        if standalone_multiplier:
            unit_price_token = standalone_multiplier.group(1)
            # PHASE 6: Use normalization for price token
            unit_price = self._normalise_price_token(unit_price_token)
            if unit_price is not None and 0 < unit_price < 10000:
                LOGGER.debug(f"[PRICE_EXTRACT] Detected standalone multiplier: x {unit_price}")
                return (unit_price, None)
        
        # FIX 1: Expand window but prefer rightmost prices
        # Scan last 80 chars for wider layouts, but prioritize rightmost matches
        if len(line) <= 100:
            line_end = line
        else:
            line_end = line[-80:]
        
        # FIX 2: Extract pack size number to exclude it from price matching
        pack_size_number = None
        if pack_size:
            # Extract numeric part from pack size (e.g., "12L" → 12)
            pack_match = re.match(r'^(\d+)', pack_size)
            if pack_match:
                try:
                    pack_size_number = float(pack_match.group(1))
                except (ValueError, TypeError):
                    pass
        
        # FIX 3: More flexible price patterns
        # Pattern 1: Prices with exactly 2 decimal places (original, strict) - most reliable
        price_pattern_strict = r'(?:[£$€]?\s*)?(\d{1,3}(?:[,\s]\d{3})*\.\d{2}|\d+\.\d{2})\b'
        
        # Pattern 2: Whole numbers (no decimals) - but we'll filter out unit indicators
        price_pattern_whole = r'(?:[£$€]?\s*)?(\d{1,3}(?:[,\s]\d{3})*)\b(?![.\d])'
        
        # Pattern 3: Prices with 1 decimal place
        price_pattern_one_decimal = r'(?:[£$€]?\s*)?(\d{1,3}(?:[,\s]\d{3})*\.\d{1})\b(?![.\d])'
        
        # Try strict pattern first (most reliable)
        matches = re.findall(price_pattern_strict, line_end)
        
        # If no strict matches, try whole numbers
        if not matches:
            matches = re.findall(price_pattern_whole, line_end)
            # Filter out very small numbers that are likely quantities, not prices
            matches = [m for m in matches if len(m.replace(',', '').replace(' ', '')) >= 2]
        
        # If still no matches, try one decimal place
        if not matches:
            matches = re.findall(price_pattern_one_decimal, line_end)
        
        # FIX 3b: Filter out numbers that are part of unit indicators (L, G, LITRE, ABV, %)
        # Check if number is immediately followed by unit indicators
        filtered_matches = []
        for match in matches:
            # Find the match position in the line
            match_pos = line_end.find(match)
            if match_pos >= 0:
                # Check what comes after the match
                after_match = line_end[match_pos + len(match):match_pos + len(match) + 10].strip()
                # Exclude if followed by unit indicators
                if re.match(r'^\s*(L|G|LITRE|LTR|GAL|GALLON|ABV|%)', after_match, re.IGNORECASE):
                    LOGGER.debug(f"[PRICE_EXTRACT] Excluding number near unit indicator: {match} (followed by: '{after_match[:5]}')")
                    continue
                # Also check what comes before (for patterns like "18 4G")
                before_match = line_end[max(0, match_pos - 5):match_pos].strip()
                if re.search(r'(L|G|LITRE|LTR|GAL|GALLON|ABV|%)\s*$', before_match, re.IGNORECASE):
                    LOGGER.debug(f"[PRICE_EXTRACT] Excluding number after unit indicator: {match} (preceded by: '{before_match}')")
                    continue
            filtered_matches.append(match)
        matches = filtered_matches
        
        if not matches:
            return (None, None)
        
        # PHASE 6 - Module 2: Use _normalise_price_token() for robust price normalization
        clean_prices = []
        match_positions = []  # Track positions for rightmost preference
        
        for match in matches:
            # Use new normalization method (handles OCR confusion, trailing punctuation, etc.)
            price_val = self._normalise_price_token(match)
            
            if price_val is None:
                continue
            
            # FIX 5: Exclude pack size number if it matches
            if pack_size_number is not None and abs(price_val - pack_size_number) < 0.01:
                LOGGER.debug(f"[PRICE_EXTRACT] Excluding pack size number: {price_val} (pack_size={pack_size})")
                continue
            
            # Validate: prices should be > 0 and < 10000 (strict requirement)
            # Must not be Qty accidentally parsed as price
            if 0 < price_val < 10000:
                # Find position in original line (rightmost is better)
                pos = line.rfind(match)
                clean_prices.append(price_val)
                match_positions.append(pos if pos >= 0 else 0)
        
        if not clean_prices:
            return (None, None)
        
        # FIX 6: Remove duplicates while preserving order
        seen = set()
        unique_prices = []
        unique_positions = []
        for i, price in enumerate(clean_prices):
            if price not in seen:
                seen.add(price)
                unique_prices.append(price)
                unique_positions.append(match_positions[i])
        clean_prices = unique_prices
        match_positions = unique_positions
        
        # FIX 7: Prefer rightmost prices (prices are usually right-aligned)
        if len(clean_prices) > 1:
            # Sort by position (rightmost first)
            sorted_indices = sorted(range(len(clean_prices)), key=lambda i: match_positions[i], reverse=True)
            clean_prices = [clean_prices[i] for i in sorted_indices]
        
        # Determine unit_price and total_price (use numeric magnitude: smallest=unit, largest=total)
        if len(clean_prices) >= 2:
            prices_sorted = sorted(clean_prices)
            return (prices_sorted[-2], prices_sorted[-1])
        elif len(clean_prices) == 1:
            return (None, clean_prices[0])
        return (None, None)
    
    def _wide_net_line_items(self, candidate_lines: List[str]) -> List['LineItem']:
        """
        Super-lenient wide-net fallback: create minimal line items from any line with price-like tokens.

        This is the "don't come back empty-handed" rule - if we see prices, create items.

        Args:
            candidate_lines: List of candidate lines to scan

        Returns:
            List of minimal LineItem objects
        """
        # DEBUG: Verify this function is being called
        LOGGER.info(f"[WIDE_NET_DEBUG] _wide_net_line_items called with {len(candidate_lines)} lines")
        # LineItem is defined in this module (see class LineItem above)
        items = []
        price_pattern = re.compile(r'(\d+[.,]\d{2}|\d+,\d{3}\.\d{2}|\d+\.\d{1,2}|[£$€]\s*(\d+[.,]?\d*))')
        int_pattern = re.compile(r'\b(\d{1,3})\b')
        
        for line_idx, line in enumerate(candidate_lines):
            if not line or not line.strip():
                continue
            
            line_stripped = line.strip()
            
            # Check if line has alphabetic characters and price-like tokens
            has_alphabetic = bool(re.search(r'[A-Za-z]', line_stripped))
            price_matches = list(price_pattern.finditer(line_stripped))
            
            if has_alphabetic and price_matches:
                # Extract all prices; prefer smallest as unit and largest as total if multiple
                prices_floats = []
                for m in price_matches:
                    pt = m.group(1)
                    pn = pt.replace('£', '').replace('$', '').replace('€', '').replace(',', '').strip()
                    try:
                        prices_floats.append((m.start(), float(pn)))
                    except (ValueError, AttributeError):
                        continue
                if not prices_floats:
                    continue
                prices_sorted = sorted(prices_floats, key=lambda x: x[1])  # (start_idx, price)

                # Heuristic: if 2+ prices, treat largest as total, second-largest as unit.
                # If 3+ prices, smallest is often discount; ignore it.
                total_price_val = None
                unit_price_val = None
                first_price_start = prices_sorted[0][0]

                if len(prices_sorted) >= 2:
                    # largest -> total, second largest -> unit
                    total_price_val = prices_sorted[-1][1]
                    unit_price_val = prices_sorted[-2][1]
                    first_price_start = prices_sorted[-2][0]  # description ends before unit price
                else:
                    unit_price_val = prices_sorted[0][1]
                    total_price_val = None
                    first_price_start = prices_sorted[0][0]

                # Extract description (everything before first price) and clean leading punctuation
                description = line_stripped[:first_price_start].strip()
                description = re.sub(r'^[^\w]+', '', description)  # drop leading punctuation
                description = re.sub(r'[^\w\s-]+$', '', description).strip()
                
                # Skip if description is too short or looks like metadata
                if len(description) < 3:
                    continue
                desc_lower = description.lower()
                if any(kw in desc_lower for kw in ['invoice', 'total', 'vat', 'date', 'account', 'statement']):
                    continue
                
                # Try to capture an explicit quantity before the first price
                qty_val = None
                for m in int_pattern.finditer(line_stripped):
                    if m.start() < first_price_start:
                        try:
                            cand = int(m.group(1))
                            if 1 <= cand <= 100:
                                qty_val = cand
                                break
                        except ValueError:
                            pass
                
                # Infer quantity from total/unit if not explicitly found
                if qty_val is None and total_price_val and unit_price_val > 0:
                    inferred = round(total_price_val / unit_price_val)
                    if 1 <= inferred <= 100 and abs(total_price_val - inferred * unit_price_val) / max(total_price_val, 1) < 0.1:
                        qty_val = inferred
                
                if qty_val is None:
                    qty_val = 1
                
                # Choose total_price based on parsed values
                out_total_price = total_price_val if total_price_val and total_price_val >= unit_price_val else unit_price_val

                # Create minimal LineItem
                cell_data = {
                    "line_index": line_idx,
                    "raw_line": line_stripped,
                    "qty_source": "wide_net_fallback_inferred" if qty_val != 1 else "wide_net_fallback_qty1",
                    "price_source": "wide_net_line_price",
                    "inference_notes": ["wide_net_fallback_created_from_single_line"],
                    "method": "line_fallback_wide_net"
                }
                
                line_item = LineItem(
                    description=description,
                    quantity=str(qty_val),
                    unit_price=f"{unit_price_val:.2f}",
                    total_price=f"{out_total_price:.2f}",
                    vat="",
                    confidence=0.5,  # Low confidence for wide-net items
                    row_index=len(items),
                    cell_data=cell_data
                )
                
                items.append(line_item)
                LOGGER.debug(f"[WIDE_NET] Created item from line {line_idx}: '{description[:50]}...' price={unit_price_val:.2f}")
        
        return items
    
    def fallback_extract_from_lines(self, lines: List[str], base_confidence: float = 0.75, items_region_subtotal: Optional[Tuple[int, int]] = None, price_grid: Optional[Dict[str, Any]] = None, line_structure: Optional[Dict[str, Any]] = None, supplier_name: Optional[str] = None, items_region_detected: bool = False) -> Tuple[List[LineItem], List[Dict[str, Any]]]:
        """
        Fallback extractor when we have a flat list of OCR lines (no table blocks).
        
        PHASE 4 - Module B: Now runs 3 passes (strict, standard, lenient) and combines results.
        
        Uses simple heuristics:
        - Identify potential item lines
        - Parse quantity + pack_size from the start using parse_qty_and_pack_size()
        - Parse numeric values at the end as unit_price / line_total where possible
        - Stop at 'SUBTOTAL' / 'TOTAL' lines
        
        Args:
            lines: List of OCR text lines
            base_confidence: Base OCR confidence for adaptive parsing (MODULE 6)
            items_region_subtotal: Optional tuple (start_idx, end_idx) for SUBTOTAL region boost (MODULE 5)
            price_grid: Optional price grid info from MODULE 1 for advisory boost
            line_structure: Optional line structure info from PHASE 4 Module A
            supplier_name: Optional supplier name for PHASE 4 Module D pattern learning
            items_region_detected: Whether items region was detected (affects candidate region selection)
        
        Returns:
            Tuple of (line_items, skipped_lines) where skipped_lines contains
            {"line_index": int, "reason": str} for each skipped line
        """
        # B. Build manual candidate region if items_region_detected is False
        candidate_start = 0
        candidate_end = len(lines)
        candidate_region_info = None
        
        if not items_region_detected:
            # Find header line with keywords
            header_keywords = ['item', 'qty', 'rate', 'unit price', 'description', 'product', 'code']
            header_idx = None
            for i, line in enumerate(lines):
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in header_keywords):
                    header_idx = i
                    LOGGER.debug(f"[LINE_FALLBACK] Found header line at index {i}: '{line[:50]}'")
                    break

            if header_idx is not None:
                candidate_start = header_idx + 1
            else:
                # No header found, skip first few lines of address/metadata
                candidate_start = min(5, len(lines))

            # Use subtotal region end if available
            if items_region_subtotal is not None:
                candidate_end = items_region_subtotal[0]  # Start of subtotal region
            else:
                candidate_end = len(lines)

            candidate_region_info = {"start_idx": candidate_start, "end_idx": candidate_end}
            LOGGER.info(f"[LINE_FALLBACK] Manual candidate region: lines {candidate_start} to {candidate_end-1} (items_region_detected=False) - ORIGINAL_LINES={len(lines)}")

            # Use candidate region for all passes
            lines = lines[candidate_start:candidate_end]
            LOGGER.info(f"[LINE_FALLBACK] Using candidate region: {len(lines)} lines after slicing")
        else:
            # Items region detected - use all lines as-is
            candidate_region_info = {"start_idx": 0, "end_idx": len(lines)}
        
        # PHASE 4 - Module B: Multi-Pass Extraction
        # Run 3 passes with different strictness levels
        # ENFORCE PASS ORDERING: strict → standard → lenient (explicit ordering)
        LOGGER.error(f"[DEBUG_TEST] fallback_extract_from_lines called with {len(lines)} lines - our changes should be active!")
        LOGGER.info(f"[LINE_FALLBACK] Starting multi-pass extraction (confidence={base_confidence:.3f}, {len(lines)} lines)")
        
        # Pass 1: High confidence (strict) - confidence boost to 1.1
        pass1_confidence = min(0.95, base_confidence * 1.1)
        items_pass1, skipped_pass1 = self._fallback_extract_single_pass(
            lines, pass1_confidence, items_region_subtotal, price_grid, 
            line_structure, supplier_name, pass_name="strict"
        )
        LOGGER.info(f"[LINE_FALLBACK] Pass 1 (strict): {len(items_pass1)} items, {len(skipped_pass1)} skipped")
        
        # Pass 2: Standard (current heuristics) - use base_confidence
        items_pass2, skipped_pass2 = self._fallback_extract_single_pass(
            lines, base_confidence, items_region_subtotal, price_grid,
            line_structure, supplier_name, pass_name="standard"
        )
        LOGGER.info(f"[LINE_FALLBACK] Pass 2 (standard): {len(items_pass2)} items, {len(skipped_pass2)} skipped")
        
        # Pass 3: Low confidence (lenient) - confidence boost to 0.8, more lenient
        pass3_confidence = max(0.5, base_confidence * 0.8)
        items_pass3, skipped_pass3 = self._fallback_extract_single_pass(
            lines, pass3_confidence, items_region_subtotal, price_grid,
            line_structure, supplier_name, pass_name="lenient", lenient_mode=True
        )
        LOGGER.info(f"[LINE_FALLBACK] Pass 3 (lenient): {len(items_pass3)} items, {len(skipped_pass3)} skipped")
        
        # PHASE 6 - Module 7: Enhanced multi-pass debug info
        pass_details = {
            "pass_strict": {"extracted": len(items_pass1), "skipped": len(skipped_pass1)},
            "pass_standard": {"extracted": len(items_pass2), "skipped": len(skipped_pass2)},
            "pass_lenient": {"extracted": len(items_pass3), "skipped": len(skipped_pass3)},
            "final_method": None  # Will be set after combination
        }
        
        try:
            combined_items, combined_skipped, final_method = self._combine_multi_pass_results(
                items_pass1, items_pass2, items_pass3,
                skipped_pass1, skipped_pass2, skipped_pass3
            )
            LOGGER.info(f"[LINE_FALLBACK] Multi-pass combined: {len(combined_items)} items, {len(combined_skipped)} skipped, final_method={final_method}")
            pass_details["final_method"] = final_method
        except Exception as e:
            LOGGER.warning(f"[LINE_FALLBACK] Multi-pass combination failed: {e}, falling back to standard pass", exc_info=True)
            # Fallback to standard pass results
            combined_items = items_pass2
            combined_skipped = skipped_pass2
            pass_details["final_method"] = "standard_fallback"
            pass_details["phase4_failure"] = "multi_pass_combination"
            # Mark failure in items' cell_data
            for item in combined_items:
                if item.cell_data:
                    item.cell_data["phase4_failure"] = "multi_pass_combination"
        
        # C. Final super-lenient wide-net fallback if no items found
        if len(combined_items) == 0:
            # Check if candidate region has price-like tokens
            price_pattern = re.compile(r'\d+\.\d{2}|\d+,\d{3}\.\d{2}|\d+\.\d{1,2}|[£$€]\s*\d+')
            has_price_tokens = False
            for line in lines:
                if price_pattern.search(line):
                    has_price_tokens = True
                    break
            
            if has_price_tokens:
                LOGGER.info(f"[LINE_FALLBACK] No items found but price tokens detected, running wide-net fallback")
                wide_net_items = self._wide_net_line_items(lines)
                if wide_net_items:
                    LOGGER.info(f"[LINE_FALLBACK] Wide-net fallback found {len(wide_net_items)} items")
                    combined_items = wide_net_items
                    pass_details["final_method"] = "fallback_wide_net"
                    # Mark in pass_details
                    pass_details["wide_net_items"] = len(wide_net_items)
        
        # Store pass details and candidate region in a way that can be accessed by caller
        # Attach to first item's cell_data as metadata (will be collected in debug_info)
        if combined_items and combined_items[0].cell_data:
            combined_items[0].cell_data["_phase6_pass_details"] = pass_details
            if candidate_region_info:
                combined_items[0].cell_data["_candidate_region"] = candidate_region_info
        
        return (combined_items, combined_skipped)
    
    def _classify_line(self, raw: str, tokens: List[str], line_idx: int, word_blocks: Optional[List[Dict]] = None) -> str:
        """
        PHASE 6 - Module 3: Context-aware line classification.
        
        Classifies each line into one of: 'item', 'desc', 'cont', 'header', 'total', 'noise'
        
        Args:
            raw: Raw line text
            tokens: Tokenized line (list of words)
            line_idx: Line index in document
            word_blocks: Optional word blocks with bbox info for spatial analysis
            
        Returns:
            Classification string: 'item', 'desc', 'cont', 'header', 'total', or 'noise'
        """
        if not raw or not raw.strip():
            return 'noise'
        
        line_lower = raw.lower().strip()
        line_upper = raw.upper().strip()
        
        # PRIORITY CHECK: If line has quantity + product words, classify as 'item' immediately
        # This overrides header/total classification
        if self._line_has_quantity_and_product_words(raw):
            LOGGER.info(f"[CLASSIFY_DEBUG] Line has quantity + product words, classifying as 'item': '{raw[:50]}'")
            return 'item'
        
        # Check for total/header keywords (but only if no quantity+product signal)
        total_keywords = ['subtotal', 'sub-total', 'sub total', 'vat total', 'vat summary', 
                         'total', 'grand total', 'total due', 'balance due', 'amount due',
                         'invoice total', 'net total']
        for keyword in total_keywords:
            if keyword in line_lower:
                return 'total'
        
        header_keywords = ['invoice', 'invoice number', 'invoice date', 'date:', 'invoice #',
                          'ship to', 'bill to', 'delivery address', 'billing address',
                          'product', 'description', 'qty', 'quantity', 'rate', 'amount',
                          'item', 'items', 'line', 'lines']
        for keyword in header_keywords:
            # Only classify as header if line STARTS with keyword AND has no quantity+product signal
            if (line_lower.startswith(keyword) or line_lower == keyword):
                # Double-check: if it has quantity + product words, it's still an item
                if not self._line_has_quantity_and_product_words(raw):
                    return 'header'
        
        # Check for price patterns
        price_pattern = re.compile(r'[\d,]+\.\d{2}|[£$€]\s*[\d,]+\.?\d*')
        has_price = bool(price_pattern.search(raw))
        
        # Check for quantity patterns
        qty_pattern = re.compile(r'^\s*[\W\s]*?(\d+)[\s\.\)\^]+')
        has_qty = bool(qty_pattern.match(raw))
        
        # Check for product keywords
        product_keywords = ['pepsi', 'coke', 'coca', 'cola', 'beer', 'wine', 'spirit',
                           'bottle', 'can', 'pack', 'case', 'keg', 'litre', 'gallon',
                           'premium', 'regular', 'diet', 'zero', 'max']
        has_product_keyword = any(keyword in line_lower for keyword in product_keywords)
        
        # Check bounding box structure if available
        has_structure = False
        if word_blocks:
            # Check if we have aligned columns (suggests structured item line)
            x_positions = []
            for wb in word_blocks:
                if isinstance(wb, dict) and 'bbox' in wb:
                    bbox = wb.get('bbox', [])
                    if len(bbox) >= 4:
                        x_positions.append(bbox[0])
            
            # If we have multiple words with similar X positions, likely structured
            if len(x_positions) >= 3:
                # Check for column alignment (similar X positions)
                x_sorted = sorted(x_positions)
                # Count distinct column positions (within 30px tolerance)
                distinct_cols = 1
                for i in range(1, len(x_sorted)):
                    if x_sorted[i] - x_sorted[i-1] > 30:
                        distinct_cols += 1
                
                if distinct_cols >= 2:  # At least 2 columns suggests structured line
                    has_structure = True
        
        # Classification logic
        # Item line: has qty AND (has price OR has product keyword)
        if has_qty and (has_price or has_product_keyword):
            return 'item'
        
        # Description line: has product keyword OR (has alphabetic content AND no price)
        if has_product_keyword or (re.search(r'[A-Za-z]{3,}', raw) and not has_price and not has_qty):
            # Check if it looks like continuation (starts with lowercase or is short)
            if len(tokens) > 0 and tokens[0]:
                first_token = tokens[0]
                if first_token and len(first_token) > 0 and first_token[0].islower() or len(raw) < 30:
                    return 'cont'
            return 'desc'
        
        # Continuation line: no qty, no price, starts with lowercase or is short
        if not has_qty and not has_price:
            if len(tokens) > 0 and raw.strip():
                first_char = raw.strip()[0]
                if first_char and first_char.islower() or len(raw.strip()) < 25:
                    return 'cont'
        
        # If has price but no qty and no product keyword, might be item or total
        if has_price and not has_qty:
            # Check if it's a single price (likely total line)
            price_matches = price_pattern.findall(raw)
            if len(price_matches) == 1 and len(tokens) <= 3:
                return 'total'
            # Otherwise might be item with missing qty
            if has_structure or len(tokens) >= 4:
                return 'item'
        
        # Default: if we have substantial content, treat as description
        if len(raw.strip()) >= 5 and re.search(r'[A-Za-z]', raw):
            return 'desc'
        
        # Everything else is noise
        LOGGER.debug(f"[CLASSIFY_DEBUG] Line classified as 'noise': '{raw[:50]}'")
        return 'noise'
    
    def _assemble_item_block(self, start_idx: int, lines: List[str], classifications: List[str]) -> Tuple[str, int]:
        """
        PHASE 6 - Module 4: Greedy multi-line item assembly.
        
        Assembles blocks: [item line] + [continuation line] + [continuation line]
        
        Args:
            start_idx: Starting line index
            lines: List of all lines
            classifications: List of line classifications (parallel to lines)
            
        Returns:
            Tuple of (block_text, end_idx) where end_idx is the index after the last line in block
        """
        if start_idx >= len(lines) or start_idx >= len(classifications):
            return ("", start_idx)
        
        # Start with the initial line
        block_lines = [lines[start_idx]]
        current_idx = start_idx + 1
        max_continuations = 3  # Maximum continuation lines per item
        
        continuation_count = 0
        
        # Continue while next line is continuation or description
        while current_idx < len(lines) and continuation_count < max_continuations:
            if current_idx >= len(classifications):
                break
            
            classification = classifications[current_idx]
            
            # Stop conditions
            if classification in ['item', 'header', 'total', 'noise']:
                break
            
            # Continue if it's a continuation or description line
            if classification in ['cont', 'desc']:
                block_lines.append(lines[current_idx])
                continuation_count += 1
                current_idx += 1
            else:
                # Unknown classification, stop
                break
        
        # Join lines with space
        block_text = " ".join(block_lines)
        
        return (block_text, current_idx)
    
    def _extract_quantity_full_spectrum(self, line: str) -> Tuple[Optional[int], str]:
        """
        PHASE 6 - Module 1: Full-spectrum quantity extraction (block-level aware).
        
        Extract quantities from ANY of these patterns, with block-level intelligence:
        - Filters out price-like tokens (decimals > 1, currency symbols, percentages)
        - Prioritizes small integers (1-48) over larger numbers
        - Works at block level to consider all numeric tokens
        
        Extract quantities from ANY of these patterns:
        - x12, 12x, 12 X 1L, 12*1L, 12pk
        - case of 6, (6), 6), 6., 6-
        - qty:12, QTY: 12
        - Number before description
        
        Args:
            line: Input line/block text
            
        Returns:
            Tuple of (quantity, remaining_text) where quantity may be None
        """
        if not line or not line.strip():
            return (None, line)
        
        line_stripped = line.strip()
        remaining_text = line_stripped
        
        # BLOCK-LEVEL QUANTITY EXTRACTION: Collect all numeric tokens and filter
        # Split block into lines for better context
        block_lines = [l.strip() for l in line_stripped.split('\n') if l.strip()]
        all_numeric_tokens = []
        
        # Collect all numeric tokens with their context
        for line_idx, block_line in enumerate(block_lines):
            # Find all numeric tokens in this line
            numeric_pattern = re.compile(r'\b(\d+(?:[.,]\d+)?)\b')
            for match in numeric_pattern.finditer(block_line):
                token = match.group(1)
                token_pos = match.start()
                line_text = block_line
                
                # Try to parse as float/int
                try:
                    # Normalize decimal separator
                    normalized = token.replace(',', '.')
                    if '.' in normalized:
                        value = float(normalized)
                        is_integer = False
                    else:
                        value = int(normalized)
                        is_integer = True
                    
                    all_numeric_tokens.append({
                        'value': value,
                        'token': token,
                        'is_integer': is_integer,
                        'line_idx': line_idx,
                        'position': token_pos,
                        'line_text': line_text
                    })
                except (ValueError, AttributeError):
                    continue
        
        # Filter tokens into price-like and quantity-like
        price_like_tokens = []
        quantity_like_tokens = []
        
        for token_info in all_numeric_tokens:
            value = token_info['value']
            token = token_info['token']
            line_text = token_info['line_text']
            is_integer = token_info['is_integer']
            
            # Check if price-like
            is_price_like = False
            
            # Has decimal separator and value > 1.0
            if '.' in token or ',' in token:
                if abs(value) > 1.0:
                    is_price_like = True
            
            # Contains currency symbol nearby
            token_start = line_text.find(token)
            context = line_text[max(0, token_start-2):token_start+len(token)+2]
            if re.search(r'[£$€]', context):
                is_price_like = True
            
            # Looks like percentage (xx.xx% or xx%)
            if re.search(r'\d+[.,]?\d*\s*%', line_text):
                # Check if this token is part of percentage
                if re.search(rf'{re.escape(token)}\s*%', line_text):
                    is_price_like = True
            
            # VAT/discount pattern (e.g., "17.65/10%")
            if re.search(r'\d+[.,]\d+\s*/\s*\d+%', line_text):
                if token in line_text:
                    is_price_like = True
            
            if is_price_like:
                price_like_tokens.append(token_info)
            elif is_integer and 1 <= value <= 120:
                # Quantity-like: integer in reasonable range
                quantity_like_tokens.append(token_info)
            # REMOVED: Don't add integers > 120 as quantity candidates
            # They're likely prices, invoice numbers, or other metadata, not quantities
            # This prevents extracting "176" from "176.50" as a quantity
        
        # Score quantity candidates
        scored_candidates = []
        for token_info in quantity_like_tokens:
            value = token_info['value']
            position = token_info['position']
            line_text = token_info['line_text']
            
            # Base score by value range
            if 1 <= value <= 48:
                score = 100  # Highest priority
            elif 49 <= value <= 120:
                score = 50   # Medium priority
            else:
                score = 10   # Low priority (only if nothing else)
            
            # Bonus: closer to start of line
            line_length = len(line_text)
            if line_length > 0:
                position_ratio = 1.0 - (position / line_length)
                score += int(position_ratio * 20)  # Up to +20 points
            
            # Bonus: line has product-like text (not just meta words)
            has_product_words = bool(re.search(r'\b(pepsi|coke|cola|beer|wine|keg|bottle|can|pack|case|litre|gallon|premium|regular|diet|zero|max|connector|dispense)\b', line_text, re.IGNORECASE))
            has_meta_words = bool(re.search(r'\b(invoice|total|vat|date|account|statement|page|no\.?|number)\b', line_text, re.IGNORECASE))
            if has_product_words and not has_meta_words:
                score += 30  # Strong product signal
            
            scored_candidates.append((score, value, token_info))
        
        # Sort by score (highest first)
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        
        # If we have good quantity candidates, use the best one
        if scored_candidates and scored_candidates[0][0] >= 50:
            best_qty = scored_candidates[0][1]
            best_token_info = scored_candidates[0][2]
            qty_source_tag = "explicit_integer_block_scan"
            
            # Remove the quantity token from remaining text (if it's at the start)
            remaining_text = line_stripped
            # Try to remove the quantity from the beginning if it's there
            qty_pattern = re.compile(rf'^\s*{re.escape(str(int(best_qty)))}\s+', re.IGNORECASE)
            remaining_text = qty_pattern.sub('', remaining_text).strip()
            
            return (int(best_qty), remaining_text)
        
        # Fallback: Use original pattern-based extraction for explicit patterns
        # Pattern 1: "x12" or "12x" (quantity with x prefix/suffix)
        match = re.match(r'^x\s*(\d+)\s+(.+)$', line_stripped, re.IGNORECASE)
        if match:
            qty = int(match.group(1))
            return (qty, match.group(2).strip())
        
        match = re.match(r'^(\d+)\s*x\s+(.+)$', line_stripped, re.IGNORECASE)
        if match:
            qty = int(match.group(1))
            return (qty, match.group(2).strip())
        
        # Pattern 2: "12 X 1L" or "12*1L" (quantity with multiplier and unit)
        match = re.match(r'^(\d+)\s*[xX*]\s*\d+[A-Za-z]+\s+(.+)$', line_stripped, re.IGNORECASE)
        if match:
            qty = int(match.group(1))
            # Extract the part after the unit
            unit_match = re.search(r'\d+[A-Za-z]+\s+(.+)$', line_stripped, re.IGNORECASE)
            if unit_match:
                return (qty, unit_match.group(1).strip())
            return (qty, match.group(2).strip())
        
        # Pattern 3: "12pk" or "12 pk" (quantity with pack indicator)
        match = re.match(r'^(\d+)\s*pk\s+(.+)$', line_stripped, re.IGNORECASE)
        if match:
            qty = int(match.group(1))
            return (qty, match.group(2).strip())
        
        # Pattern 4: "case of 6" or "cases of 12"
        match = re.search(r'case(?:s)?\s+of\s+(\d+)', line_stripped, re.IGNORECASE)
        if match:
            qty = int(match.group(1))
            # Remove the "case of X" part from remaining text
            remaining_text = re.sub(r'case(?:s)?\s+of\s+\d+\s*', '', line_stripped, flags=re.IGNORECASE).strip()
            return (qty, remaining_text)
        
        # Pattern 5: "(6)" or "6)" or "6." or "6-" (quantity in parentheses or with punctuation)
        match = re.match(r'^\((\d+)\)\s+(.+)$', line_stripped)
        if match:
            qty = int(match.group(1))
            return (qty, match.group(2).strip())
        
        match = re.match(r'^(\d+)\)\s+(.+)$', line_stripped)
        if match:
            qty = int(match.group(1))
            return (qty, match.group(2).strip())
        
        match = re.match(r'^(\d+)\.\s+(.+)$', line_stripped)
        if match:
            qty = int(match.group(1))
            return (qty, match.group(2).strip())
        
        match = re.match(r'^(\d+)-\s+(.+)$', line_stripped)
        if match:
            qty = int(match.group(1))
            return (qty, match.group(2).strip())
        
        # Pattern 6: "qty:12" or "QTY: 12" or "quantity: 12"
        match = re.search(r'(?:qty|quantity)\s*:\s*(\d+)', line_stripped, re.IGNORECASE)
        if match:
            qty = int(match.group(1))
            # Remove the qty part from remaining text
            remaining_text = re.sub(r'(?:qty|quantity)\s*:\s*\d+\s*', '', line_stripped, flags=re.IGNORECASE).strip()
            return (qty, remaining_text)
        
        # Pattern 7: Number at start of line (most common pattern)
        # Enhanced prefix noise handling: optional non-digit prefix, then digit
        match = re.match(r'^[\W\s]*?(\d+)[\s\.\)\^]+(.+)$', line_stripped)
        if match:
            qty = int(match.group(1))
            # Validate: reasonable quantity (1-100) and not price-like
            # CRITICAL: Cap at 100 to prevent extracting prices (like 176 from 176.50) as quantities
            if 1 <= qty <= 100:
                # Double-check it's not a price (decimal nearby or currency symbol)
                if not re.search(r'[£$€]', line_stripped[:50]) and '.' not in match.group(1):
                    return (qty, match.group(2).strip())
        
        # Pattern 8: Number near unit (e.g., "12L" at start - extract 12 as qty)
        match = re.match(r'^(\d+)([A-Za-z]{1,3})\s+(.+)$', line_stripped)
        if match:
            qty_str = match.group(1)
            unit = match.group(2).upper()
            # Check if it's a known unit (L, G, ML, etc.) - if so, might be pack size, not qty
            # But if followed by description, treat as quantity
            if unit in ['L', 'G', 'ML', 'PK', 'CT']:
                # This might be pack size, but if there's more text, could be qty
                desc = match.group(3).strip()
                if len(desc) > 3:  # Has substantial description
                    qty = int(qty_str)
                    if 1 <= qty <= 1000:
                        return (qty, f"{qty_str}{unit} {desc}")
        
        # Last resort: if we found any quantity-like token, use it (but only if reasonable)
        # CRITICAL: Only use candidates <= 100 to avoid extracting prices as quantities
        if scored_candidates and scored_candidates[0][1] <= 100:
            best_qty = scored_candidates[0][1]
            qty_source_tag = "explicit_integer_block_scan"
            remaining_text = line_stripped
            qty_pattern = re.compile(rf'^\s*{re.escape(str(int(best_qty)))}\s+', re.IGNORECASE)
            remaining_text = qty_pattern.sub('', remaining_text).strip()
            return (int(best_qty), remaining_text)
        
        # No quantity pattern found
        return (None, line_stripped)
    
    def _wide_net_parsing(self, block_text: str) -> Optional[LineItem]:
        """
        PHASE 6 - Module 5: Wide net parsing strategy.
        
        Find ANY price → extract 3-5 words before it → treat as description.
        
        Args:
            block_text: Block text to parse
            
        Returns:
            LineItem if successful, None otherwise
        """
        if not block_text or len(block_text.strip()) < 5:
            return None
        
        # Find any price in the text
        price_pattern = re.compile(r'[\d,]+\.\d{2}|[£$€]\s*[\d,]+\.?\d*')
        price_match = price_pattern.search(block_text)
        
        if not price_match:
            return None
        
        price_start = price_match.start()
        price_text = price_match.group(0)
        
        # Extract 3-5 words before the price
        text_before_price = block_text[:price_start].strip()
        words = text_before_price.split()
        
        # Take last 3-5 words as description
        if len(words) >= 3:
            desc_words = words[-5:] if len(words) >= 5 else words[-3:]
            description = " ".join(desc_words)
        else:
            description = text_before_price
        
        # Normalize and extract price
        price_val = self._normalise_price_token(price_text)
        if price_val is None:
            return None
        
        # Create minimal line item (qty=1 assumed, no unit price)
        return LineItem(
            description=description.strip(),
            quantity="1",
            unit_price="",
            total_price=f"{price_val:.2f}",
            vat="",
            confidence=0.6,  # Lower confidence for fallback method
            row_index=0,
            cell_data={"fallback_method": "wide_net_parsing", "source_line": block_text}
        )
    
    def _token_pairing_parsing(self, block_text: str) -> Optional[LineItem]:
        """
        PHASE 6 - Module 5: Token pairing parsing strategy.
        
        Look for pairs: (digit cluster) (word cluster) (price)
        even if the order is messy.
        
        Args:
            block_text: Block text to parse
            
        Returns:
            LineItem if successful, None otherwise
        """
        if not block_text or len(block_text.strip()) < 5:
            return None
        
        tokens = block_text.split()
        if len(tokens) < 3:
            return None
        
        # Look for pattern: digit cluster, word cluster(s), price
        digit_cluster = None
        word_cluster = []
        price_val = None
        
        # Scan tokens from left to right
        for i, token in enumerate(tokens):
            # Check if token is a digit cluster (quantity)
            if re.match(r'^\d+$', token):
                qty_val = int(token)
                if 1 <= qty_val <= 1000:
                    digit_cluster = qty_val
            
            # Check if token is a price
            normalized_price = self._normalise_price_token(token)
            if normalized_price is not None:
                price_val = normalized_price
                # Description is everything between digit_cluster and price
                if digit_cluster is not None and i > 0:
                    word_cluster = tokens[1:i] if digit_cluster else tokens[:i]
                break
            
            # If we have a digit cluster, collect words as description
            if digit_cluster is not None and not re.match(r'^\d+$', token):
                word_cluster.append(token)
        
        # If we found price but no qty, try to find qty elsewhere
        if price_val is not None and digit_cluster is None:
            # Look for qty at start
            if tokens and re.match(r'^\d+$', tokens[0]):
                try:
                    digit_cluster = int(tokens[0])
                    if 1 <= digit_cluster <= 1000:
                        word_cluster = tokens[1:-1] if len(tokens) > 2 else []
                except (ValueError, TypeError):
                    pass
        
        # Need at least price and some description
        if price_val is None:
            return None
        
        if not word_cluster:
            # Try to extract description from remaining tokens
            word_cluster = [t for t in tokens if not re.match(r'^[\d,]+\.?\d*$', t) and t.lower() not in ['x', '*', 'x']]
        
        description = " ".join(word_cluster).strip() if word_cluster else "Item"
        
        if len(description) < 2:
            return None
        
        qty = digit_cluster if digit_cluster is not None else 1
        
        return LineItem(
            description=description,
            quantity=str(qty),
            unit_price="",
            total_price=f"{price_val:.2f}",
            vat="",
            confidence=0.65,  # Slightly higher than wide_net
            row_index=0,
            cell_data={"fallback_method": "token_pairing_parsing", "source_line": block_text}
        )
    
    def _pure_description_price_parsing(self, block_text: str) -> Optional[LineItem]:
        """
        PHASE 6 - Module 5: Pure description + price parsing strategy.
        
        If no qty but description + price exist → assume qty=1.
        
        Args:
            block_text: Block text to parse
            
        Returns:
            LineItem if successful, None otherwise
        """
        if not block_text or len(block_text.strip()) < 5:
            return None
        
        # Find price
        price_pattern = re.compile(r'[\d,]+\.\d{2}|[£$€]\s*[\d,]+\.?\d*')
        price_match = price_pattern.search(block_text)
        
        if not price_match:
            return None
        
        price_start = price_match.start()
        price_text = price_match.group(0)
        price_val = self._normalise_price_token(price_text)
        
        if price_val is None:
            return None
        
        # Extract description (everything before price)
        description = block_text[:price_start].strip()
        
        # Clean description
        description = self._clean_description(description)
        
        # Validate description has substantial content
        if len(description) < 3 or not re.search(r'[A-Za-z]', description):
            return None
        
        # Check for product keywords (boost confidence)
        product_keywords = ['pepsi', 'coke', 'coca', 'cola', 'beer', 'wine', 'spirit',
                           'bottle', 'can', 'pack', 'case', 'keg', 'litre', 'gallon']
        has_keyword = any(keyword in description.lower() for keyword in product_keywords)
        confidence = 0.7 if has_keyword else 0.65
        
        return LineItem(
            description=description,
            quantity="1",  # Assume qty=1
            unit_price="",
            total_price=f"{price_val:.2f}",
            vat="",
            confidence=confidence,
            row_index=0,
            cell_data={"fallback_method": "pure_description_price_parsing", "source_line": block_text}
        )
    
    def _fallback_extract_single_pass(self, lines: List[str], base_confidence: float, items_region_subtotal: Optional[Tuple[int, int]], price_grid: Optional[Dict[str, Any]], line_structure: Optional[Dict[str, Any]], supplier_name: Optional[str], pass_name: str = "standard", lenient_mode: bool = False) -> Tuple[List[LineItem], List[Dict[str, Any]]]:
        """
        PHASE 4 - Module B: Single pass extraction (internal method).
        
        This calls the core extraction logic with pass-specific parameters.
        Applies supplier patterns and delegates to _fallback_extract_core.
        """
        LOGGER.debug(f"[LINE_FALLBACK] Starting {pass_name} pass extraction (confidence={base_confidence:.3f}, lenient={lenient_mode})")
        
        # Apply supplier-specific patterns if available (Module D)
        # Use safe dict access with default empty dict
        supplier_pattern_applied = None
        if supplier_name:
            patterns = self._supplier_patterns.get(supplier_name, {})
            if patterns:
                # Adjust base_confidence based on learned patterns
                if patterns.get("avg_confidence", 0) > 0:
                    old_confidence = base_confidence
                    base_confidence = (base_confidence + patterns["avg_confidence"]) / 2
                    supplier_pattern_applied = f"confidence_adjusted_{old_confidence:.3f}_to_{base_confidence:.3f}"
                LOGGER.debug(f"[SUPPLIER_PATTERNS] Applied patterns for {supplier_name}, adjusted confidence to {base_confidence:.3f}")
        
        # Call the core extraction logic with supplier pattern info
        return self._fallback_extract_core(lines, base_confidence, items_region_subtotal, price_grid, line_structure, pass_name, lenient_mode, supplier_pattern_applied)
    
    def _fallback_extract_core(self, lines: List[str], base_confidence: float, items_region_subtotal: Optional[Tuple[int, int]], price_grid: Optional[Dict[str, Any]], line_structure: Optional[Dict[str, Any]], pass_name: str, lenient_mode: bool, supplier_pattern_applied: Optional[str] = None) -> Tuple[List[LineItem], List[Dict[str, Any]]]:
        """
        Core extraction logic (extracted from original fallback_extract_from_lines for multi-pass support).
        Contains the full extraction loop with lenient_mode support.
        """
        LOGGER.error(f"[DEBUG_TEST] _fallback_extract_core called with {len(lines)} lines, pass_name={pass_name} - our changes should be active!")

        # MODULE 1: Log price grid info if available
        if price_grid:
            LOGGER.debug(f"[LINE_FALLBACK] Price grid available: price_column_x={price_grid.get('price_column_x')}, "
                        f"confidence={price_grid.get('confidence', 0):.3f}")

        # MODULE 6: Get parsing strictness based on confidence
        strictness = self._get_parsing_strictness(base_confidence)
        LOGGER.debug(f"[LINE_FALLBACK] Parsing strictness: min_desc_len={strictness['min_description_length']}, "
                    f"qty_1_evidence={strictness['qty_1_evidence_required']}")

        # PHASE 4 - Module A: Use line_structure to guide extraction (if available and confident)
        use_structure_guidance = (
            line_structure and
            line_structure.get("confidence", 0) > 0.5 and
            (line_structure.get("qty_pos") is not None or line_structure.get("price_pos") is not None)
        )
        if use_structure_guidance:
            LOGGER.debug(f"[LINE_FALLBACK] Using structure guidance: qty_pos={line_structure.get('qty_pos')}, "
                        f"price_pos={line_structure.get('price_pos')}, desc_window={line_structure.get('desc_window')}")

        line_items = []
        skipped_lines = []
        
        # PHASE 5 - Module F: Initialize SUBTOTAL tracking for two-phase stopping
        self._subtotal_seen_in_pass = False
        
        # PHASE 5 - Module B: Apply fuzzy reconstruction to all lines first
        # This fixes merged tokens, broken spacing, and fused symbols before processing
        fuzzy_reconstructed_lines = []
        for line in lines:
            reconstructed = self._fuzzy_reconstruct_line(line.strip())
            fuzzy_reconstructed_lines.append(reconstructed)
        lines = fuzzy_reconstructed_lines
        
        # PHASE 5 - Module D: Enhanced description continuation merging
        # Merge continuation lines (description overflow) with expanded rules
        processed_lines = []
        i = 0
        max_continuations = 2  # Allow up to 2 continuation lines per item
        
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
            
            # Check if this line might be a continuation of the previous line
            if i > 0 and processed_lines:
                prev_line = processed_lines[-1]
                prev_line_lower = prev_line.lower()
                
                # Count how many times we've already merged with this previous line
                continuation_count = 0
                if hasattr(processed_lines[-1], '_continuation_count'):
                    continuation_count = processed_lines[-1]._continuation_count
                elif isinstance(processed_lines[-1], str) and '_continuation_count' in str(processed_lines[-1]):
                    # Extract continuation count from metadata if stored
                    continuation_count = 0  # Default
                
                # Only merge if we haven't exceeded max continuations
                if continuation_count < max_continuations:
                    line_lower = line.lower()
                    tokens = line.split()
                    first_token = tokens[0] if tokens else ""
                    
                    # Check for price-like patterns
                    has_price_pattern = bool(re.search(r'[\d,]+\.\d{2}', line))
                    has_qty_pattern = bool(re.match(r'^\s*\d+', line))
                    has_product_keyword = any(keyword in line_lower for keyword in self._product_keywords)
                    
                    # Check if previous line has price but no description (too short)
                    prev_has_price = bool(re.search(r'[\d,]+\.\d{2}', prev_line))
                    prev_tokens = prev_line.split()
                    prev_desc_length = len(' '.join(prev_tokens[1:])) if len(prev_tokens) > 1 else len(prev_line)
                    
                    # Rule 1: No price-like token on line → continuation (even without keyword)
                    rule1 = not has_price_pattern and not has_qty_pattern
                    
                    # Rule 2: First token not numeric → continuation (description overflow)
                    rule2 = first_token and not first_token[0].isdigit() and not has_price_pattern
                    
                    # Rule 3: Description too short (<5 chars) → merge upward
                    rule3 = len(line) < 5 and not has_price_pattern and not has_qty_pattern
                    
                    # Rule 4: Previous line has price but description too short → merge next line as description
                    rule4 = prev_has_price and prev_desc_length < 5 and not has_price_pattern
                    
                    # Original rule: Previous ended mid-word AND current has product keywords AND no qty/price
                    prev_ends_mid_word = (
                        not re.search(r'[\.\,\;\:\!\?]$', prev_line) and
                        not re.search(r'[\d,]+\.\d{2}\s*$', prev_line) and
                        len(prev_line) > 10
                    )
                    rule5 = prev_ends_mid_word and has_product_keyword and not has_price_pattern and not has_qty_pattern
                    
                    # Merge if any rule applies
                    if rule1 or rule2 or rule3 or rule4 or rule5:
                        # Merge with previous line
                        merged_line = f"{prev_line} {line}"
                        processed_lines[-1] = merged_line
                        # Track continuation count (store as attribute on string - we'll use a dict wrapper)
                        # For simplicity, just track in a comment/log
                        LOGGER.debug(f"[LINE_FALLBACK] Merged continuation line {i} with previous (rule: {[r for r, v in [('1', rule1), ('2', rule2), ('3', rule3), ('4', rule4), ('5', rule5)] if v]}): '{line[:50]}'")
                        i += 1
                        continue
            
            processed_lines.append(line)
            i += 1
        
        # PHASE 5 - Module D: Validate merged descriptions
        # Ensure final descriptions are valid (not all numbers, minimum length)
        validated_lines = []
        for line in processed_lines:
            # Check if line is all numbers (likely not a valid description)
            tokens = line.split()
            if tokens:
                # Check if all tokens are numeric (with possible decimal points)
                all_numeric = all(re.match(r'^[\d,]+\.?\d*$', token) for token in tokens)
                if all_numeric and len(tokens) > 2:
                    # Likely not a description, skip or mark
                    LOGGER.debug(f"[LINE_FALLBACK] Skipping line that's all numbers: '{line[:50]}'")
                    continue
            
            # Ensure minimum length (at least 3 chars for description)
            if len(line.strip()) >= 3:
                validated_lines.append(line)
            else:
                LOGGER.debug(f"[LINE_FALLBACK] Skipping line too short after validation: '{line[:50]}'")
        
        # Use validated_lines instead of lines
        lines = validated_lines
        
        # PHASE 6 - Module 3: Classify all lines first
        classifications = []
        try:
            for line_idx, line in enumerate(lines):
                tokens = line.split() if line else []
                try:
                    classification = self._classify_line(line, tokens, line_idx, word_blocks=None)
                    classifications.append(classification)
                except Exception as e:
                    LOGGER.warning(f"[LINE_FALLBACK] Classification failed for line {line_idx}: {e}", exc_info=True)
                    classifications.append('noise')  # Default to noise on error
            
            LOGGER.debug(f"[LINE_FALLBACK] Classified {len(lines)} lines: {sum(1 for c in classifications if c == 'item')} items, "
                        f"{sum(1 for c in classifications if c == 'desc')} desc, {sum(1 for c in classifications if c == 'cont')} cont")
        except Exception as e:
            LOGGER.error(f"[LINE_FALLBACK] Classification phase failed: {e}", exc_info=True)
            # Fallback: classify all as 'desc' to allow processing
            classifications = ['desc'] * len(lines) if lines else []
        
        # Header/footer keywords to skip (expanded list)
        skip_keywords = [
            'invoice', 'ship to', 'bill to', 'invoice number', 'invoice date', 'due date',
            'tel:', 'telephone:', 'phone:', 'company reg', 'company registration', 'reg no',
            'registered office', 'vat registration', 'email:', 'website:', 'www.',
            'delivered in containers', 'we do not accept returns', 'payment info',
            'bank details', 'sort code', 'account number', 'signature', 'name:', 'date:'
        ]
        
        # Stop keywords - stop scanning when we hit these
        stop_keywords = ['subtotal', 'sub-total', 'sub total', 'vat total', 'vat summary', 
                        'total', 'grand total', 'total due', 'balance due', 'amount due']
        
        # PHASE 6 - Module 4: Use block assembly instead of line-by-line
        line_idx = 0
        extraction_error = None
        try:
            while line_idx < len(lines):
                line = lines[line_idx].strip()
                classification = classifications[line_idx] if line_idx < len(classifications) else 'noise'
                
                # Skip noise, headers, and totals (unless we're processing them)
                if classification in ['noise', 'header']:
                    skipped_lines.append({
                        "line_index": line_idx,
                        "reason": f"classification_{classification}",
                        "detail": f"Line classified as {classification}"
                    })
                    line_idx += 1
                    continue
                
                # PHASE 6: Assemble item block if this is an item or desc line
                source_line = line  # Store original before any modifications
                continuation_lines_used = 0
                line_idx_to_use = line_idx
                
                if classification in ['item', 'desc']:
                    block_text, end_idx = self._assemble_item_block(line_idx, lines, classifications)
                    continuation_lines_used = end_idx - line_idx - 1
                    
                    # Process the assembled block
                    line = block_text
                    line_idx_to_use = line_idx  # Use original line index for tracking
                    
                    # Update line_idx to skip processed lines
                    line_idx = end_idx
                else:
                    # Not an item block, process single line
                    line_idx += 1
                    continue  # Skip to next iteration since we're not processing this line as an item block
                
                # Store for debug telemetry
                fuzzy_line = line  # Already fuzzy reconstructed above
                line = line.strip()
                
                # MODULE 5: Check if line is within SUBTOTAL region (for lenient heuristics)
                in_subtotal_region = False
                if items_region_subtotal:
                    start_idx, end_idx = items_region_subtotal
                    if start_idx <= line_idx_to_use < end_idx:
                        in_subtotal_region = True
                        LOGGER.debug(f"[LINE_FALLBACK] Line {line_idx_to_use} is within SUBTOTAL region, applying lenient heuristics")
                
                # Skip empty or very short lines (more lenient in SUBTOTAL region)
                min_line_len = 3 if in_subtotal_region else 5
                if not line or len(line) < min_line_len:
                    skipped_lines.append({"line_index": line_idx_to_use, "reason": "empty_or_too_short"})
                    continue
                
                line_lower = line.lower()
                
                # PHASE 5 - Module F: Two-phase SUBTOTAL stopping
                # Phase 1: Check if this is a stop keyword line
                is_stop_keyword = False
                stop_kw_found = None
                for stop_kw in stop_keywords:
                    if line_lower.startswith(stop_kw) or line_lower == stop_kw:
                        is_stop_keyword = True
                        stop_kw_found = stop_kw
                        break
                
                # Phase 2: Only stop if we have at least 1 valid item extracted
                if is_stop_keyword:
                    if len(line_items) > 0:
                        # Valid items found before SUBTOTAL - safe to stop
                        LOGGER.info(f"[LINE_FALLBACK] Stopping at line {line_idx} (found '{stop_kw_found}'): '{line[:50]}' - {len(line_items)} items extracted")
                        break
                    else:
                        # SUBTOTAL found but no items yet - might be false positive
                        # Continue parsing, but track that we saw a SUBTOTAL
                        # Stop only if we see a second SUBTOTAL or reach end of lines
                        if not hasattr(self, '_subtotal_seen_in_pass'):
                            self._subtotal_seen_in_pass = False
                        
                        if self._subtotal_seen_in_pass:
                            # Second SUBTOTAL found - stop now
                            LOGGER.info(f"[LINE_FALLBACK] Stopping at second SUBTOTAL line {line_idx}: '{line[:50]}' (no items found yet)")
                            break
                        else:
                            # First SUBTOTAL - mark it but continue
                            self._subtotal_seen_in_pass = True
                            LOGGER.debug(f"[LINE_FALLBACK] SUBTOTAL found at line {line_idx_to_use} but no items yet - continuing (might be false positive): '{line[:50]}'")
                            # Skip this line but continue processing
                            skipped_lines.append({"line_index": line_idx_to_use, "reason": "subtotal_before_items"})
                            continue
                
                # Skip header/footer lines
                should_skip = False
                skip_reason = None
                for skip_kw in skip_keywords:
                    if skip_kw in line_lower:
                        should_skip = True
                        skip_reason = f"header/meta ({skip_kw})"
                        break
                
                if should_skip:
                    skipped_lines.append({"line_index": line_idx_to_use, "reason": skip_reason or "header/meta"})
                    continue
                
                # PHASE 6 - Module 1: Use full-spectrum quantity extraction
                outer_quantity, remaining_text = self._extract_quantity_full_spectrum(line)
                qty_source = "parsed" if outer_quantity is not None else None
                
                # CRITICAL FIX: Cap excessive quantities IMMEDIATELY after extraction, before any validation
                # This prevents any downstream code from skipping the line due to excessive quantity
                if outer_quantity is not None and outer_quantity > self._max_quantity_threshold:
                    LOGGER.warning(
                        "[QUANTITY_FIX_ACTIVE] IMMEDIATE CAP: Excessive quantity %s detected at extraction, "
                        "capping to 1 for line_index=%s (pass=%s) - preventing skip",
                        outer_quantity, line_idx_to_use, pass_name
                    )
                    outer_quantity = 1
                    qty_source = "qty_capped_excessive_phase4_immediate"
                
                if outer_quantity is None:
                    # No explicit quantity found - check if this might still be a product line
                    # Hospitality heuristic: if line has drink keyword + price, assume qty=1
                    desc_lower = line_lower
                    has_drink_keyword = any(keyword in desc_lower for keyword in self._product_keywords)
                    
                    # Check if line has price-like patterns
                    price_pattern = re.compile(r'\d+\.\d{2}|\d+,\d{3}\.\d{2}|\d+\.\d{1,2}')
                    has_price = bool(price_pattern.search(line))
                    
                    # MODULE 2 + MODULE 5 + MODULE 6: Enhanced drink keyword + price heuristic with confidence adaptation and region boost
                    qty_1_evidence = strictness["qty_1_evidence_required"]
                    
                    # MODULE 5: In SUBTOTAL region, be more lenient with qty=1 assumption
                    if in_subtotal_region:
                        qty_1_evidence = "weak"  # Override to weak in region
                    
                    if has_drink_keyword and has_price:
                        # Strong evidence: drink keyword + price
                        outer_quantity = 1
                        remaining_text = line.strip()
                        qty_source = "inferred"
                        LOGGER.debug(f"[LINE_FALLBACK] Assuming qty=1 for line with drink keyword but no explicit qty: '{line[:50]}'")
                    elif has_drink_keyword and qty_1_evidence in ("weak", "medium"):
                        # Weak/medium evidence: drink keyword only (if strictness allows)
                        outer_quantity = 1
                        remaining_text = line.strip()
                        qty_source = "inferred"
                        LOGGER.debug(f"[LINE_FALLBACK] Assuming qty=1 for line with drink keyword (no price pattern yet, evidence={qty_1_evidence}): '{line[:50]}'")
                    elif in_subtotal_region and has_price:
                        # MODULE 5: In SUBTOTAL region, accept qty=1 with just price (no keyword needed)
                        outer_quantity = 1
                        remaining_text = line.strip()
                        qty_source = "inferred"
                        LOGGER.debug(f"[LINE_FALLBACK] Assuming qty=1 in SUBTOTAL region with price but no keyword: '{line[:50]}'")
                    else:
                        # PHASE 6 - Module 5: Try fallback parsing strategies
                        fallback_item = None
                        
                        # Try wide_net_parsing first
                        fallback_item = self._wide_net_parsing(line)
                        if fallback_item:
                            LOGGER.debug(f"[LINE_FALLBACK] Fallback wide_net_parsing succeeded for line: '{line[:50]}'")
                        else:
                            # Try token_pairing_parsing
                            fallback_item = self._token_pairing_parsing(line)
                            if fallback_item:
                                LOGGER.debug(f"[LINE_FALLBACK] Fallback token_pairing_parsing succeeded for line: '{line[:50]}'")
                            else:
                                # Try pure_description_price_parsing
                                fallback_item = self._pure_description_price_parsing(line)
                                if fallback_item:
                                    LOGGER.debug(f"[LINE_FALLBACK] Fallback pure_description_price_parsing succeeded for line: '{line[:50]}'")
                        
                        if fallback_item:
                            # Add debug telemetry
                            fallback_item.cell_data.update({
                                "source_line": source_line,
                                "fuzzy_line": fuzzy_line,
                                "classification": classification,
                                "continuation_lines_used": continuation_lines_used,
                                "qty_source": "defaulted",
                                "price_source": "parsed" if fallback_item.total_price else "none"
                            })
                            line_items.append(fallback_item)
                            continue
                        
                        # No quantity and doesn't look like a product line, and fallback strategies failed
                        skipped_lines.append({
                            "line_index": line_idx_to_use,
                            "reason": "no_qty_pattern",
                            "detail": "No quantity pattern found and all fallback strategies failed"
                        })
                        continue
                
                # Parse qty and pack size from remaining text
                # Note: parse_qty_and_pack_size may return a quantity, but we want to use outer_quantity
                parsed_qty, pack_size, cleaned_description = self.parse_qty_and_pack_size(remaining_text)
                
                # Always use outer_quantity as the quantity (first number in line, or assumed 1)
                # NOTE: outer_quantity may have already been capped above if excessive
                quantity = outer_quantity
                
                # DEFENSIVE: Final safety check - ensure quantity never exceeds threshold
                # This is a last-resort safeguard in case any code path missed the earlier cap
                if quantity is not None and quantity > self._max_quantity_threshold:
                    LOGGER.error(
                        "[QUANTITY_FIX_ACTIVE] DEFENSIVE CAP: Quantity %s still exceeds threshold after extraction cap! "
                        "Capping to 1 for line_index=%s (pass=%s)",
                        quantity, line_idx_to_use, pass_name
                    )
                    quantity = 1
                    qty_source = "qty_capped_excessive_phase4_defensive"
                
                # Use cleaned description if pack_size was found, otherwise use remaining_text
                if pack_size is not None:
                    description = cleaned_description if cleaned_description else remaining_text
                else:
                    # No pack size pattern found, use remaining text as description
                    description = cleaned_description if cleaned_description else remaining_text
                
                # PHASE 4 - Module A: Use desc_window to focus description extraction
                if use_structure_guidance and line_structure.get("desc_window"):
                    desc_window = line_structure["desc_window"]
                    tokens = line.split()
                    if len(tokens) > desc_window[0]:
                        # Extract description from desc_window region
                        start_idx = desc_window[0]
                        end_idx = desc_window[1] if desc_window[1] > 0 else len(tokens)
                        if end_idx > start_idx:
                            desc_tokens = tokens[start_idx:end_idx]
                            windowed_desc = " ".join(desc_tokens)
                            # Use windowed description if it's substantial, otherwise keep original
                            if len(windowed_desc.strip()) >= 3:
                                description = windowed_desc
                                LOGGER.debug(f"[LINE_FALLBACK] Used structure-guided description window: '{description[:50]}'")
                
                # MODULE 4: Clean description - strip leading garbage, normalize spaces
                description = self._clean_description(description)
                
                # TRACE: Log quantity before check
                LOGGER.warning(
                    "[QUANTITY_TRACE] Line %s: quantity=%s, threshold=%s, checking if excessive",
                    line_idx_to_use, quantity, self._max_quantity_threshold
                )
                
                # Quantity sanity filter: treat excessive quantity as soft warning, not hard skip
                # CHANGED: Previously this would skip lines with excessive quantities (> 100), creating
                # "excessive_quantity (X)" skip reasons. Now we salvage these lines by setting qty=1
                # and continuing to build the line item. This ensures we always extract at least one
                # item for single-line invoices instead of returning empty results.
                if quantity is not None and quantity > self._max_quantity_threshold:
                    # CHANGED: Instead of skipping, cap the quantity and log a warning
                    original_quantity = quantity
                    quantity = 1  # Cap to safe value instead of skipping
                    qty_source = "qty_capped_excessive_phase4"

                    # Log the capping action with VERY obvious tag
                    LOGGER.warning(
                        "[QUANTITY_FIX_ACTIVE] Capping excessive quantity %s to %s for line_index=%s (pass=%s)",
                        original_quantity, quantity, line_idx_to_use, pass_name
                    )

                    # Mark in cell_data for debugging
                    if 'inference_notes' not in locals():
                        inference_notes = []
                    inference_notes.append(f"quantity_out_of_range_original={original_quantity}, using_fallback_qty=1")

                    # CRITICAL: Do NOT skip - continue building the item (DO NOT add to skipped_lines)
                    # This ensures we always extract at least one item for single-line invoices
                
                # Extract prices from the end of the line using improved pattern
                # FIX: Pass pack_size to exclude pack size numbers from price extraction
                unit_price_val, line_total_val = self._extract_prices_from_line_end(line, pack_size=pack_size)
                
                # PHASE 5 - Module E: Early unit price inference
                # If only line_total exists and we have quantity, infer unit_price
                if line_total_val is not None and unit_price_val is None and quantity > 0:
                    try:
                        computed_unit = line_total_val / quantity
                        # Validate: reasonable unit price (0 < unit_price < 15000)
                        if 0 < computed_unit < 15000:
                            unit_price_val = computed_unit
                            # PHASE 6: Track inference
                            if 'inference_notes' not in locals():
                                inference_notes = []
                            inference_notes.append(f"Early inference: unit_price = {line_total_val:.2f} / {quantity} = {computed_unit:.2f}")
                            LOGGER.debug(f"[LINE_FALLBACK] Early inference: unit_price = {line_total_val:.2f} / {quantity} = {computed_unit:.2f}")
                    except (ZeroDivisionError, ValueError, TypeError):
                        pass  # Skip if calculation fails

                # PHASE 5 - Module E2: If prices are still missing, derive from all price tokens on the line
                if (unit_price_val is None or line_total_val is None):
                    price_tokens = re.findall(r'\d+[.,]\d{2}', line)
                    prices_clean = []
                    for pt in price_tokens:
                        try:
                            prices_clean.append(float(pt.replace(',', '')))
                        except ValueError:
                            continue
                    if prices_clean:
                        prices_sorted = sorted(prices_clean)
                        if unit_price_val is None:
                            unit_price_val = prices_sorted[0]
                        if line_total_val is None and len(prices_sorted) > 1:
                            line_total_val = prices_sorted[-1]
                        # Infer quantity from unit/total if plausible and qty not already >1
                        if unit_price_val and line_total_val and (quantity is None or quantity == 1):
                            inferred_qty = round(line_total_val / unit_price_val)
                            if 1 <= inferred_qty <= self._max_quantity_threshold:
                                # accept if within 10% tolerance
                                if abs(line_total_val - inferred_qty * unit_price_val) / max(line_total_val, 1) < 0.1:
                                    quantity = inferred_qty
                                    qty_source = "inferred_from_prices"
                                    if 'inference_notes' not in locals():
                                        inference_notes = []
                                    inference_notes.append(f"Qty inferred from prices: total {line_total_val:.2f} / unit {unit_price_val:.2f} = {inferred_qty}")
                
                # PHASE 4 - Module A: Validate price position using structure guidance
                if use_structure_guidance and line_structure.get("price_pos") is not None:
                    # Count tokens from right to find price position
                    tokens = line.split()
                    price_pos_from_right = None
                    if line_total_val is not None or unit_price_val is not None:
                        # Find rightmost price in tokens
                        for i in range(len(tokens) - 1, -1, -1):
                            token = tokens[i]
                            # Check if this token contains the price
                            if line_total_val and str(line_total_val) in token.replace(',', ''):
                                price_pos_from_right = len(tokens) - 1 - i
                                break
                            elif unit_price_val and str(unit_price_val) in token.replace(',', ''):
                                price_pos_from_right = len(tokens) - 1 - i
                                break
                        
                        expected_price_pos = line_structure.get("price_pos")
                        # Allow tolerance of 1 token position
                        if price_pos_from_right is not None and abs(price_pos_from_right - expected_price_pos) > 1:
                            LOGGER.debug(f"[LINE_FALLBACK] Price position mismatch: expected={expected_price_pos}, found={price_pos_from_right}, "
                                       f"but keeping prices (structure guidance is advisory)")
                        # Note: We keep the prices even if position doesn't match (structure is advisory)
                
                unit_price = None
                line_total = None
                
                if unit_price_val is not None:
                    unit_price = f"{unit_price_val:.2f}"
                if line_total_val is not None:
                    line_total = f"{line_total_val:.2f}"
                
                # PHASE 5 - Module A: Confidence-scaled tolerance-based price validation
                # This catches cases where we extracted wrong numbers (e.g., pack size as price)
                # Tolerance scales with OCR confidence: higher confidence = stricter tolerance
                if unit_price_val is not None and line_total_val is not None and quantity > 0:
                    expected_total = quantity * unit_price_val
                    
                    # Scale tolerance based on base_confidence
                    if base_confidence >= 0.85:
                        # High confidence: 5% tolerance
                        percentage_tolerance = 0.05
                        rejection_threshold = 0.20  # 20% mismatch threshold
                    elif base_confidence >= 0.70:
                        # Medium confidence: 10% tolerance
                        percentage_tolerance = 0.10
                        rejection_threshold = 0.25  # 25% mismatch threshold
                    else:
                        # Low confidence: 15% tolerance
                        percentage_tolerance = 0.15
                        rejection_threshold = 0.30  # 30% mismatch threshold
                    
                    # Calculate absolute tolerance (minimum £0.10)
                    tolerance = max(0.10, expected_total * percentage_tolerance)
                    mismatch_abs = abs(line_total_val - expected_total)
                    mismatch_percent = (mismatch_abs / expected_total) if expected_total > 0 else 0.0
                    
                    if mismatch_abs > tolerance:
                        # Mismatch detected - likely extracted wrong numbers
                        LOGGER.warning(
                            f"[LINE_FALLBACK] Price mismatch detected: qty={quantity}, "
                            f"unit={unit_price_val}, total={line_total_val}, expected={expected_total:.2f}, "
                            f"mismatch={mismatch_abs:.2f} ({mismatch_percent*100:.1f}%), "
                            f"tolerance={tolerance:.2f} ({percentage_tolerance*100:.0f}% @ conf={base_confidence:.2f}) "
                            f"(line: '{line[:60]}')"
                        )
                        # If mismatch exceeds rejection threshold, reject both prices
                        if mismatch_percent > rejection_threshold:
                            LOGGER.debug(f"[LINE_FALLBACK] Rejecting mismatched prices (mismatch {mismatch_percent*100:.1f}% > threshold {rejection_threshold*100:.0f}%)")
                            unit_price = None
                            line_total = None
                            unit_price_val = None
                            line_total_val = None
                        # If mismatch is smaller, keep total_price but clear unit_price
                        # (total_price is usually more reliable)
                        else:
                            LOGGER.debug(f"[LINE_FALLBACK] Keeping total_price, clearing unit_price due to mismatch (within rejection threshold)")
                            unit_price = None
                            unit_price_val = None
                
                # Reject tiny totals when description looks like a big-ticket item (e.g. keg)
                desc_lower = description.lower()
                if "keg" in desc_lower and line_total_val is not None and line_total_val < 20:
                    LOGGER.debug(f"[LINE_FALLBACK] Rejecting keg with suspiciously low total: {line_total_val} (line: '{line[:50]}')")
                    skipped_lines.append({"line_index": line_idx_to_use, "reason": "suspiciously_low_total"})
                    continue

                # If quantity is missing/1, try to capture an explicit integer before the first price token
                if quantity is None or quantity == 1:
                    first_price_match = re.search(r'\d+[.,]\d{2}', line)
                    first_price_start = first_price_match.start() if first_price_match else len(line)
                    qty_token = None
                    for m in re.finditer(r'\b(\d{1,3})\b', line):
                        if m.start() < first_price_start:
                            try:
                                cand = int(m.group(1))
                                if 1 <= cand <= 100:
                                    qty_token = cand
                                    break
                            except ValueError:
                                continue
                    if qty_token and (quantity is None or quantity == 1):
                        quantity = qty_token
                        qty_source = "inferred_from_line_integer"

                # If prices exist but one is missing, back-fill from qty
                if quantity and quantity > 0:
                    if unit_price_val is not None and line_total_val is None:
                        line_total_val = unit_price_val * quantity
                    elif line_total_val is not None and unit_price_val is None:
                        unit_price_val = line_total_val / quantity
                
                # Check if this line is header/meta before creating LineItem
                price_value_for_check = line_total_val if line_total_val is not None else unit_price_val
                if self._is_header_or_meta_description(description, price_value=price_value_for_check, line_index=line_idx_to_use):
                    LOGGER.debug(f"[LINE_FALLBACK] Skipping header/meta line: '{line[:50]}'")
                    skipped_lines.append({"line_index": line_idx_to_use, "reason": "header/meta"})
                    continue
                
                # MODULE 5 + MODULE 6: Validate description with confidence-adaptive thresholds and region boost
                min_desc_len = strictness["min_description_length"]
                # MODULE 5: More lenient in SUBTOTAL region
                if in_subtotal_region:
                    min_desc_len = max(3, min_desc_len - 1)  # Reduce by 1, but not below 3
                # PHASE 4 - Module B: More lenient in lenient_mode
                if lenient_mode:
                    min_desc_len = max(2, min_desc_len - 2)  # Reduce by 2 in lenient mode
                
                if not description or len(description) < min_desc_len:
                    # MODULE 8: Enhanced skip reason with context
                    reason = f"invalid_description (len < {min_desc_len})"
                    if in_subtotal_region:
                        reason = f"invalid_description_in_subtotal_region (len < {min_desc_len})"
                    skipped_lines.append({"line_index": line_idx_to_use, "reason": reason})
                    continue
                
                if strictness["require_alphabetic"] and not re.search(r'[A-Za-z]', description):
                    # MODULE 8: Enhanced skip reason
                    reason = "no_alphabetic_chars"
                    if base_confidence >= 0.90:
                        reason = "low_confidence_strict_reject_no_alphabetic"
                    skipped_lines.append({"line_index": line_idx_to_use, "reason": reason})
                    continue
                
                # MODULE 6: Product keyword bias with confidence-adaptive thresholds
                has_product_keyword = any(keyword in desc_lower for keyword in self._product_keywords)
                min_price = strictness["min_price_threshold"]
                max_price = strictness["max_price_threshold"]
                has_valid_prices = (
                    unit_price_val is not None and 
                    line_total_val is not None and
                    min_price < unit_price_val < max_price and
                    min_price < line_total_val < max_price
                )
                
                # Apply strictness rules
                require_keyword = strictness["require_product_keyword"]
                # PHASE 4 - Module B: Disable keyword requirement in lenient_mode
                if lenient_mode:
                    require_keyword = False
                if require_keyword and not has_product_keyword:
                    # MODULE 8: Enhanced skip reason
                    reason = "no_product_keyword_required"
                    if base_confidence >= 0.90:
                        reason = "low_confidence_strict_reject_no_keyword"
                    skipped_lines.append({"line_index": line_idx_to_use, "reason": reason})
                    continue
                
                if not has_product_keyword and not has_valid_prices:
                    # MODULE 8: Enhanced skip reason
                    reason = "no_price_pattern"
                    if in_subtotal_region:
                        reason = "no_price_pattern_in_subtotal_region"
                    LOGGER.debug(f"[LINE_FALLBACK] Rejecting line without product keyword or valid prices: '{line[:50]}'")
                    skipped_lines.append({"line_index": line_idx_to_use, "reason": reason})
                    continue
                
                # MODULE 6: Calculate confidence based on fields found, with confidence boost
                found_fields = sum(1 for field in [quantity, description, unit_price, line_total] if field)
                base_item_confidence = min(0.9, 0.6 + (found_fields * 0.1))
                confidence = base_item_confidence * strictness["confidence_boost"]
                
                # MODULE 1: Boost confidence if price grid detected and we have prices
                if price_grid and (unit_price or line_total) and price_grid.get("confidence", 0) > 0.6:
                    grid_boost = 1.0 + (price_grid["confidence"] - 0.6) * 0.1  # Up to 4% boost
                    confidence = min(0.95, confidence * grid_boost)
                    LOGGER.debug(f"[LINE_FALLBACK] Applied price grid confidence boost: {grid_boost:.3f}")
                
                # PHASE 6 - Module 7: Create line item with comprehensive debug telemetry
                # Determine price_source
                price_source = "parsed"
                if unit_price_val is None and line_total_val is None:
                    price_source = "none"
                elif unit_price_val is not None and line_total_val is None:
                    price_source = "parsed_unit_only"
                elif unit_price_val is None and line_total_val is not None:
                    price_source = "parsed_total_only"
                
                # Initialize inference_notes (will be updated if inferences occur)
                if 'inference_notes' not in locals():
                    inference_notes = []
                
                cell_data = {
                    "line_index": line_idx_to_use,
                    "raw_line": line,
                    "source_line": source_line if 'source_line' in locals() else line,
                    "fuzzy_line": fuzzy_line if 'fuzzy_line' in locals() else line,
                    "classification": classification if 'classification' in locals() else 'unknown',
                    "method": "line_fallback",
                    "pass": pass_name,
                    "qty_source": qty_source if 'qty_source' in locals() else "parsed",
                    "price_source": price_source,
                    "continuation_lines_used": continuation_lines_used if 'continuation_lines_used' in locals() else 0,
                    "inference_notes": inference_notes,
                    "structure_confidence": line_structure.get("confidence", 0.0) if line_structure else 0.0
                }
                # PHASE 4 - Module D: Mark supplier pattern application if used
                if supplier_pattern_applied:
                    cell_data["supplier_pattern_applied"] = supplier_pattern_applied
                
                line_item = LineItem(
                    description=description,
                    quantity=str(quantity),  # Convert to string for consistency
                    unit_price=unit_price or "",
                    total_price=line_total or "",
                    vat="",
                    confidence=confidence,
                    row_index=len(line_items),
                    cell_data=cell_data,
                    pack_size=pack_size
                )
                
                # ENHANCEMENT 6: Improved price backfill logic
                # Backfill total_price from qty × unit_price if missing
                if line_item.quantity and line_item.unit_price and not line_item.total_price:
                    try:
                        qty_val = float(line_item.quantity)
                        unit_str = line_item.unit_price.replace('£', '').replace('$', '').replace('€', '').replace(',', '').strip()
                        unit_val = float(unit_str)
                        
                        # Safety checks: reasonable values only
                        # ENHANCEMENT: Relaxed upper bound for unit_price (10,000 → 15,000)
                        if qty_val > 0 and unit_val > 0 and qty_val <= 100 and unit_val < 15000:
                            computed_total = qty_val * unit_val
                            # Skip if computed total would be unreasonably large
                            if computed_total < 100000:
                                line_item.total_price = f"{computed_total:.2f}"
                                # Mark in cell_data for debugging
                                if not line_item.cell_data:
                                    line_item.cell_data = {}
                                line_item.cell_data["price_backfill"] = "computed_total_from_qty_unit"
                                line_item.cell_data["price_source"] = "inferred"
                                if "inference_notes" not in line_item.cell_data:
                                    line_item.cell_data["inference_notes"] = []
                                line_item.cell_data["inference_notes"].append(f"Backfilled total_price: {qty_val} × {unit_val} = {computed_total:.2f}")
                                # Slightly lower confidence for backfilled prices
                                line_item.confidence = confidence * 0.95
                                LOGGER.debug(f"[LINE_FALLBACK] Backfilled total_price: {qty_val} × {unit_val} = {computed_total:.2f}")
                    except (ValueError, TypeError, AttributeError):
                        pass  # Skip if values can't be parsed
                
                # PHASE 4 - Module C: Price-Reconciliation Engine v2 (with error handling)
                # Enhanced price mapping logic
                try:
                    line_item = self._reconcile_prices_v2(line_item, strictness)
                except Exception as e:
                    LOGGER.warning(f"[LINE_FALLBACK] Price reconciliation failed for item: {e}", exc_info=True)
                    # Return original item on failure, mark in cell_data
                    if line_item.cell_data:
                        line_item.cell_data["phase4_failure"] = "price_reconciliation"
                    # Continue with original item
                
                # PHASE 5 - Module E: Try to infer unit_price from total_price and qty if missing (fallback)
                # This helps when invoice shows totals but not unit prices
                # Note: Early inference already attempted above, this is a fallback for edge cases
                if line_item.quantity and line_item.total_price and not line_item.unit_price:
                    try:
                        qty_val = float(line_item.quantity)
                        total_str = line_item.total_price.replace('£', '').replace('$', '').replace('€', '').replace(',', '').strip()
                        total_val = float(total_str)
                        
                        # Safety checks: reasonable values only
                        if qty_val > 0 and total_val > 0 and qty_val <= 100 and total_val < 100000:
                            computed_unit = total_val / qty_val
                            # Only accept if unit price is reasonable (< 15,000)
                            if 0 < computed_unit < 15000:
                                line_item.unit_price = f"{computed_unit:.2f}"
                                # Mark in cell_data for debugging
                                if not line_item.cell_data:
                                    line_item.cell_data = {}
                                line_item.cell_data["price_backfill"] = "computed_unit_from_qty_total"
                                line_item.cell_data["inferred_unit_price"] = True  # PHASE 5: Mark as inferred
                                line_item.cell_data["price_source"] = "inferred"
                                if "inference_notes" not in line_item.cell_data:
                                    line_item.cell_data["inference_notes"] = []
                                line_item.cell_data["inference_notes"].append(f"Backfilled unit_price (fallback): {total_val} / {qty_val} = {computed_unit:.2f}")
                                # Slightly lower confidence for backfilled prices (0.05 reduction)
                                line_item.confidence = max(0.5, confidence - 0.05)
                                LOGGER.debug(f"[LINE_FALLBACK] Backfilled unit_price (fallback): {total_val} / {qty_val} = {computed_unit:.2f}")
                    except (ValueError, TypeError, AttributeError, ZeroDivisionError):
                        pass  # Skip if values can't be parsed
                
                line_items.append(line_item)
                LOGGER.debug(f"[LINE_FALLBACK] [{pass_name}] Extracted item {len(line_items)}: qty={quantity}, pack_size={pack_size}, desc='{description[:50]}...', unit={line_item.unit_price}, total={line_item.total_price}")
        except Exception as e:
            extraction_error = str(e)
            LOGGER.error(f"[LINE_FALLBACK] [{pass_name}] Extraction loop failed at line_idx={line_idx}: {e}", exc_info=True)
            # Continue - we'll return what we have so far
        
        if extraction_error:
            LOGGER.warning(f"[LINE_FALLBACK] [{pass_name}] Extraction completed with error: {extraction_error}")
        
        LOGGER.info(f"[LINE_FALLBACK] [{pass_name}] Extracted {len(line_items)} line items from {len(lines)} lines, skipped {len(skipped_lines)} lines")
        
        # Mark pass name in cell_data for all items
        for item in line_items:
            if item.cell_data:
                item.cell_data["pass"] = pass_name
        
        return (line_items, skipped_lines)
    
    def _combine_multi_pass_results(self, items_pass1: List[LineItem], items_pass2: List[LineItem], items_pass3: List[LineItem], skipped_pass1: List[Dict], skipped_pass2: List[Dict], skipped_pass3: List[Dict]) -> Tuple[List[LineItem], List[Dict[str, Any]], str]:
        """
        PHASE 4 - Module B + PHASE 6 - Module 7: Combine results from 3 passes.
        
        Strategy:
        - Keep highest confidence row per raw line (by line_index)
        - Merge prices if one pass found unit_price and another found total_price
        - Combine skipped_lines with deduplication
        
        Args:
            items_pass1/2/3: Line items from each pass
            skipped_pass1/2/3: Skipped lines from each pass
            
        Returns:
            Tuple of (combined_items, combined_skipped, final_method)
            final_method indicates which pass contributed most items
        """
        # Group items by line_index (raw line they came from)
        items_by_line: Dict[int, List[LineItem]] = defaultdict(list)
        
        for item in items_pass1 + items_pass2 + items_pass3:
            line_idx = item.cell_data.get("line_index")
            if line_idx is not None:
                items_by_line[line_idx].append(item)
        
        combined_items = []
        processed_lines = set()
        
        # For each line, pick the best item (highest confidence)
        # Sort by line_idx for deterministic output
        for line_idx, candidates in sorted(items_by_line.items(), key=lambda x: x[0]):
            if not candidates:
                continue
            
            # Sort by confidence (descending)
            candidates.sort(key=lambda x: x.confidence, reverse=True)
            best_item = candidates[0]
            
            # Try to merge prices from other candidates
            for candidate in candidates[1:]:
                # If best has unit but not total, and candidate has total, merge
                if best_item.unit_price and not best_item.total_price and candidate.total_price:
                    best_item.total_price = candidate.total_price
                    best_item.cell_data["price_merged_from_pass"] = candidate.cell_data.get("pass", "unknown")
                    LOGGER.debug(f"[MULTI_PASS] Merged total_price from pass {candidate.cell_data.get('pass')} for line {line_idx}")
                # If best has total but not unit, and candidate has unit, merge
                elif best_item.total_price and not best_item.unit_price and candidate.unit_price:
                    best_item.unit_price = candidate.unit_price
                    best_item.cell_data["price_merged_from_pass"] = candidate.cell_data.get("pass", "unknown")
                    LOGGER.debug(f"[MULTI_PASS] Merged unit_price from pass {candidate.cell_data.get('pass')} for line {line_idx}")
            
            combined_items.append(best_item)
            processed_lines.add(line_idx)
        
        # Combine skipped lines (deduplicate by line_index)
        skipped_by_line: Dict[int, Dict] = {}
        for skipped in skipped_pass1 + skipped_pass2 + skipped_pass3:
            line_idx = skipped.get("line_index")
            if line_idx is not None and line_idx not in processed_lines:
                # Keep the most specific reason
                if line_idx not in skipped_by_line:
                    skipped_by_line[line_idx] = skipped
                else:
                    # Prefer more specific reasons
                    existing_reason = skipped_by_line[line_idx].get("reason", "")
                    new_reason = skipped.get("reason", "")
                    if len(new_reason) > len(existing_reason):
                        skipped_by_line[line_idx] = skipped
        
        # Sort skipped lines by line_index for deterministic output
        combined_skipped = sorted(skipped_by_line.values(), key=lambda x: x.get("line_index", 0))
        
        # PHASE 6: Determine final_method (which pass contributed most items)
        pass_counts = {
            "strict": len([item for item in combined_items if item.cell_data.get("pass") == "strict"]),
            "standard": len([item for item in combined_items if item.cell_data.get("pass") == "standard"]),
            "lenient": len([item for item in combined_items if item.cell_data.get("pass") == "lenient"])
        }
        final_method = max(pass_counts.items(), key=lambda x: x[1])[0] if pass_counts else "standard"
        
        LOGGER.info(f"[MULTI_PASS] Combined: {len(combined_items)} items from {len(processed_lines)} lines, {len(combined_skipped)} skipped, final_method={final_method}")
        return (combined_items, combined_skipped, final_method)
    
    def _reconcile_prices_v2(self, line_item: LineItem, strictness: Dict[str, Any]) -> LineItem:
        """
        PHASE 4 - Module C: Price-Reconciliation Engine v2
        
        Enhanced price mapping logic:
        - If line has quantity and two prices: map smaller as unit_price, larger as total_price
        - If line has one price and quantity > 1: compute inferred_unit = price / qty
        - Validate inferred prices against known norms
        
        Args:
            line_item: LineItem to reconcile
            strictness: Parsing strictness config
            
        Returns:
            LineItem with reconciled prices and debug info
        """
        if not line_item.cell_data:
            line_item.cell_data = {}
        
        try:
            qty_str = line_item.quantity
            unit_str = line_item.unit_price or ""
            total_str = line_item.total_price or ""
            
            # Parse quantities and prices
            qty_val = None
            if qty_str:
                qty_val = float(str(qty_str).replace(',', '').strip())
            
            unit_val = None
            if unit_str:
                unit_val = float(str(unit_str).replace('£', '').replace('$', '').replace('€', '').replace(',', '').strip())
            
            total_val = None
            if total_str:
                total_val = float(str(total_str).replace('£', '').replace('$', '').replace('€', '').replace(',', '').strip())
            
            # Case 1: Two prices present - map smaller as unit, larger as total
            if unit_val is not None and total_val is not None and qty_val and qty_val > 0:
                if unit_val > total_val:
                    # Swap if unit > total (likely mis-assigned)
                    line_item.unit_price = f"{total_val:.2f}"
                    line_item.total_price = f"{unit_val:.2f}"
                    line_item.cell_data["price_inference"] = "swapped_unit_total"
                    LOGGER.debug(f"[PRICE_RECONCILE] Swapped prices: unit={total_val:.2f}, total={unit_val:.2f}")
                else:
                    # Validate: unit * qty should approximately equal total
                    expected_total = unit_val * qty_val
                    tolerance = max(0.10, expected_total * 0.05)  # 5% tolerance
                    if abs(total_val - expected_total) > tolerance:
                        # Mismatch - mark but keep both prices
                        line_item.cell_data["price_inference"] = "unit_total_mismatch"
                        LOGGER.debug(f"[PRICE_RECONCILE] Price mismatch: unit={unit_val:.2f}, qty={qty_val}, "
                                   f"total={total_val:.2f}, expected={expected_total:.2f}")
                    else:
                        line_item.cell_data["price_inference"] = "valid_unit_total"
            
            # Case 2: One price + quantity > 1 - infer unit price
            elif (unit_val is None and total_val is not None and qty_val and qty_val > 1) or \
                 (total_val is None and unit_val is not None and qty_val and qty_val > 1):
                
                price_val = total_val if total_val is not None else unit_val
                inferred_unit = price_val / qty_val
                
                # Validate against known soft-drink norms (typical unit prices: £0.50 - £15.00)
                # Allow wider range for hospitality: £0.20 - £50.00
                min_unit = 0.20
                max_unit = 50.00
                
                if min_unit <= inferred_unit <= max_unit:
                    if total_val is not None:
                        # We have total, inferred unit
                        line_item.unit_price = f"{inferred_unit:.2f}"
                        line_item.cell_data["price_inference"] = "unit_from_total"
                        LOGGER.debug(f"[PRICE_RECONCILE] Inferred unit: {total_val:.2f} / {qty_val} = {inferred_unit:.2f}")
                    else:
                        # We have unit, inferred total
                        inferred_total = unit_val * qty_val
                        if inferred_total < 100000:  # Sanity check
                            line_item.total_price = f"{inferred_total:.2f}"
                            line_item.cell_data["price_inference"] = "total_from_unit"
                            LOGGER.debug(f"[PRICE_RECONCILE] Inferred total: {unit_val:.2f} * {qty_val} = {inferred_total:.2f}")
                else:
                    # Suspicious price - mark but keep
                    line_item.cell_data["price_inference"] = "suspicious_inferred_price"
                    LOGGER.debug(f"[PRICE_RECONCILE] Suspicious inferred price: {inferred_unit:.2f} (outside normal range)")
            
            # Case 3: One price, qty = 1 - could be either unit or total
            elif (unit_val is None or total_val is None) and qty_val == 1:
                price_val = total_val if total_val is not None else unit_val
                if price_val is not None:
                    # For qty=1, unit and total are the same
                    if total_val is None:
                        line_item.total_price = f"{price_val:.2f}"
                        line_item.cell_data["price_inference"] = "total_from_unit_qty1"
                    else:
                        line_item.unit_price = f"{price_val:.2f}"
                        line_item.cell_data["price_inference"] = "unit_from_total_qty1"
            
            # Case 4: No valid inference possible
            else:
                line_item.cell_data["price_inference"] = "invalid"
        
        except (ValueError, TypeError, AttributeError, ZeroDivisionError) as e:
            LOGGER.debug(f"[PRICE_RECONCILE] Error reconciling prices: {e}")
            if not line_item.cell_data.get("price_inference"):
                line_item.cell_data["price_inference"] = "error"
        
        return line_item
    
    def _learn_supplier_patterns(self, supplier_name: str, line_items: List[LineItem], skipped_lines: List[Dict[str, Any]]) -> None:
        """
        PHASE 4 - Module D: Supplier-Specific Template Learning
        
        Learn patterns from successful extractions and store in cache.
        
        Args:
            supplier_name: Supplier name (should be normalized)
            line_items: Successfully extracted line items
            skipped_lines: Skipped lines with reasons
        """
        # PHASE 4 - Module D: Validate and normalize supplier name
        if not supplier_name:
            return
        
        # Normalize supplier name (strip, lowercase, limit length)
        supplier_name = supplier_name.strip().lower()[:100]
        if not supplier_name or len(supplier_name) < 2:  # Reject too short names
            return
        
        if not line_items:
            return
        
        # Use safe dict access - initialize if not exists
        if supplier_name not in self._supplier_patterns:
            self._supplier_patterns[supplier_name] = {
                "extraction_count": 0,
                "avg_confidence": 0.0,
                "avg_tokens_per_line": 0.0,
                "pack_size_patterns": [],
                "common_price_alignment": None,
                "successful_patterns": defaultdict(int),
                "failed_patterns": defaultdict(int)
            }
        
        patterns = self._supplier_patterns[supplier_name]
        patterns["extraction_count"] += len(line_items)
        
        # Update average confidence
        if line_items:
            avg_conf = sum(item.confidence for item in line_items) / len(line_items)
            old_count = patterns["extraction_count"] - len(line_items)
            if old_count > 0:
                patterns["avg_confidence"] = (patterns["avg_confidence"] * old_count + avg_conf * len(line_items)) / patterns["extraction_count"]
            else:
                patterns["avg_confidence"] = avg_conf
        
        # Learn pack-size patterns
        pack_sizes = [item.pack_size for item in line_items if item.pack_size]
        for pack_size in pack_sizes:
            if pack_size not in patterns["pack_size_patterns"]:
                patterns["pack_size_patterns"].append(pack_size)
        
        # Learn token patterns from successful extractions
        for item in line_items:
            if item.cell_data and "raw_line" in item.cell_data:
                raw_line = item.cell_data["raw_line"]
                tokens = raw_line.split()
                patterns["avg_tokens_per_line"] = (patterns["avg_tokens_per_line"] * (patterns["extraction_count"] - 1) + len(tokens)) / patterns["extraction_count"]
        
        # Track successful vs failed patterns from skipped lines
        for skipped in skipped_lines:
            reason = skipped.get("reason", "unknown")
            patterns["failed_patterns"][reason] += 1
        
        LOGGER.debug(f"[SUPPLIER_PATTERNS] Updated patterns for {supplier_name}: {len(line_items)} items, avg_conf={patterns['avg_confidence']:.3f}")
    
    def _get_supplier_pattern_adjustments(self, supplier_name: str) -> Dict[str, Any]:
        """
        PHASE 4 - Module D: Get pattern-based adjustments for a supplier.
        
        Returns adjustments to thresholds based on learned patterns.
        """
        if not supplier_name:
            return {}
        
        # Use safe dict access with default empty dict
        patterns = self._supplier_patterns.get(supplier_name, {})
        if not patterns:
            return {}
        adjustments = {}
        
        # Lower thresholds for patterns that repeatedly matched
        # Increase strictness for patterns that never matched
        if patterns["extraction_count"] > 5:  # Need some data
            # Adjust confidence threshold based on historical success
            if patterns["avg_confidence"] > 0.8:
                adjustments["confidence_boost"] = 1.05  # Slight boost for reliable suppliers
            elif patterns["avg_confidence"] < 0.6:
                adjustments["confidence_boost"] = 0.95  # Slight reduction for unreliable suppliers
        
        return adjustments
    
    def _score_extraction(
        self,
        items: List[LineItem],
        base_confidence: float,
        method_name: str,
    ) -> float:
        """
        Score an extraction method based on quality metrics.
        
        Scoring model:
        score = (n_items * 2.0)
              + (avg_confidence * 1.0)
              + (items_with_pack_size * 0.5)
              + (items_with_prices * 0.75)
              + format_stability_bonus (+1.0 if no header/meta/postcode patterns)
        
        Args:
            items: List of extracted LineItem objects
            base_confidence: Base confidence value if items have no confidence
            method_name: Name of the extraction method (for logging)
            
        Returns:
            Float score (higher is better)
        """
        if not items:
            return 0.0
        
        n_items = len(items)
        
        # Calculate average confidence
        confidences = [item.confidence for item in items if item.confidence > 0]
        if confidences:
            avg_confidence = sum(confidences) / len(confidences)
        else:
            avg_confidence = base_confidence
        
        # Count items with pack_size
        items_with_pack_size = sum(1 for item in items if item.pack_size is not None and item.pack_size.strip())
        
        # Count items with prices (unit_price or total_price)
        items_with_prices = sum(
            1 for item in items 
            if (item.unit_price and item.unit_price.strip()) or (item.total_price and item.total_price.strip())
        )
        
        # Format stability bonus: +1.0 if no header/meta/postcode patterns appear
        format_stability_bonus = 0.0
        has_header_meta = False
        for item in items:
            price_value = None
            if item.total_price:
                try:
                    # Try to parse price value for validation
                    price_str = item.total_price.replace('£', '').replace('$', '').replace('€', '').replace(',', '').strip()
                    price_value = float(price_str) if price_str else None
                except (ValueError, TypeError):
                    pass
            
            if self._is_header_or_meta_description(item.description, price_value):
                has_header_meta = True
                break
        
        if not has_header_meta:
            format_stability_bonus = 1.0
        
        # Calculate final score
        score = (
            (n_items * 2.0) +
            (avg_confidence * 1.0) +
            (items_with_pack_size * 0.5) +
            (items_with_prices * 0.75) +
            format_stability_bonus
        )
        
        LOGGER.debug(
            f"[SCORE] {method_name}: n_items={n_items}, avg_conf={avg_confidence:.3f}, "
            f"pack_size={items_with_pack_size}, prices={items_with_prices}, "
            f"stability_bonus={format_stability_bonus}, final_score={score:.2f}"
        )
        
        return score
    
    def extract_document_totals_from_text(self, text: str) -> Dict[str, Optional[float]]:
        """
        Extract document-level totals (subtotal, VAT, grand total) from OCR text.
        
        Parses lines containing keywords like "SUBTOTAL", "VAT TOTAL", "TOTAL DUE" and
        extracts the associated monetary values.
        
        Args:
            text: Full OCR text string (lines separated by \n)
            
        Returns:
            Dict with keys: invoice_subtotal, invoice_vat_total, invoice_grand_total
            Values are floats or None if not found
        """
        if not text or not text.strip():
            return {
                "invoice_subtotal": None,
                "invoice_vat_total": None,
                "invoice_grand_total": None
            }
        
        lines = text.split('\n')
        invoice_subtotal = None
        invoice_vat_total = None
        invoice_grand_total = None
        
        # Money pattern: digits with optional commas, decimal point, 2 decimal places
        # Handles: "1,473.36", "1473.36", "1.473,36" (European format)
        money_pattern = re.compile(r'[\d,]+[.,]\d{2}')
        
        def parse_money_value(money_str: str) -> Optional[float]:
            """Parse a money string to float, handling commas and currency symbols."""
            if not money_str:
                return None
            
            # Remove currency symbols
            cleaned = re.sub(r'[£$€Â£â‚¬]', '', money_str).strip()
            
            # Handle comma as thousands separator or decimal separator
            # If last comma is before decimal point, it's thousands separator
            # If comma is after digits and before decimal, it might be decimal separator (European)
            # Strategy: remove all commas, then parse
            cleaned = cleaned.replace(',', '')
            
            try:
                return float(cleaned)
            except (ValueError, TypeError):
                return None
        
        # Process lines from top to bottom (prefer last occurrence)
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            line_lower = line_stripped.lower()
            
            # Extract all money-like values from the line
            money_matches = money_pattern.findall(line_stripped)
            if not money_matches:
                continue
            
            # Parse money values
            money_values = []
            for match in money_matches:
                parsed = parse_money_value(match)
                if parsed is not None:
                    money_values.append(parsed)
            
            if not money_values:
                continue
            
            # SUBTOTAL pattern
            if "subtotal" in line_lower or "sub total" in line_lower:
                # Use last money value (typically the subtotal amount)
                invoice_subtotal = money_values[-1]
                LOGGER.debug(f"[TOTALS] Found subtotal: {invoice_subtotal} from line: {line_stripped[:80]}")
            
            # VAT TOTAL pattern
            elif "vat total" in line_lower or "vat summary" in line_lower:
                # Use last money value
                invoice_vat_total = money_values[-1]
                LOGGER.debug(f"[TOTALS] Found VAT total: {invoice_vat_total} from line: {line_stripped[:80]}")
            elif "vat @" in line_lower:
                # For "VAT @ 20% 245.56 1,227.80" format, first number is usually VAT amount
                invoice_vat_total = money_values[0]
                LOGGER.debug(f"[TOTALS] Found VAT @: {invoice_vat_total} from line: {line_stripped[:80]}")
            
            # GRAND TOTAL / TOTAL DUE pattern
            elif "total due" in line_lower or "amount due" in line_lower:
                # Use last money value
                invoice_grand_total = money_values[-1]
                LOGGER.debug(f"[TOTALS] Found total due: {invoice_grand_total} from line: {line_stripped[:80]}")
            elif line_lower.startswith("total ") or line_lower == "total":
                # Generic "TOTAL" - use last money value
                # But be careful not to match "SUBTOTAL" again
                if "subtotal" not in line_lower:
                    invoice_grand_total = money_values[-1]
                    LOGGER.debug(f"[TOTALS] Found total: {invoice_grand_total} from line: {line_stripped[:80]}")
        
        result = {
            "invoice_subtotal": invoice_subtotal,
            "invoice_vat_total": invoice_vat_total,
            "invoice_grand_total": invoice_grand_total
        }
        
        LOGGER.info(
            f"[TOTALS] Extracted totals: subtotal={invoice_subtotal}, "
            f"vat={invoice_vat_total}, grand_total={invoice_grand_total}"
        )
        
        return result
    
    def detect_items_region_from_blocks(self, word_blocks: List[Dict[str, Any]], page_height: Optional[int] = None) -> Tuple[Optional[int], Optional[int]]:
        """
        Detect the vertical region (y_min, y_max) where invoice line items are located.
        
        Enterprise-grade multi-signal detection:
        1. Right-edge clustering: Group blocks by max_x coordinate, find vertical clusters of price-aligned blocks
        2. First-price-line detection: Find earliest line containing qty + price OR unit_price + total_price
        3. Vertical density: Look for consecutive dense word blocks (likely table rows)
        4. Confidence fallback: If none found, use first qty-containing line to last price-containing line
        
        Args:
            word_blocks: List of word blocks with bbox info [x, y, w, h] or (x, y, w, h)
            page_height: Optional page height for calculating margins
            
        Returns:
            Tuple of (y_min, y_max) for items region, or (None, None) if detection fails
        """
        if not word_blocks:
            return (None, None)
        
        import re
        
        # Parse blocks into structured format
        parsed_blocks = []
        for block in word_blocks:
            bbox = block.get('bbox', [0, 0, 0, 0]) if isinstance(block, dict) else getattr(block, 'bbox', [0, 0, 0, 0])
            if len(bbox) >= 4:
                x, y, w, h = bbox[:4]
                text = block.get('text', '') if isinstance(block, dict) else getattr(block, 'text', '')
                max_x = x + w
                center_y = y + h // 2
                parsed_blocks.append({
                    'text': text,
                    'x': x,
                    'y': y,
                    'w': w,
                    'h': h,
                    'max_x': max_x,
                    'center_y': center_y
                })
        
        if not parsed_blocks:
            return (None, None)
        
        # Group blocks by similar center_y into lines
        lines_by_y = defaultdict(list)
        for block in parsed_blocks:
            rounded_y = (block['center_y'] // 10) * 10
            lines_by_y[rounded_y].append(block)
        
        # Sort lines by y position
        sorted_y_positions = sorted(lines_by_y.keys())
        
        # SIGNAL 1: Right-edge clustering for price-aligned blocks
        # Group blocks by max_x coordinate (prices are usually right-aligned)
        right_edge_groups = defaultdict(list)
        for block in parsed_blocks:
            # Round max_x to nearest 50 pixels (prices should align within ~50px)
            rounded_x = (block['max_x'] // 50) * 50
            right_edge_groups[rounded_x].append(block)
        
        # Find the rightmost cluster (likely price column)
        if right_edge_groups:
            rightmost_x = max(right_edge_groups.keys())
            price_aligned_blocks = right_edge_groups[rightmost_x]
            
            # Check if this cluster has vertical density (multiple lines)
            price_y_positions = sorted([b['center_y'] for b in price_aligned_blocks])
            if len(price_y_positions) >= 3:
                # Check for consecutive dense blocks
                consecutive_count = 1
                max_consecutive = 1
                for i in range(1, len(price_y_positions)):
                    if price_y_positions[i] - price_y_positions[i-1] < 50:  # Within 50px vertically
                        consecutive_count += 1
                        max_consecutive = max(max_consecutive, consecutive_count)
                    else:
                        consecutive_count = 1
                
                if max_consecutive >= 3:
                    # Found a vertical cluster of price-aligned blocks
                    price_region_y_min = min(b['y'] for b in price_aligned_blocks)
                    price_region_y_max = max(b['y'] + b['h'] for b in price_aligned_blocks)
                    LOGGER.info(f"[ITEMS_REGION] Signal 1: Right-edge clustering found price region: y={price_region_y_min}-{price_region_y_max}")
        
        # SIGNAL 2: First-price-line detection
        # Find earliest line containing qty + price OR unit_price + total_price
        first_price_line_y = None
        price_pattern = re.compile(r'\d+\.\d{2}|\d+,\d{3}\.\d{2}|\d+\.\d{1,2}')
        qty_pattern = re.compile(r'^\s*\d+\s+')
        
        for y_pos in sorted_y_positions:
            line_blocks = lines_by_y[y_pos]
            line_text = " ".join([b['text'] for b in line_blocks])
            
            # Check for qty + price pattern
            has_qty = bool(qty_pattern.match(line_text))
            has_price = bool(price_pattern.search(line_text))
            
            if has_qty and has_price:
                first_price_line_y = y_pos
                LOGGER.info(f"[ITEMS_REGION] Signal 2: First-price-line detected at y={first_price_line_y}")
                break
        
        # SIGNAL 3: Vertical density analysis
        # Look for consecutive dense word blocks (likely table rows)
        dense_region_start = None
        dense_region_end = None
        consecutive_dense_lines = 0
        min_dense_lines = 3  # Need at least 3 consecutive dense lines
        
        for i, y_pos in enumerate(sorted_y_positions):
            line_blocks = lines_by_y[y_pos]
            # A line is "dense" if it has multiple blocks (likely a table row)
            if len(line_blocks) >= 3:
                if consecutive_dense_lines == 0:
                    dense_region_start = y_pos
                consecutive_dense_lines += 1
                dense_region_end = y_pos
            else:
                if consecutive_dense_lines >= min_dense_lines:
                    # Found a dense region
                    LOGGER.info(f"[ITEMS_REGION] Signal 3: Vertical density found region: y={dense_region_start}-{dense_region_end}")
                    break
                consecutive_dense_lines = 0
                dense_region_start = None
                dense_region_end = None
        
        # SIGNAL 4: Confidence fallback
        # Use first qty-containing line to last price-containing line
        first_qty_y = None
        last_price_y = None
        
        for y_pos in sorted_y_positions:
            line_blocks = lines_by_y[y_pos]
            line_text = " ".join([b['text'] for b in line_blocks])
            
            if first_qty_y is None and qty_pattern.match(line_text):
                first_qty_y = y_pos
            
            if price_pattern.search(line_text):
                last_price_y = y_pos
        
        # Combine signals to determine region
        candidates = []
        
        # Use first-price-line as start if found
        if first_price_line_y is not None:
            candidates.append(('first_price_line', first_price_line_y, None))
        
        # Use dense region if found
        if dense_region_start is not None and dense_region_end is not None:
            candidates.append(('dense_region', dense_region_start, dense_region_end))
        
        # Use fallback if available
        if first_qty_y is not None and last_price_y is not None and last_price_y > first_qty_y:
            candidates.append(('fallback', first_qty_y, last_price_y))
        
        # Also check for header + summary (original method as backup)
        header_keywords = ["qty", "quantity", "description", "item", "product", "price", "total", "unit"]
        header_y = None
        
        for y_pos in sorted_y_positions[:20]:  # Check first 20 lines
            line_texts = [b['text'] for b in lines_by_y[y_pos]]
            combined_text = " ".join(line_texts).lower()
            keyword_count = sum(1 for keyword in header_keywords if keyword in combined_text)
            if keyword_count >= 2:
                header_y = y_pos
                break
        
        summary_keywords = ["subtotal", "sub total", "vat total", "total", "total due", "amount due"]
        summary_y = None
        
        for y_pos in sorted_y_positions:
            if header_y is not None and y_pos <= header_y:
                continue
            line_texts = [b['text'] for b in lines_by_y[y_pos]]
            combined_text = " ".join(line_texts).lower()
            for keyword in summary_keywords:
                if keyword in combined_text:
                    summary_y = y_pos
                    break
            if summary_y is not None:
                break
        
        if header_y is not None and summary_y is not None and summary_y > header_y:
            candidates.append(('header_summary', header_y, summary_y))
        
        # Select best candidate
        if candidates:
            # Prefer first-price-line or dense_region over fallback
            best_candidate = None
            for candidate_type, y_start, y_end in candidates:
                if candidate_type in ('first_price_line', 'dense_region'):
                    best_candidate = (y_start, y_end)
                    break
            
            if best_candidate is None:
                # Use fallback or header_summary
                best_candidate = (candidates[0][1], candidates[0][2])
            
            y_min, y_max = best_candidate
            
            # If y_max is None (from first_price_line), use last_price_y or page_height
            if y_max is None:
                y_max = last_price_y if last_price_y is not None else (page_height if page_height else sorted_y_positions[-1] + 100)
            
            # Add margins
            margin_below_start = 30
            margin_above_end = 20
            y_min = y_min + margin_below_start
            y_max = y_max - margin_above_end
            
            if y_max > y_min:
                LOGGER.info(f"[ITEMS_REGION] Detected items region (v2): y_min={y_min}, y_max={y_max}")
                return (y_min, y_max)
        
        # All heuristics failed
        LOGGER.warning(f"[ITEMS_REGION] Failed to detect items region with multi-signal approach")
        return (None, None)
    
    def _salvage_excessive_quantity_lines(
        self,
        page_lines: List[str],
        debug_block: Dict[str, Any],
    ) -> List[LineItem]:
        """
        Last-resort salvage: scan all lines for excessive quantities (> 100) and
        treat them as real items with qty=1.

        This is intentionally simple and defensive: it aims to give the user at
        least one plausible line item instead of an empty table.
        """
        salvage_rows: List[LineItem] = []

        # First try: look for lines that were previously skipped with excessive_quantity reason
        skipped = debug_block.get("skipped_lines") or []
        candidate_indices = [
            entry.get("line_index")
            for entry in skipped
            if isinstance(entry, dict)
            and isinstance(entry.get("reason"), str)
            and "excessive_quantity" in entry["reason"]
        ]

        # Second try: proactively scan all lines for excessive quantities OR any line with numbers
        # This ensures we salvage at least one line even if no skip reasons were found
        if not candidate_indices:
            for idx, line_text in enumerate(page_lines):
                if not line_text or len(line_text.strip()) < 3:
                    continue
                # Extract first number from line (likely the quantity)
                import re
                numbers = re.findall(r'\d+', line_text)
                if numbers:
                    try:
                        first_num = int(numbers[0])
                        # If quantity is excessive OR if we have no candidates yet and this line has numbers
                        if first_num > self._max_quantity_threshold:  # > 100
                            candidate_indices.append(idx)
                        elif not candidate_indices and first_num > 0:
                            # If we have no candidates yet, use the first line with a number
                            candidate_indices.append(idx)
                    except (ValueError, IndexError):
                        continue

        if not candidate_indices:
            return salvage_rows

        for idx in candidate_indices:
            if idx is None:
                continue
            if idx < 0 or idx >= len(page_lines):
                continue
            line_text = page_lines[idx]

            # Extract all numeric tokens from the line, keep decimals.
            numbers = re.findall(r"\d+\.\d+|\d+", line_text)
            # Basic defensive default values
            qty = 1
            unit_price = None
            line_total = None

            # Heuristic:
            # - if we have at least 2 numbers, treat the last as line_total,
            #   the previous as unit_price, and infer qty by division.
            # - if division is impossible, just keep qty=1 and treat the
            #   last number as either unit_price or line_total.
            if len(numbers) >= 2:
                try:
                    line_total = float(numbers[-1])
                except Exception:
                    line_total = None
                try:
                    unit_price = float(numbers[-2])
                except Exception:
                    unit_price = None

                if unit_price and line_total and unit_price > 0:
                    inferred_qty = round(line_total / unit_price)
                    if 1 <= inferred_qty <= 100:
                        qty = inferred_qty
            elif len(numbers) == 1:
                try:
                    unit_price = float(numbers[0])
                except Exception:
                    unit_price = None
            # If there are no numbers, we still salvage the description with qty=1.

            # Create LineItem object
            row = LineItem(
                description=line_text.strip(),
                quantity=str(qty),
                unit_price=f"{unit_price:.2f}" if unit_price is not None else "",
                total_price=f"{line_total:.2f}" if line_total is not None else "",
                vat="",
                confidence=0.5,  # Low confidence for salvaged items
                row_index=idx,
                cell_data={
                    "qty_source": "salvage_excessive_quantity",
                    "price_source": "salvage_excessive_quantity",
                    "salvaged": True,
                    "original_line": line_text
                }
            )
            salvage_rows.append(row)

        return salvage_rows
    
    def extract_best_line_items(
        self,
        ocr_result: Any,  # OCRResult from ocr_processor
        page_index: int,
        *,
        text_lines: Optional[List[str]] = None,
        base_confidence: float = 0.0,
        image: Optional[Any] = None,  # np.ndarray when available
    ) -> Tuple[List[LineItem], Dict[str, Any]]:
        """
        Enterprise helper: Run both table and line_fallback extraction, score them, pick the best.

        This method:
        1. Runs table extraction (if image and word_blocks available)
        2. Runs line_fallback extraction
        3. Scores both using _score_extraction()
        4. Returns the best extraction with debug info

        Args:
            ocr_result: OCRResult object with ocr_text, word_blocks, etc.
            page_index: Page index (0-based)
            text_lines: Optional pre-split text lines (if None, extracted from ocr_result.ocr_text)
            base_confidence: Base confidence value for scoring
            image: Optional image array for table extraction (if None, table extraction may be skipped)

        Returns:
            Tuple of (chosen_items, debug_info) where debug_info includes:
            - page_index
            - items_table_count
            - items_fallback_count
            - table_score
            - fallback_score
            - method_chosen ("table" or "fallback")
        """
        LOGGER.error(f"[DEBUG_TEST] extract_best_line_items called for page {page_index} - our changes should be active!")
        LOGGER.info(f"[BEST_EXTRACTION] Starting dual extraction for page {page_index}")
        
        items_table = []
        items_fallback = []
        skipped_lines_fallback = []  # Always initialize for debug output
        table_score = 0.0
        fallback_score = 0.0
        items_region_detected = False
        items_region = (None, None)
        
        # Step 0: Detect items region from word blocks (if available)
        if hasattr(ocr_result, 'word_blocks') and ocr_result.word_blocks:
            try:
                # Get page height from image if available
                page_height = None
                if image is not None:
                    page_height = image.shape[0] if len(image.shape) >= 2 else None
                
                # Convert word_blocks to list of dicts
                word_blocks_list = []
                for wb in ocr_result.word_blocks:
                    if isinstance(wb, dict):
                        word_blocks_list.append(wb)
                    else:
                        word_blocks_list.append({
                            'text': getattr(wb, 'text', ''),
                            'bbox': getattr(wb, 'bbox', [0, 0, 0, 0])
                        })
                
                items_region = self.detect_items_region_from_blocks(word_blocks_list, page_height)
                if items_region[0] is not None and items_region[1] is not None:
                    items_region_detected = True
                    LOGGER.info(f"[BEST_EXTRACTION] Items region detected: y_min={items_region[0]}, y_max={items_region[1]}")
                
                # MODULE 1: Detect price grid from word blocks
                price_grid = self._detect_price_grid_from_ocr_blocks(word_blocks_list)
            except Exception as e:
                LOGGER.warning(f"[BEST_EXTRACTION] Items region detection failed: {e}", exc_info=True)
                price_grid = None
        else:
            price_grid = None
        
        # Step 1: Run table extraction (if we have image and word_blocks)
        if image is not None and hasattr(ocr_result, 'word_blocks') and ocr_result.word_blocks:
            try:
                LOGGER.info(f"[BEST_EXTRACTION] Attempting table extraction with {len(ocr_result.word_blocks)} word blocks")
                
                # Get bbox from OCRResult
                bbox = ocr_result.bbox if hasattr(ocr_result, 'bbox') else (0, 0, image.shape[1], image.shape[0])
                
                # Get ocr_text
                ocr_text = ocr_result.ocr_text if hasattr(ocr_result, 'ocr_text') else ""
                
                # Convert word_blocks to the format expected by extract_table
                ocr_blocks = []
                for wb in ocr_result.word_blocks:
                    if isinstance(wb, dict):
                        ocr_blocks.append(wb)
                    else:
                        # Convert object to dict
                        ocr_blocks.append({
                            'text': getattr(wb, 'text', ''),
                            'bbox': getattr(wb, 'bbox', [0, 0, 0, 0])
                        })
                
                # Run table extraction
                table_result = self.extract_table(image, bbox, ocr_text, ocr_blocks)
                items_table = table_result.line_items
                table_score = self._score_extraction(items_table, base_confidence, "table")
                
                LOGGER.info(f"[BEST_EXTRACTION] Table extraction: {len(items_table)} items, score={table_score:.2f}")
            except Exception as e:
                LOGGER.warning(f"[BEST_EXTRACTION] Table extraction failed: {e}", exc_info=True)
                items_table = []
                table_score = 0.0
        else:
            LOGGER.info(f"[BEST_EXTRACTION] Skipping table extraction (image={image is not None}, word_blocks={hasattr(ocr_result, 'word_blocks') and ocr_result.word_blocks is not None})")
        
        # Step 2: Run line_fallback extraction
        # PHASE 4 - Initialize failure tracking (must be outside try block for scope)
        phase4_failures = []
        line_structure = None
        supplier_name = None
        
        try:
            # Build text_lines from OCRResult if not supplied
            if text_lines is None:
                ocr_text = ocr_result.ocr_text if hasattr(ocr_result, 'ocr_text') else ""
                text_lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
            
            # MODULE 5: Detect SUBTOTAL-driven region
            items_region_subtotal = None
            first_item_idx = None
            subtotal_idx = None
            
            # Find first line with qty+price pattern OR drink keyword + price
            for i, line in enumerate(text_lines):
                line_lower = line.lower().strip()
                
                # Check for qty+price pattern
                has_qty = bool(re.match(r'^\s*\d+', line))
                has_price = bool(re.search(r'[\d,]+\.\d{2}', line))
                has_drink_keyword = any(keyword in line_lower for keyword in self._product_keywords)
                
                if first_item_idx is None and ((has_qty and has_price) or (has_drink_keyword and has_price)):
                    first_item_idx = i
                    LOGGER.debug(f"[BEST_EXTRACTION] Found first item line at index {i}: '{line[:50]}'")
                
                # Find SUBTOTAL line
                if subtotal_idx is None:
                    if any(kw in line_lower for kw in ['subtotal', 'sub-total', 'sub total']):
                        subtotal_idx = i
                        LOGGER.debug(f"[BEST_EXTRACTION] Found SUBTOTAL line at index {i}: '{line[:50]}'")
                        break
            
            # PHASE 5 - Module F: Create region only if both found AND items exist before SUBTOTAL
            # Require first_item_idx to be valid (not None) - ensures items found before SUBTOTAL
            if first_item_idx is not None and subtotal_idx is not None and subtotal_idx > first_item_idx:
                items_region_subtotal = (first_item_idx, subtotal_idx)
                LOGGER.info(f"[BEST_EXTRACTION] SUBTOTAL region detected: lines {first_item_idx} to {subtotal_idx-1} (items found before SUBTOTAL)")
            elif subtotal_idx is not None and first_item_idx is None:
                # SUBTOTAL found but no items before it - don't create region
                LOGGER.debug(f"[BEST_EXTRACTION] SUBTOTAL found at line {subtotal_idx} but no items detected before it - not creating region")
            
            # Always start with all lines - region filtering is optional optimization
            filtered_text_lines = text_lines
            use_subtotal_fallback = False
            
            # Optionally filter by items region if detected (but still track skipped lines)
            if items_region_detected and hasattr(ocr_result, 'word_blocks') and ocr_result.word_blocks:
                try:
                    # Map text lines to y positions using word blocks
                    y_min, y_max = items_region
                    
                    # Group word blocks by line (similar y positions)
                    lines_by_y = defaultdict(list)
                    for wb in ocr_result.word_blocks:
                        bbox = wb.get('bbox', [0, 0, 0, 0]) if isinstance(wb, dict) else getattr(wb, 'bbox', [0, 0, 0, 0])
                        if len(bbox) >= 4:
                            y = bbox[1]
                            rounded_y = (y // 10) * 10
                            text = wb.get('text', '') if isinstance(wb, dict) else getattr(wb, 'text', '')
                            lines_by_y[rounded_y].append(text)
                    
                    # Filter text_lines based on whether their corresponding word blocks are in region
                    filtered_text_lines = []
                    for line in text_lines:
                        line_lower = line.lower()
                        # Check if any word block for this line is in the items region
                        in_region = False
                        for y_pos, texts in lines_by_y.items():
                            if y_min <= y_pos <= y_max:
                                # Check if this line matches any text in this y position
                                for text in texts:
                                    if text.lower() in line_lower or line_lower in text.lower():
                                        in_region = True
                                        break
                                if in_region:
                                    break
                        
                        if in_region or not items_region_detected:
                            filtered_text_lines.append(line)
                    
                    if len(filtered_text_lines) < len(text_lines):
                        LOGGER.info(f"[BEST_EXTRACTION] Filtered {len(text_lines)} lines to {len(filtered_text_lines)} lines in items region")
                except Exception as e:
                    LOGGER.warning(f"[BEST_EXTRACTION] Failed to filter lines by region: {e}", exc_info=True)
                    # Fall back to unfiltered lines
                    filtered_text_lines = text_lines
            
            # Fallback: If region detection failed, try SUBTOTAL heuristic (but don't restrict too much)
            if not items_region_detected and text_lines:
                try:
                    # Find first line that looks like an item (has qty + price pattern)
                    first_item_idx = None
                    for idx, line in enumerate(text_lines):
                        line_lower = line.lower().strip()
                        # Check for qty pattern (more lenient)
                        qty_match = re.match(r'^[\W\s]*?(\d+)[\s\.]', line) or re.match(r'^[^\d]*?(\d+)', line)
                        # Check for price pattern
                        price_pattern = re.compile(r'\d+\.\d{2}|\d+,\d{3}\.\d{2}|\d+\.\d{1,2}')
                        has_price = bool(price_pattern.search(line))
                        
                        if qty_match and has_price:
                            first_item_idx = idx
                            break
                    
                    # Find SUBTOTAL line
                    subtotal_idx = None
                    subtotal_keywords = ['subtotal', 'sub-total', 'sub total']
                    for idx, line in enumerate(text_lines):
                        line_lower = line.lower().strip()
                        for keyword in subtotal_keywords:
                            if keyword in line_lower:
                                subtotal_idx = idx
                                break
                        if subtotal_idx is not None:
                            break
                    
                    # PHASE 5 - Module F: Only create region if items found before SUBTOTAL
                    # (SUBTOTAL fallback is informational, not restrictive)
                    if first_item_idx is not None and subtotal_idx is not None and subtotal_idx > first_item_idx:
                        use_subtotal_fallback = True
                        LOGGER.info(f"[BEST_EXTRACTION] SUBTOTAL fallback identified region: lines {first_item_idx} to {subtotal_idx-1} (items found before SUBTOTAL), but processing all lines")
                    elif subtotal_idx is not None and first_item_idx is None:
                        LOGGER.debug(f"[BEST_EXTRACTION] SUBTOTAL fallback: SUBTOTAL found at {subtotal_idx} but no items before it - not creating region")
                except Exception as e:
                    LOGGER.warning(f"[BEST_EXTRACTION] SUBTOTAL fallback failed: {e}", exc_info=True)
            
            # PHASE 4 - Module A + PHASE 5 - Module C: Detect line structure with bounding box support
            try:
                # Get word_blocks from ocr_result if available
                word_blocks_for_structure = None
                if hasattr(ocr_result, 'word_blocks') and ocr_result.word_blocks:
                    word_blocks_for_structure = ocr_result.word_blocks
                
                line_structure = self._detect_line_structure(
                    filtered_text_lines if filtered_text_lines else text_lines,
                    word_blocks=word_blocks_for_structure
                )
                LOGGER.info(f"[BEST_EXTRACTION] Line structure detected: qty_pos={line_structure.get('qty_pos')}, "
                           f"price_pos={line_structure.get('price_pos')}, confidence={line_structure.get('confidence', 0):.3f}")
            except Exception as e:
                LOGGER.warning(f"[BEST_EXTRACTION] Line structure detection failed: {e}", exc_info=True)
                phase4_failures.append("line_structure")
                # Fallback to empty structure
                line_structure = {
                    "qty_pos": None,
                    "price_pos": None,
                    "desc_window": [0, -1],
                    "pack_pos": None,
                    "confidence": 0.0
                }
            
            # PHASE 4 - Module D: Extract and normalize supplier name if available
            if hasattr(ocr_result, 'supplier_name'):
                supplier_name = ocr_result.supplier_name
            elif hasattr(ocr_result, 'ocr_text') and ocr_result.ocr_text:
                # Try to extract supplier name from OCR text (simple heuristic)
                lines = ocr_result.ocr_text.split('\n')[:10]  # Check first 10 lines
                for line in lines:
                    line_lower = line.lower().strip()
                    if any(kw in line_lower for kw in ['supplier', 'vendor', 'company', 'ltd', 'limited', 'inc']):
                        # Extract potential supplier name (first substantial line)
                        supplier_name = line.strip()[:50]  # Limit length
                        break
            
            # PHASE 4 - Module D: Normalize supplier name to prevent pattern leakage
            if supplier_name:
                # Normalize: strip, lowercase, limit length, remove special chars
                supplier_name = supplier_name.strip()
                if len(supplier_name) > 0:
                    # Keep original case for display but use normalized for cache key
                    supplier_name_normalized = supplier_name.lower().strip()[:100]  # Limit to 100 chars
                    # Remove excessive whitespace
                    supplier_name_normalized = re.sub(r'\s+', ' ', supplier_name_normalized)
                    # Use normalized version for pattern cache
                    supplier_name = supplier_name_normalized
                else:
                    supplier_name = None
            
            # Always process all lines (region filtering is just for optimization, not restriction)
            if filtered_text_lines:
                LOGGER.info(f"[BEST_EXTRACTION] Running line_fallback extraction with {len(filtered_text_lines)} lines (from {len(text_lines)} total lines)")
                try:
                    items_fallback, skipped_lines_fallback = self.fallback_extract_from_lines(
                        filtered_text_lines, 
                        base_confidence=base_confidence,
                        items_region_subtotal=items_region_subtotal,  # MODULE 5: Pass SUBTOTAL region
                        price_grid=price_grid,  # MODULE 1: Pass price grid for advisory boost
                        line_structure=line_structure,  # PHASE 4 - Module A: Pass line structure
                        supplier_name=supplier_name,  # PHASE 4 - Module D: Pass supplier name
                        items_region_detected=items_region_detected  # Pass region detection status
                    )
                except Exception as inner_e:
                    LOGGER.error(f"[BEST_EXTRACTION] fallback_extract_from_lines raised exception: {inner_e}", exc_info=True)
                    raise  # Re-raise to be caught by outer try-except
                
                # PHASE 4 - Module D: Learn patterns from successful extraction (with error handling)
                if supplier_name and items_fallback:
                    try:
                        self._learn_supplier_patterns(supplier_name, items_fallback, skipped_lines_fallback)
                    except Exception as e:
                        LOGGER.warning(f"[BEST_EXTRACTION] Supplier pattern learning failed: {e}", exc_info=True)
                        phase4_failures.append("supplier_patterns")
                        # Continue without pattern learning
                fallback_score = self._score_extraction(items_fallback, base_confidence, "fallback")
                
                LOGGER.info(f"[BEST_EXTRACTION] Line fallback: {len(items_fallback)} items, score={fallback_score:.2f}")
            else:
                LOGGER.warning(f"[BEST_EXTRACTION] filtered_text_lines is empty! text_lines has {len(text_lines) if text_lines else 0} lines")
                items_fallback = []
                skipped_lines_fallback = []
                fallback_score = 0.0
        except Exception as e:
            LOGGER.warning(f"[BEST_EXTRACTION] Line fallback extraction failed: {e}", exc_info=True)
            items_fallback = []
            skipped_lines_fallback = []
            fallback_score = 0.0
            # Ensure phase4_failures is initialized even on exception
            if 'phase4_failures' not in locals():
                phase4_failures = []
            phase4_failures.append("fallback_extraction")
        
        # Step 3: Pick the best extraction
        if table_score > fallback_score:
            chosen_items = items_table
            method_chosen = "table"
            LOGGER.info(f"[BEST_EXTRACTION] Chose TABLE method (score: {table_score:.2f} > {fallback_score:.2f})")
        elif fallback_score > 0.0:
            chosen_items = items_fallback
            method_chosen = "fallback"
            # Check if it was wide-net fallback
            if items_fallback and len(items_fallback) > 0:
                first_item = items_fallback[0]
                if first_item.cell_data and first_item.cell_data.get("method") == "line_fallback_wide_net":
                    method_chosen = "fallback_wide_net"
            LOGGER.info(f"[BEST_EXTRACTION] Chose {method_chosen.upper()} method (score: {fallback_score:.2f} > {table_score:.2f})")
        else:
            # Both failed or no items - prefer fallback if it has any items (even wide-net)
            if items_fallback:
                chosen_items = items_fallback
                method_chosen = "fallback"
                # Check if it was wide-net fallback
                if items_fallback and len(items_fallback) > 0:
                    first_item = items_fallback[0]
                    if first_item.cell_data and first_item.cell_data.get("method") == "line_fallback_wide_net":
                        method_chosen = "fallback_wide_net"
            else:
                chosen_items = items_table if items_table else []
                method_chosen = "table" if items_table else "none"
            LOGGER.warning(f"[BEST_EXTRACTION] Both methods had issues, using {method_chosen} ({len(chosen_items)} items)")
        
        # MODULE 7: Apply reconciliation to chosen items
        reconciliation_info = None
        if chosen_items:
            strictness = self._get_parsing_strictness(base_confidence)
            reconciled_items, reconciliation_info = self._reconcile_line_items(
                chosen_items, 
                invoice_total=None,  # Will be set by caller if available (from main.py)
                strictness=strictness
            )
            chosen_items = reconciled_items
        
        # Last-resort salvage: if no items extracted, try to salvage lines that were skipped for excessive quantity
        if not chosen_items:
            # Build a temporary debug block for salvage function
            temp_debug_block = {
                "skipped_lines": skipped_lines_fallback
            }
            salvage_items = self._salvage_excessive_quantity_lines(
                page_lines=filtered_text_lines if filtered_text_lines else text_lines,
                debug_block=temp_debug_block,
            )
            if salvage_items:
                LOGGER.warning(
                    "[QUANTITY_FIX_ACTIVE] Using salvage_excessive_quantity "
                    f"for page_index={page_index} (0 items from normal passes) - salvaged {len(salvage_items)} row(s)"
                )
                chosen_items = salvage_items
                # Update method_chosen to reflect that we used salvage
                method_chosen = "salvage_excessive_quantity"
        
        # PHASE 4 - Collect pass details and price inference notes
        pass_details = None
        candidate_region_info = None
        if items_fallback and len(items_fallback) > 0:
            # Extract pass details and candidate region from first item's cell_data if available
            first_item = items_fallback[0]
            if first_item.cell_data:
                if "_phase6_pass_details" in first_item.cell_data:
                    pass_details = first_item.cell_data.pop("_phase6_pass_details")  # Remove after extracting
                if "_candidate_region" in first_item.cell_data:
                    candidate_region_info = first_item.cell_data.pop("_candidate_region")  # Remove after extracting
            # If not found in cell_data, create default structure (fallback extraction may not have run multi-pass)
            if pass_details is None and method_chosen in ["fallback", "fallback_wide_net"]:
                pass_details = {
                    "strict": {"rows": 0, "skipped": 0},
                    "standard": {"rows": len(items_fallback), "skipped": len(skipped_lines_fallback)},
                    "lenient": {"rows": 0, "skipped": 0},
                    "merged_pass_rows": len(items_fallback)
                }
        
        # PHASE 4 - Collect price inference notes from all items
        price_inference_notes = []
        supplier_pattern_hits = []
        if chosen_items:
            for item in chosen_items:
                if item.cell_data:
                    # Collect price_inference values
                    price_inf = item.cell_data.get("price_inference")
                    if price_inf and price_inf not in price_inference_notes:
                        price_inference_notes.append(price_inf)
                    
                    # Collect supplier pattern hits
                    if "supplier_pattern_applied" in item.cell_data:
                        supplier_pattern_hits.append(item.cell_data["supplier_pattern_applied"])
        
        # PHASE 4 - Get supplier pattern adjustments if available
        if supplier_name:
            try:
                pattern_adjustments = self._get_supplier_pattern_adjustments(supplier_name)
                if pattern_adjustments:
                    supplier_pattern_hits.append(pattern_adjustments)
            except Exception as e:
                LOGGER.debug(f"[BEST_EXTRACTION] Failed to get supplier pattern adjustments: {e}")
        
        # phase4_failures is initialized at start of Step 2, so it's always available here
        
        # Build debug info
        # BACKWARD COMPATIBILITY: All existing fields preserved, Phase 4 fields are additive only
        debug_info = {
            # Existing fields (Phase 3 and earlier) - MUST be preserved
            "page_index": page_index,
            "items_table_count": len(items_table),
            "items_fallback_count": len(items_fallback),
            "table_score": table_score,
            "fallback_score": fallback_score,
            "method_chosen": method_chosen,
            "items_region_detected": items_region_detected,
            "items_region": {"y_min": items_region[0], "y_max": items_region[1]} if items_region_detected else None,
            "skipped_lines": [s for s in skipped_lines_fallback if "excessive_quantity" not in str(s.get("reason", "")).lower()],  # Filter out excessive_quantity skip reasons
            "reconciliation_info": reconciliation_info,  # MODULE 7: Add reconciliation info
            "price_grid_detected": price_grid is not None,  # MODULE 1: Price grid detection
            "price_grid": price_grid,  # MODULE 1: Price grid details
            "subtotal_region_detected": items_region_subtotal is not None,  # MODULE 5: SUBTOTAL region
            "subtotal_region": {"start_idx": items_region_subtotal[0], "end_idx": items_region_subtotal[1]} if items_region_subtotal else None,  # MODULE 5
            "candidate_region": candidate_region_info,  # B: Manual candidate region when items_region_detected=False
            "base_confidence": base_confidence,  # MODULE 6: Confidence-adaptive parsing
            "parsing_strictness": self._get_parsing_strictness(base_confidence),  # MODULE 6: Strictness config
            # PHASE 4 - New fields (additive, don't break existing consumers)
            "line_structure": line_structure,  # PHASE 4 - Module A: Line structure detection
            "supplier_name": supplier_name,  # PHASE 4 - Module D: Supplier name
            "supplier_patterns_available": supplier_name in self._supplier_patterns if supplier_name else False,  # PHASE 4 - Module D
            # PHASE 4 - Comprehensive debug section
            "phase4": {
                "structure_model": line_structure if line_structure else None,
                "passes": pass_details if pass_details else {
                    "strict": {"rows": 0, "skipped": 0},
                    "standard": {"rows": len(items_fallback), "skipped": len(skipped_lines_fallback)},
                    "lenient": {"rows": 0, "skipped": 0}
                },
                "merged_pass_rows": len(chosen_items) if method_chosen == "fallback" else 0,
                "supplier_template_used": supplier_name in self._supplier_patterns if supplier_name else False,
                "supplier_pattern_hits": supplier_pattern_hits if supplier_pattern_hits else [],
                "price_inference_notes": price_inference_notes if price_inference_notes else [],
                "phase4_failures": phase4_failures
            }
        }
        
        LOGGER.info(f"[BEST_EXTRACTION] Final result: {len(chosen_items)} items using {method_chosen} method")
        
        return (chosen_items, debug_info)
    
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
                           ocr_text: str = "", ocr_blocks: Optional[List[Dict[str, Any]]] = None) -> TableResult:
    """
    Main entry point for table extraction from a single block.
    
    Args:
        image: Full document image
        block_info: Block information with type and bbox
        ocr_text: OCR text from the block (optional, for text-based fallback)
        ocr_blocks: List of OCR word blocks with bbox and text (optional, for spatial clustering)
    
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
    return extractor.extract_table(image, bbox, ocr_text, ocr_blocks)

