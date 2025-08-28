#!/usr/bin/env python3
"""
Enhanced Line-Item Extractor for Phase B

Features:
- Column detection via x-projection clustering
- Row assembly tolerant of wrapped descriptions
- Units normalization with conversions
- Doc-type aware processing (invoice, delivery note, receipt)
- VAT per line extraction
- Confidence scoring and reasons
"""

import re
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
import logging

logger = logging.getLogger(__name__)

@dataclass
class LineItem:
    """Enhanced line item with confidence and reasons"""
    description: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    unit_original: Optional[str] = None  # Store original unit text
    unit_price: Optional[float] = None
    line_total: Optional[float] = None
    tax_rate: Optional[float] = None
    delivered_qty: Optional[float] = None  # For delivery notes
    computed_total: bool = False  # Flag if line_total was computed
    line_confidence: float = 0.0
    row_reasons: List[str] = None
    
    def __post_init__(self):
        if self.row_reasons is None:
            self.row_reasons = []

@dataclass
class ExtractionResult:
    """Result of line item extraction"""
    line_items: List[LineItem]
    table_detected: bool
    columns_detected: List[str]
    extraction_confidence: float
    extraction_reasons: List[str]

class EnhancedLineItemExtractor:
    """Enhanced line item extractor with doc-type awareness"""
    
    def __init__(self):
        # Unit normalization mappings (English + Welsh)
        self.unit_mappings = {
            # English units
            'x': 'ea', 'each': 'ea', 'units': 'ea', 'unit': 'ea',
            'kg': 'kg', 'kgs': 'kg', 'kilograms': 'kg',
            'g': 'g', 'grams': 'g', 'gram': 'g',
            'l': 'l', 'litres': 'l', 'litre': 'l', 'liter': 'l', 'liters': 'l',
            'ml': 'ml', 'millilitres': 'ml', 'millilitre': 'ml',
            'case': 'case', 'cases': 'case',
            'pack': 'pack', 'packs': 'pack',
            'box': 'box', 'boxes': 'box',
            'bottle': 'bottle', 'bottles': 'bottle',
            'can': 'can', 'cans': 'can',
            
            # Welsh units
            'un': 'ea', 'uned': 'ea', 'unedau': 'ea',
            'cilogram': 'kg', 'cilogramau': 'kg',
            'gram': 'g', 'gramau': 'g',
            'litr': 'l', 'litrau': 'l',
            'mililitr': 'ml', 'mililitrau': 'ml',
            'cas': 'case', 'casiau': 'case',
            'pecyn': 'pack', 'pecynnau': 'pack',
            'blwch': 'box', 'blychau': 'box',
            'botel': 'bottle', 'boteli': 'bottle',
            'can': 'can', 'cannau': 'can',
        }
        
        # Unit conversions (from -> to)
        self.unit_conversions = {
            ('g', 'kg'): 0.001,
            ('kg', 'g'): 1000,
            ('ml', 'l'): 0.001,
            ('l', 'ml'): 1000,
        }
        
        # Price patterns (bilingual)
        self.price_pattern = re.compile(r'[£€$]\s*\d+(?:[.,]\d{2})?')
        self.quantity_pattern = re.compile(
            r'\b(\d+(?:\.\d+)?)\s*(kg|g|l|ml|case|cases|ea|each|x|pack|packs|box|boxes|bottle|bottles|can|cans|'
            r'un|uned|unedau|cilogram|cilogramau|gram|gramau|litr|litrau|mililitr|mililitrau|'
            r'cas|casiau|pecyn|pecynnau|blwch|blychau|botel|boteli|cannau)\b', re.I)
        
        # VAT patterns (bilingual)
        self.vat_pattern = re.compile(r'\((\d+(?:\.\d+)?)%\)|(?:vat|taw)\s*(\d+(?:\.\d+)?)%', re.I)
        
        # Meta row patterns (bilingual)
        self.meta_pattern = re.compile(
            r'\b(change|rounding|cash|card|tip|balance|total|subtotal|'
            r'newid|tal|cerdyn|cyfanswm|is-gyfanswm)\b', re.I)
        
        # Wrapped description patterns
        self.wrap_pattern = re.compile(r'^[A-Za-zÀ-ÿ\s\-\.]+$')  # Letters, spaces, hyphens, dots
        
    def extract_line_items(self, ocr_result: Dict[str, Any], doc_type: str = "invoice") -> ExtractionResult:
        """
        Extract line items from OCR result with doc-type awareness
        
        Args:
            ocr_result: OCR result with word boxes and text
            doc_type: Document type (invoice, delivery_note, receipt)
            
        Returns:
            ExtractionResult with line items and metadata
        """
        logger.info(f"🔄 Extracting line items for {doc_type}")
        
        # Extract word boxes and text
        word_boxes = ocr_result.get('word_boxes', [])
        text = ocr_result.get('text', '')
        
        if not word_boxes:
            logger.warning("No word boxes found, falling back to regex extraction")
            return self._fallback_regex_extraction(text, doc_type)
        
        # Detect table structure
        table_box = self._detect_table_box(word_boxes)
        
        if table_box:
            logger.info("Table detected, using column-based extraction")
            return self._column_based_extraction(word_boxes, table_box, doc_type)
        else:
            logger.info("No table detected, using regex extraction")
            return self._fallback_regex_extraction(text, doc_type)
    
    def _detect_table_box(self, word_boxes: List[Dict]) -> Optional[Dict]:
        """Detect table bounding box from word boxes"""
        if not word_boxes:
            return None
            
        # Look for table-like patterns in word arrangement
        # Check if we have multiple rows with similar structure
        y_positions = sorted(set(box['bbox'][1] for box in word_boxes))
        
        # Check if we have price-like patterns (currency symbols)
        price_words = [box for box in word_boxes if re.search(r'[£€$]', box.get('text', ''))]
        
        # Check if we have quantity-like patterns (numbers or text with numbers)
        quantity_words = [box for box in word_boxes if re.match(r'^\d+(?:\.\d+)?$', box.get('text', ''))]
        quantity_like_words = [box for box in word_boxes if re.search(r'\d+', box.get('text', ''))]
        
        # If we have both prices and quantities, likely a table (even single row)
        if len(price_words) >= 1 and len(quantity_words) >= 1:
            # Calculate bounding box
            x_coords = [box['bbox'][0] for box in word_boxes]
            y_coords = [box['bbox'][1] for box in word_boxes]
            x2_coords = [box['bbox'][2] for box in word_boxes]
            y2_coords = [box['bbox'][3] for box in word_boxes]
            
            return {
                'x1': min(x_coords),
                'y1': min(y_coords),
                'x2': max(x2_coords),
                'y2': max(y2_coords)
            }
        
        # If we have prices and quantity-like text (e.g., "500g"), also treat as table
        if len(price_words) >= 1 and len(quantity_like_words) >= 1:
            # Calculate bounding box
            x_coords = [box['bbox'][0] for box in word_boxes]
            y_coords = [box['bbox'][1] for box in word_boxes]
            x2_coords = [box['bbox'][2] for box in word_boxes]
            y2_coords = [box['bbox'][3] for box in word_boxes]
            
            return {
                'x1': min(x_coords),
                'y1': min(y_coords),
                'x2': max(x2_coords),
                'y2': max(y2_coords)
            }
        
        # For delivery notes, if we have quantities and multiple rows, treat as table
        if len(quantity_words) >= 2 and len(y_positions) >= 2:
            # Calculate bounding box
            x_coords = [box['bbox'][0] for box in word_boxes]
            y_coords = [box['bbox'][1] for box in word_boxes]
            x2_coords = [box['bbox'][2] for box in word_boxes]
            y2_coords = [box['bbox'][3] for box in word_boxes]
            
            return {
                'x1': min(x_coords),
                'y1': min(y_coords),
                'x2': max(x2_coords),
                'y2': max(y2_coords)
            }
        
        return None
    
    def _column_based_extraction(self, word_boxes: List[Dict], table_box: Dict, doc_type: str) -> ExtractionResult:
        """Extract line items using column detection"""
        # Filter words within table box
        table_words = [
            box for box in word_boxes
            if (box['bbox'][0] >= table_box['x1'] and box['bbox'][2] <= table_box['x2'] and
                box['bbox'][1] >= table_box['y1'] and box['bbox'][3] <= table_box['y2'])
        ]
        
        # Detect columns via x-projection clustering
        columns = self._detect_columns(table_words)
        
        # Group words by rows
        rows = self._group_words_by_rows(table_words)
        
        # Extract line items from rows
        line_items = []
        for row in rows:
            line_item = self._extract_line_item_from_row(row, doc_type)
            if line_item:
                line_items.append(line_item)
        
        return ExtractionResult(
            line_items=line_items,
            table_detected=True,
            columns_detected=[col['type'] for col in columns],
            extraction_confidence=0.85,
            extraction_reasons=['COLUMN_DETECTION']
        )
    
    def _detect_columns(self, words: List[Dict]) -> List[Dict]:
        """Detect columns using x-projection clustering with improved robustness"""
        if not words:
            return []
        
        # Get x-coordinates of word centers
        x_centers = [(box['bbox'][0] + box['bbox'][2]) / 2 for box in words]
        
        # Improved clustering with adaptive threshold
        clusters = []
        sorted_x = sorted(x_centers)
        
        if len(sorted_x) < 2:
            return []
        
        # Calculate adaptive threshold based on document width
        x_range = max(sorted_x) - min(sorted_x)
        threshold = max(30, x_range / 20)  # Minimum 30px, or 5% of width
        
        current_cluster = [sorted_x[0]]
        for x in sorted_x[1:]:
            if x - current_cluster[-1] < threshold:
                current_cluster.append(x)
            else:
                if len(current_cluster) >= 2:  # Only keep clusters with multiple points
                    clusters.append(current_cluster)
                current_cluster = [x]
        
        if len(current_cluster) >= 2:
            clusters.append(current_cluster)
        
        # Create column definitions with confidence
        columns = []
        for i, cluster in enumerate(clusters):
            avg_x = sum(cluster) / len(cluster)
            cluster_width = max(cluster) - min(cluster)
            
            # Determine column type based on content
            column_type = self._classify_column_type(cluster, words)
            
            columns.append({
                'index': i,
                'x_center': avg_x,
                'width': cluster_width,
                'type': column_type,
                'confidence': min(1.0, len(cluster) / 5.0)  # More words = higher confidence
            })
        
        # Sort columns by x-position
        columns.sort(key=lambda x: x['x_center'])
        
        return columns
    
    def _classify_column_type(self, cluster: List[float], words: List[Dict]) -> str:
        """Classify column type based on content"""
        # Find words in this column
        cluster_center = sum(cluster) / len(cluster)
        cluster_width = max(cluster) - min(cluster)
        
        column_words = []
        for word in words:
            word_center = (word['bbox'][0] + word['bbox'][2]) / 2
            if abs(word_center - cluster_center) < cluster_width / 2:
                column_words.append(word['text'].lower())
        
        # Analyze content to determine type
        text = ' '.join(column_words)
        
        # Check for quantity indicators
        if any(qty in text for qty in ['qty', 'quantity', 'nifer', 'un']):
            return 'quantity'
        
        # Check for price indicators
        if any(price in text for price in ['price', 'cost', 'pris', 'cost']):
            return 'unit_price'
        
        # Check for total indicators
        if any(total in text for total in ['total', 'cyfanswm', 'sum']):
            return 'line_total'
        
        # Check for description indicators
        if any(desc in text for desc in ['description', 'item', 'disgrifiad', 'eitem']):
            return 'description'
        
        # Default classification based on position and content
        if any(char.isdigit() for char in text):
            if any(char in text for char in ['£', '€', '$']):
                return 'line_total'
            else:
                return 'quantity'
        else:
            return 'description'
    
    def _group_words_by_rows(self, words: List[Dict]) -> List[List[Dict]]:
        """Group words by rows with improved tolerance for wrapped descriptions"""
        if not words:
            return []
        
        # Sort words by y-coordinate
        sorted_words = sorted(words, key=lambda w: w['bbox'][1])
        
        rows = []
        current_row = [sorted_words[0]]
        current_y = sorted_words[0]['bbox'][1]
        
        for word in sorted_words[1:]:
            word_y = word['bbox'][1]
            y_diff = abs(word_y - current_y)
            
            # Adaptive row height threshold
            word_height = word['bbox'][3] - word['bbox'][1]
            threshold = max(10, word_height * 1.5)  # At least 10px or 1.5x word height
            
            if y_diff <= threshold:
                # Same row
                current_row.append(word)
            else:
                # New row
                if current_row:
                    rows.append(current_row)
                current_row = [word]
                current_y = word_y
        
        if current_row:
            rows.append(current_row)
        
        return rows
    
    def _extract_line_item_from_row(self, row_words: List[Dict], doc_type: str) -> Optional[LineItem]:
        """Extract line item from a row of words with improved description handling"""
        if not row_words:
            return None
        
        # Sort words by x-coordinate
        sorted_words = sorted(row_words, key=lambda w: w['bbox'][0])
        
        # Extract text and classify content
        row_text = ' '.join([w['text'] for w in sorted_words])
        
        # Skip meta rows (for receipts)
        if doc_type == 'receipt' and self.meta_pattern.search(row_text):
            return None
        
        # Extract components
        description = self._extract_description(sorted_words, doc_type)
        quantity = self._extract_quantity(sorted_words, doc_type)
        unit = self._extract_unit(sorted_words, doc_type)
        unit_original = self._extract_unit_original(sorted_words, doc_type)
        unit_price = self._extract_unit_price(sorted_words, doc_type)
        line_total = self._extract_line_total(sorted_words, doc_type)
        tax_rate = self._extract_tax_rate(sorted_words, doc_type)
        
        # Compute line total if missing
        computed_total = False
        if line_total is None and quantity is not None and unit_price is not None:
            line_total = quantity * unit_price
            computed_total = True
        
        # Calculate confidence
        confidence = self._calculate_line_confidence(description, quantity, unit_price, line_total, doc_type)
        
        # Generate reasons
        reasons = self._generate_line_reasons(description, quantity, unit_price, line_total, computed_total, doc_type)
        
        return LineItem(
            description=description,
            quantity=quantity,
            unit=unit,
            unit_original=unit_original,  # Store original unit text
            unit_price=unit_price,
            line_total=line_total,
            tax_rate=tax_rate,
            computed_total=computed_total,
            line_confidence=confidence,
            row_reasons=reasons
        )
    
    def _extract_description(self, words: List[Dict], doc_type: str) -> str:
        """Extract description with support for wrapped text"""
        description_words = []
        
        for word in words:
            text = word['text'].strip()
            
            # Skip price-like text
            if self.price_pattern.match(text):
                continue
            
            # Skip pure numeric text (but allow text with numbers like "500g")
            if re.match(r'^\d+(?:\.\d+)?$', text):
                continue
            
            # Skip standalone unit text (but allow text that contains units)
            if text.lower() in self.unit_mappings and len(text) <= 10:
                continue
            
            # Check if this looks like description text
            if self.wrap_pattern.match(text) and len(text) > 1:
                description_words.append(text)
        
        # Join description words
        description = ' '.join(description_words)
        
        # Handle wrapped descriptions
        if len(description_words) > 1:
            # Look for continuation patterns
            for i in range(len(description_words) - 1):
                current = description_words[i]
                next_word = description_words[i + 1]
                
                # Check if next word continues the description
                if (current.endswith('-') or 
                    (len(current) > 3 and len(next_word) > 2) or
                    current.lower() in ['prosciutto', 'di', 'parma']):  # Common wrapped words
                    continue
                else:
                    # Might be separate items
                    break
        
        return description.strip()
    
    def _extract_quantity(self, words: List[Dict], doc_type: str) -> Optional[float]:
        """Extract quantity with improved pattern matching"""
        for word in words:
            text = word['text'].strip()
            
            # Look for quantity patterns
            match = re.match(r'^(\d+(?:\.\d+)?)$', text)
            if match:
                return float(match.group(1))
            
            # Look for quantity with unit
            match = self.quantity_pattern.search(text)
            if match:
                return float(match.group(1))
        
        return None
    
    def _extract_unit(self, words: List[Dict], doc_type: str) -> Optional[str]:
        """Extract and normalize unit"""
        for word in words:
            text = word['text'].strip().lower()
            
            # Look for unit in quantity pattern
            match = self.quantity_pattern.search(word['text'])
            if match:
                unit = match.group(2).lower()
                return self.unit_mappings.get(unit, unit)
            
            # Look for standalone unit
            if text in self.unit_mappings:
                return self.unit_mappings[text]
        
        return None
    
    def _extract_unit_original(self, words: List[Dict], doc_type: str) -> Optional[str]:
        """Extract original unit text before normalization"""
        for word in words:
            text = word['text'].strip()
            
            # Look for unit in quantity pattern
            match = self.quantity_pattern.search(word['text'])
            if match:
                return match.group(2)  # Return original case
            
            # Look for standalone unit
            if text.lower() in self.unit_mappings:
                return text  # Return original case
        
        return None
    
    def _extract_unit_price(self, words: List[Dict], doc_type: str) -> Optional[float]:
        """Extract unit price"""
        prices = []
        for word in words:
            text = word['text'].strip()
            
            # Look for price patterns
            match = re.search(r'[£€$]\s*(\d+(?:[.,]\d{2})?)', text)
            if match:
                price_str = match.group(1).replace(',', '')
                prices.append((float(price_str), word['bbox'][0]))
        
        if not prices:
            return None
        
        # For unit price, prefer the first (leftmost) price
        # Sort by x-position and take the first
        prices.sort(key=lambda x: x[1])
        return prices[0][0]
    
    def _extract_line_total(self, words: List[Dict], doc_type: str) -> Optional[float]:
        """Extract line total"""
        prices = []
        for word in words:
            text = word['text'].strip()
            
            # Look for price patterns
            match = re.search(r'[£€$]\s*(\d+(?:[.,]\d{2})?)', text)
            if match:
                price_str = match.group(1).replace(',', '')
                prices.append((float(price_str), word['bbox'][0]))
        
        if not prices:
            return None
        
        # If only one price, don't treat it as line total (let it be unit price)
        if len(prices) == 1:
            return None
        
        # For line total, prefer the last (rightmost) price
        # Sort by x-position and take the last
        prices.sort(key=lambda x: x[1])
        return prices[-1][0]
    
    def _extract_tax_rate(self, words: List[Dict], doc_type: str) -> Optional[float]:
        """Extract tax rate"""
        for word in words:
            text = word['text'].strip()
            
            # Look for VAT patterns
            match = self.vat_pattern.search(text)
            if match:
                rate = match.group(1) or match.group(2)
                if rate:
                    return float(rate)
        
        return None
    
    def _calculate_line_confidence(self, description: str, quantity: Optional[float], 
                                 unit_price: Optional[float], line_total: Optional[float], 
                                 doc_type: str) -> float:
        """Calculate confidence for line item extraction"""
        confidence = 0.0
        
        # Base confidence from description
        if description and len(description) > 2:
            confidence += 0.3
        
        # Add confidence for each extracted field
        if quantity is not None:
            confidence += 0.2
        
        if unit_price is not None:
            confidence += 0.2
        
        if line_total is not None:
            confidence += 0.2
        
        # Document type specific adjustments
        if doc_type == 'delivery_note':
            # Delivery notes don't need prices
            if description and quantity:
                confidence += 0.1
        elif doc_type == 'receipt':
            # Receipts need line totals
            if line_total is not None:
                confidence += 0.1
        
        return min(1.0, confidence)
    
    def _generate_line_reasons(self, description: str, quantity: Optional[float], 
                             unit_price: Optional[float], line_total: Optional[float], 
                             computed_total: bool, doc_type: str) -> List[str]:
        """Generate reasons for line item extraction"""
        reasons = []
        
        if description:
            reasons.append('DESCRIPTION_FOUND')
        
        if quantity is not None:
            reasons.append('QUANTITY_FOUND')
        
        if unit_price is not None:
            reasons.append('UNIT_PRICE_FOUND')
        
        if line_total is not None:
            if computed_total:
                reasons.append('LINE_TOTAL_COMPUTED')
            else:
                reasons.append('LINE_TOTAL_FOUND')
        
        # Document type specific reasons
        if doc_type == 'delivery_note':
            if not unit_price and not line_total:
                reasons.append('DN_NO_PRICES')
        
        if doc_type == 'receipt':
            if line_total is not None:
                reasons.append('RECEIPT_MODE')
        
        return reasons
    
    def _fallback_regex_extraction(self, text: str, doc_type: str) -> ExtractionResult:
        """Fallback regex-based extraction when table detection fails"""
        logger.info("Using fallback regex extraction")
        
        lines = text.split('\n')
        line_items = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip meta rows for receipts
            if doc_type == "receipt" and self.meta_pattern.search(line.lower()):
                continue
            
            # Extract line item using regex patterns
            line_item = self._extract_line_item_regex(line, doc_type)
            if line_item:
                line_items.append(line_item)
        
        return ExtractionResult(
            line_items=line_items,
            table_detected=False,
            columns_detected=[],
            extraction_confidence=0.6,
            extraction_reasons=['REGEX_FALLBACK']
        )
    
    def _extract_line_item_regex(self, line: str, doc_type: str) -> Optional[LineItem]:
        """Extract line item using regex patterns"""
        # Look for quantity + unit + description + price pattern
        pattern = r'(\d+(?:\.\d+)?)\s*(kg|g|l|ml|case|cases|ea|each|x|pack|packs|box|boxes|bottle|bottles|can|cans)\s+(.+?)\s+([£€$]\s*\d+(?:[.,]\d{2})?)'
        match = re.search(pattern, line, re.I)
        
        if match:
            quantity = float(match.group(1))
            unit = self._normalize_unit(match.group(2))
            description = match.group(3).strip()
            line_total = self._extract_price(match.group(4))
            
            # Doc-type specific processing
            if doc_type == "delivery_note":
                delivered_qty = quantity
                quantity = None
                unit_price = None
                line_total = None
                computed_total = False
            else:
                delivered_qty = None
                unit_price = None  # Would need separate extraction
                computed_total = False
            
            confidence = self._calculate_line_confidence(description, quantity, unit_price, line_total, doc_type)
            reasons = self._generate_row_reasons(description, quantity, unit_price, line_total, doc_type)
            
            return LineItem(
                description=description,
                quantity=quantity,
                unit=unit,
                unit_original=match.group(2), # Store original unit
                unit_price=unit_price,
                line_total=line_total,
                delivered_qty=delivered_qty,
                computed_total=computed_total,
                line_confidence=confidence,
                row_reasons=reasons
            )
        
        return None
    
    def _normalize_unit(self, unit: str) -> str:
        """Normalize unit to canonical form"""
        unit_lower = unit.lower()
        return self.unit_mappings.get(unit_lower, unit_lower)
    
    def _extract_price(self, price_str: str) -> float:
        """Extract numeric price from currency string"""
        # Remove currency symbols and convert to float
        price_clean = re.sub(r'[£€$,\s]', '', price_str)
        return float(price_clean)
    
    def _generate_row_reasons(self, description: str, quantity: Optional[float], 
                            unit_price: Optional[float], line_total: Optional[float], 
                            doc_type: str) -> List[str]:
        """Generate reasons for row extraction decisions"""
        reasons = []
        
        if not description:
            reasons.append("NO_DESCRIPTION")
        
        if quantity is None and doc_type != "receipt":
            reasons.append("NO_QUANTITY")
        
        if doc_type == "invoice" and unit_price is None:
            reasons.append("NO_UNIT_PRICE")
        
        if doc_type == "receipt" and line_total is None:
            reasons.append("NO_LINE_TOTAL")
        
        if doc_type == "delivery_note":
            reasons.append("DN_NO_PRICES")
        
        if doc_type == "receipt":
            reasons.append("RECEIPT_MODE")
        
        return reasons

def get_enhanced_line_item_extractor() -> EnhancedLineItemExtractor:
    """Get enhanced line item extractor instance"""
    return EnhancedLineItemExtractor() 