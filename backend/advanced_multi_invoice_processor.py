"""
Advanced multi-invoice processing with:
- Intelligent document segmentation
- Context-aware invoice detection
- Advanced merging algorithms
- Quality-based filtering
"""

import os
import sys
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import asyncio

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class InvoiceSegment:
    """Represents a segment of an invoice"""
    text: str
    start_line: int
    end_line: int
    confidence: float
    invoice_indicators: List[str]
    supplier_candidates: List[str]
    total_candidates: List[float]
    date_candidates: List[str]

@dataclass
class InvoiceResult:
    """Result of invoice processing"""
    supplier_name: str
    invoice_number: str
    invoice_date: str
    total_amount: float
    confidence: float
    quality_score: float
    segment_text: str
    processing_time: float
    extraction_method: str
    validation_passed: bool

class DocumentSegmenter:
    """Intelligent document segmentation"""
    
    def __init__(self):
        self.invoice_indicators = [
            'invoice', 'inv#', 'invoice no', 'invoice number',
            'bill', 'bill to', 'amount due', 'total due',
            'date', 'issued', 'created', 'supplier'
        ]
        self.supplier_indicators = [
            'limited', 'ltd', 'company', 'brewing', 'dispense', 
            'hospitality', 'services', 'solutions'
        ]
        self.separator_patterns = [
            r'={10,}',  # Lines of equals
            r'-{10,}',  # Lines of dashes
            r'\*{10,}',  # Lines of asterisks
            r'INVOICE\s+\d+',  # Invoice X
            r'PAGE\s+\d+',  # Page X
        ]
    
    async def segment_document(self, file_path: str) -> List[InvoiceSegment]:
        """Segment document into potential invoice sections"""
        try:
            # Read document content
            content = await self._read_document_content(file_path)
            if not content:
                return []
            
            # Split into lines
            lines = content.split('\n')
            
            # Find segment boundaries
            boundaries = self._find_segment_boundaries(lines)
            
            # Create segments
            segments = []
            for i, (start, end) in enumerate(boundaries):
                segment_text = '\n'.join(lines[start:end])
                segment = self._create_segment(segment_text, start, end, lines)
                if segment:
                    segments.append(segment)
            
            logger.info(f"📄 Document segmented into {len(segments)} potential invoices")
            return segments
            
        except Exception as e:
            logger.error(f"Document segmentation failed: {e}")
            return []
    
    async def _read_document_content(self, file_path: str) -> str:
        """Read document content based on file type"""
        try:
            file_path = Path(file_path)
            
            if file_path.suffix.lower() == '.pdf':
                return await self._read_pdf_content(file_path)
            elif file_path.suffix.lower() in ['.txt', '.md']:
                return await self._read_text_content(file_path)
            else:
                # For other file types, assume text content
                return await self._read_text_content(file_path)
                
        except Exception as e:
            logger.error(f"Document reading failed: {e}")
            return ""
    
    async def _read_pdf_content(self, file_path: Path) -> str:
        """Read PDF content"""
        try:
            import fitz
            
            doc = fitz.open(file_path)
            content = ""
            
            for page in doc:
                content += page.get_text()
            
            doc.close()
            return content
            
        except Exception as e:
            logger.error(f"PDF reading failed: {e}")
            return ""
    
    async def _read_text_content(self, file_path: Path) -> str:
        """Read text content"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Text reading failed: {e}")
            return ""
    
    def _find_segment_boundaries(self, lines: List[str]) -> List[Tuple[int, int]]:
        """Find boundaries between different invoices"""
        try:
            boundaries = []
            current_start = 0
            
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                
                # Check if this line indicates a new invoice
                is_new_invoice = self._is_invoice_boundary(line_stripped, i)
                
                if is_new_invoice and i > current_start:
                    # End current segment
                    boundaries.append((current_start, i))
                    current_start = i
            
            # Add final segment
            if current_start < len(lines):
                boundaries.append((current_start, len(lines)))
            
            return boundaries
            
        except Exception as e:
            logger.error(f"Boundary detection failed: {e}")
            return [(0, len(lines))]
    
    def _is_invoice_boundary(self, line: str, line_number: int) -> bool:
        """Check if line indicates a new invoice"""
        try:
            # Check for separator patterns
            for pattern in self.separator_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    return True
            
            # Check for invoice indicators
            line_lower = line.lower()
            if any(indicator in line_lower for indicator in self.invoice_indicators):
                return True
            
            # Check for supplier indicators (but not in table headers)
            if any(indicator in line_lower for indicator in self.supplier_indicators):
                if not any(table_word in line_lower for table_word in ['qty', 'code', 'item', 'price', 'total']):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Invoice boundary detection failed: {e}")
            return False
    
    def _create_segment(self, text: str, start_line: int, end_line: int, all_lines: List[str]) -> Optional[InvoiceSegment]:
        """Create an invoice segment from text"""
        try:
            if not text.strip():
                return None
            
            # Find invoice indicators in this segment
            invoice_indicators = self._find_invoice_indicators(text)
            
            # Find supplier candidates
            supplier_candidates = self._find_supplier_candidates(text)
            
            # Find total candidates
            total_candidates = self._find_total_candidates(text)
            
            # Find date candidates
            date_candidates = self._find_date_candidates(text)
            
            # Calculate confidence based on indicators
            confidence = self._calculate_segment_confidence(
                invoice_indicators, supplier_candidates, total_candidates, date_candidates
            )
            
            return InvoiceSegment(
                text=text,
                start_line=start_line,
                end_line=end_line,
                confidence=confidence,
                invoice_indicators=invoice_indicators,
                supplier_candidates=supplier_candidates,
                total_candidates=total_candidates,
                date_candidates=date_candidates
            )
            
        except Exception as e:
            logger.error(f"Segment creation failed: {e}")
            return None
    
    def _find_invoice_indicators(self, text: str) -> List[str]:
        """Find invoice indicators in text"""
        try:
            indicators = []
            text_lower = text.lower()
            
            for indicator in self.invoice_indicators:
                if indicator in text_lower:
                    indicators.append(indicator)
            
            return indicators
            
        except Exception as e:
            logger.error(f"Invoice indicator detection failed: {e}")
            return []
    
    def _find_supplier_candidates(self, text: str) -> List[str]:
        """Find supplier candidates in text"""
        try:
            candidates = []
            lines = text.split('\n')
            
            for line in lines:
                line_stripped = line.strip()
                if len(line_stripped) > 5:
                    # Look for company patterns
                    if any(pattern in line_stripped.upper() for pattern in ['LIMITED', 'LTD', 'CO', 'COMPANY']):
                        candidates.append(line_stripped)
                    # Look for supplier indicators
                    elif any(indicator in line_stripped.lower() for indicator in self.supplier_indicators):
                        candidates.append(line_stripped)
            
            return candidates
            
        except Exception as e:
            logger.error(f"Supplier candidate detection failed: {e}")
            return []
    
    def _find_total_candidates(self, text: str) -> List[float]:
        """Find total amount candidates in text"""
        try:
            candidates = []
            
            # Look for currency amounts
            amount_pattern = r'[£$€]\s*(\d+\.?\d*)'
            matches = re.findall(amount_pattern, text)
            
            for match in matches:
                try:
                    amount = float(match)
                    if amount > 10:  # Filter out small amounts
                        candidates.append(amount)
                except ValueError:
                    continue
            
            return candidates
            
        except Exception as e:
            logger.error(f"Total candidate detection failed: {e}")
            return []
    
    def _find_date_candidates(self, text: str) -> List[str]:
        """Find date candidates in text"""
        try:
            candidates = []
            
            # Look for date patterns
            date_patterns = [
                r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
                r'\d{4}-\d{2}-\d{2}',
            ]
            
            for pattern in date_patterns:
                matches = re.findall(pattern, text)
                candidates.extend(matches)
            
            return candidates
            
        except Exception as e:
            logger.error(f"Date candidate detection failed: {e}")
            return []
    
    def _calculate_segment_confidence(self, invoice_indicators: List[str], supplier_candidates: List[str], 
                                    total_candidates: List[float], date_candidates: List[str]) -> float:
        """Calculate confidence for a segment"""
        try:
            confidence = 0.0
            
            # Invoice indicators boost confidence
            if invoice_indicators:
                confidence += 0.3
            
            # Supplier candidates boost confidence
            if supplier_candidates:
                confidence += 0.2
            
            # Total candidates boost confidence
            if total_candidates:
                confidence += 0.2
            
            # Date candidates boost confidence
            if date_candidates:
                confidence += 0.1
            
            # Multiple indicators boost confidence further
            if len(invoice_indicators) + len(supplier_candidates) + len(total_candidates) + len(date_candidates) > 3:
                confidence += 0.2
            
            return min(confidence, 1.0)
            
        except Exception as e:
            logger.error(f"Confidence calculation failed: {e}")
            return 0.0

class InvoiceDetector:
    """Detects and validates invoice segments"""
    
    def __init__(self):
        self.min_confidence = 0.3
        self.min_text_length = 100
    
    def is_invoice(self, segment: InvoiceSegment) -> bool:
        """Check if segment is a valid invoice"""
        try:
            # Check minimum requirements
            if len(segment.text.strip()) < self.min_text_length:
                return False
            
            if segment.confidence < self.min_confidence:
                return False
            
            # Must have at least some invoice indicators
            if not segment.invoice_indicators and not segment.supplier_candidates:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Invoice detection failed: {e}")
            return False

class InvoiceMerger:
    """Merges incomplete invoice segments"""
    
    def merge_invoices(self, segments: List[InvoiceSegment]) -> InvoiceSegment:
        """Merge multiple segments into a single invoice"""
        try:
            if not segments:
                return None
            
            # Combine all text
            combined_text = "\n".join([seg.text for seg in segments])
            
            # Combine all indicators
            all_indicators = []
            all_suppliers = []
            all_totals = []
            all_dates = []
            
            for segment in segments:
                all_indicators.extend(segment.invoice_indicators)
                all_suppliers.extend(segment.supplier_candidates)
                all_totals.extend(segment.total_candidates)
                all_dates.extend(segment.date_candidates)
            
            # Calculate combined confidence
            avg_confidence = sum(seg.confidence for seg in segments) / len(segments)
            
            return InvoiceSegment(
                text=combined_text,
                start_line=segments[0].start_line,
                end_line=segments[-1].end_line,
                confidence=avg_confidence,
                invoice_indicators=list(set(all_indicators)),
                supplier_candidates=list(set(all_suppliers)),
                total_candidates=list(set(all_totals)),
                date_candidates=list(set(all_dates))
            )
            
        except Exception as e:
            logger.error(f"Invoice merging failed: {e}")
            return None

class QualityFilter:
    """Filters results based on quality criteria"""
    
    def __init__(self):
        self.min_confidence = 0.4
        self.min_text_length = 200
        self.min_indicators = 2
    
    def filter_results(self, results: List[InvoiceResult]) -> List[InvoiceResult]:
        """Filter results based on quality criteria"""
        try:
            filtered_results = []
            
            for result in results:
                if self._meets_quality_criteria(result):
                    filtered_results.append(result)
            
            logger.info(f"📊 Quality filtering: {len(results)} -> {len(filtered_results)} results")
            return filtered_results
            
        except Exception as e:
            logger.error(f"Quality filtering failed: {e}")
            return results
    
    def _meets_quality_criteria(self, result: InvoiceResult) -> bool:
        """Check if result meets quality criteria"""
        try:
            # Check confidence
            if result.confidence < self.min_confidence:
                return False
            
            # Check text length
            if len(result.segment_text.strip()) < self.min_text_length:
                return False
            
            # Check for required fields
            required_fields = [result.supplier_name, result.total_amount]
            valid_fields = sum(1 for field in required_fields if field and field != "Unknown" and field != 0)
            
            if valid_fields < self.min_indicators:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Quality criteria check failed: {e}")
            return False

class AdvancedMultiInvoiceProcessor:
    """
    State-of-the-art multi-invoice processing with:
    - Intelligent document segmentation
    - Context-aware invoice detection
    - Advanced merging algorithms
    - Quality-based filtering
    """
    
    def __init__(self):
        self.segmenter = DocumentSegmenter()
        self.invoice_detector = InvoiceDetector()
        self.merger = InvoiceMerger()
        self.quality_filter = QualityFilter()
    
    async def process_multi_invoice_document(self, file_path: str) -> List[InvoiceResult]:
        """Process multi-invoice document with state-of-the-art techniques"""
        start_time = datetime.now()
        
        try:
            logger.info(f"🔍 Starting multi-invoice processing for: {file_path}")
            
            # 1. Intelligent document segmentation
            segments = await self.segmenter.segment_document(file_path)
            if not segments:
                logger.warning("⚠️ No segments found")
                return [self._fallback_single_invoice(file_path)]
            
            logger.info(f"📄 Document segmented into {len(segments)} segments")
            
            # 2. Invoice detection and classification
            invoice_segments = []
            for segment in segments:
                if self.invoice_detector.is_invoice(segment):
                    invoice_segments.append(segment)
            
            logger.info(f"📄 Found {len(invoice_segments)} invoice segments")
            
            # 3. Advanced processing of each invoice
            results = []
            for i, segment in enumerate(invoice_segments):
                result = await self._process_single_invoice(segment, i+1)
                if result:
                    results.append(result)
            
            # 4. Quality-based filtering
            filtered_results = self.quality_filter.filter_results(results)
            
            # 5. Intelligent merging if needed
            if len(filtered_results) == 0 and len(results) > 0:
                logger.info("📄 No results passed quality filter, attempting merge")
                merged_segment = self.merger.merge_invoices([seg for seg in invoice_segments])
                if merged_segment:
                    merged_result = await self._process_single_invoice(merged_segment, 1)
                    if merged_result:
                        filtered_results = [merged_result]
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ Multi-invoice processing completed in {processing_time:.2f}s: {len(filtered_results)} results")
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Multi-invoice processing failed: {e}")
            return [self._fallback_single_invoice(file_path)]
    
    async def _process_single_invoice(self, segment: InvoiceSegment, segment_number: int) -> Optional[InvoiceResult]:
        """Process a single invoice segment"""
        start_time = datetime.now()
        
        try:
            # Extract fields using intelligent field extractor
            from intelligent_field_extractor import intelligent_field_extractor
            
            extracted_fields = intelligent_field_extractor.extract_all_fields(segment.text)
            
            # Create invoice result
            result = InvoiceResult(
                supplier_name=extracted_fields.fields.get('supplier_name', 'Unknown'),
                invoice_number=extracted_fields.fields.get('invoice_number', 'Unknown'),
                invoice_date=extracted_fields.fields.get('invoice_date', 'Unknown'),
                total_amount=float(extracted_fields.fields.get('total_amount', 0)),
                confidence=extracted_fields.overall_confidence,
                quality_score=segment.confidence,
                segment_text=segment.text,
                processing_time=(datetime.now() - start_time).total_seconds(),
                extraction_method=f"segment_{segment_number}",
                validation_passed=all(extracted_fields.business_rule_compliance.values())
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Single invoice processing failed: {e}")
            return None
    
    def _fallback_single_invoice(self, file_path: str) -> InvoiceResult:
        """Create fallback single invoice result"""
        return InvoiceResult(
            supplier_name="Unknown Supplier",
            invoice_number="Unknown",
            invoice_date="Unknown",
            total_amount=0.0,
            confidence=0.3,
            quality_score=0.3,
            segment_text="",
            processing_time=0.0,
            extraction_method="fallback",
            validation_passed=False
        )

# Global instance
advanced_multi_invoice_processor = AdvancedMultiInvoiceProcessor() 