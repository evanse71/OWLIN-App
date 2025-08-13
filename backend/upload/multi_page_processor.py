"""
Multi-Page Document Processor with 100% Reliability

This module provides robust processing for multi-page documents with aggregation,
page-by-page confidence tracking, and comprehensive error handling.

Key Features:
- Multi-page PDF and image processing
- Page-by-page confidence tracking
- Result aggregation across pages
- Deduplication and merging of line items
- Comprehensive error handling
- Progress tracking and reporting

Author: OWLIN Development Team
Version: 2.0.0
"""

import logging
import time
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import os

from PIL import Image
import pypdfium2 as pdfium

# Local imports
from backend.ocr.enhanced_ocr_engine import enhanced_ocr_engine
from backend.ocr.enhanced_line_item_extractor import enhanced_line_item_extractor, LineItem
from backend.ocr.ocr_engine import OCRResult

logger = logging.getLogger(__name__)

@dataclass
class PageResult:
    """Result from processing a single page"""
    page_number: int
    ocr_results: List[OCRResult]
    line_items: List[LineItem]
    confidence: float
    processing_time: float
    error: Optional[str] = None

@dataclass
class DocumentResult:
    """Aggregated result from processing a multi-page document"""
    document_type: str
    supplier: str
    invoice_number: str
    date: str
    line_items: List[LineItem]
    page_results: List[PageResult]
    overall_confidence: float
    total_processing_time: float
    pages_processed: int
    pages_failed: int

class MultiPageProcessor:
    """
    Multi-page document processor with robust error handling and result aggregation
    """
    
    def __init__(self):
        self.ocr_engine = enhanced_ocr_engine
        self.line_extractor = enhanced_line_item_extractor
    
    def process_multi_page_document(self, file_path: str) -> DocumentResult:
        """
        Process multi-page documents with aggregation
        
        Args:
            file_path: Path to the document file
            
        Returns:
            DocumentResult with aggregated results
        """
        logger.info(f"🔄 Starting multi-page document processing: {file_path}")
        start_time = time.time()
        
        try:
            # Convert document to images
            pages = self._convert_to_images(file_path)
            logger.info(f"📄 Document has {len(pages)} pages")
            
            # Process each page
            page_results = []
            all_ocr_results = []
            
            for page_num, page_image in enumerate(pages):
                logger.info(f"🔄 Processing page {page_num + 1}/{len(pages)}")
                page_start_time = time.time()
                
                try:
                    # Process page
                    page_result = self._process_single_page(page_image, page_num + 1)
                    page_results.append(page_result)
                    all_ocr_results.extend(page_result.ocr_results)
                    
                    logger.info(f"✅ Page {page_num + 1} processed successfully")
                    
                except Exception as e:
                    logger.error(f"❌ Page {page_num + 1} processing failed: {e}")
                    # Create error result for failed page
                    error_result = PageResult(
                        page_number=page_num + 1,
                        ocr_results=[],
                        line_items=[],
                        confidence=0.0,
                        processing_time=time.time() - page_start_time,
                        error=str(e)
                    )
                    page_results.append(error_result)
                finally:
                    # Clean up page image to free memory
                    try:
                        page_image.close()
                    except:
                        pass
            
            # Aggregate results across pages
            document_result = self._aggregate_results(page_results, all_ocr_results, time.time() - start_time)
            
            logger.info(f"✅ Multi-page processing completed: {document_result.pages_processed} pages processed")
            return document_result
            
        except Exception as e:
            logger.error(f"❌ Multi-page processing failed: {e}")
            # Return minimal result
            return self._create_minimal_result(file_path, str(e), time.time() - start_time)
    
    def _convert_to_images(self, file_path: str) -> List[Image.Image]:
        """
        Convert document to list of images
        
        Args:
            file_path: Path to the document file
            
        Returns:
            List of PIL Image objects
        """
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.pdf':
            return self._convert_pdf_to_images(file_path)
        else:
            # Single image file
            try:
                image = Image.open(file_path)
                return [image]
            except Exception as e:
                logger.error(f"❌ Failed to open image file: {e}")
                raise
    
    def _convert_pdf_to_images(self, file_path: str) -> List[Image.Image]:
        """
        Convert PDF to list of images
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            List of PIL Image objects
        """
        try:
            # Use pypdfium2 for PDF processing
            pdf = pdfium.PdfDocument(file_path)
            images = []
            
            for page_num in range(len(pdf)):
                page = pdf[page_num]
                # Render page to image
                image = page.render(scale=2.0)  # Higher resolution for better OCR
                pil_image = image.to_pil()
                images.append(pil_image)
            
            pdf.close()
            logger.info(f"📄 Converted PDF to {len(images)} images")
            return images
            
        except Exception as e:
            logger.error(f"❌ PDF conversion failed: {e}")
            raise Exception(f"PDF conversion failed: {str(e)}")
    
    def _process_single_page(self, page_image: Image.Image, page_number: int) -> PageResult:
        """
        Process a single page
        
        Args:
            page_image: PIL Image of the page
            page_number: Page number for tracking
            
        Returns:
            PageResult with processing results
        """
        page_start_time = time.time()
        
        try:
            # Run OCR on page
            ocr_results = self.ocr_engine.run_ocr_with_retry(page_image, page_number)
            
            # Extract line items
            line_items = self.line_extractor.extract_line_items(ocr_results)
            
            # Calculate page confidence
            confidence = self._calculate_page_confidence(ocr_results)
            
            processing_time = time.time() - page_start_time
            
            return PageResult(
                page_number=page_number,
                ocr_results=ocr_results,
                line_items=line_items,
                confidence=confidence,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"❌ Page {page_number} processing failed: {e}")
            return PageResult(
                page_number=page_number,
                ocr_results=[],
                line_items=[],
                confidence=0.0,
                processing_time=time.time() - page_start_time,
                error=str(e)
            )
    
    def _calculate_page_confidence(self, ocr_results: List[OCRResult]) -> float:
        """
        Calculate confidence score for a page
        
        Args:
            ocr_results: List of OCRResult objects
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        if not ocr_results:
            return 0.0
        
        # Calculate average confidence
        valid_results = [r for r in ocr_results if r.confidence > 0]
        if not valid_results:
            return 0.0
        
        avg_confidence = sum(r.confidence for r in valid_results) / len(valid_results)
        
        # Boost confidence based on text content
        total_text = " ".join([r.text for r in ocr_results if r.text])
        text_boost = min(len(total_text) / 100.0, 0.2)  # Up to 0.2 boost for good text content
        
        return min(avg_confidence + text_boost, 1.0)
    
    def _aggregate_results(self, page_results: List[PageResult], all_ocr_results: List[OCRResult], total_time: float) -> DocumentResult:
        """
        Aggregate results from multiple pages
        
        Args:
            page_results: List of PageResult objects
            all_ocr_results: All OCR results combined
            total_time: Total processing time
            
        Returns:
            DocumentResult with aggregated data
        """
        # Count successful and failed pages
        successful_pages = [p for p in page_results if p.error is None]
        failed_pages = [p for p in page_results if p.error is not None]
        
        # Combine line items from all pages
        all_line_items = []
        for page_result in page_results:
            all_line_items.extend(page_result.line_items)
        
        # Deduplicate and merge line items
        merged_line_items = self._merge_line_items(all_line_items)
        
        # Extract document-level information
        document_info = self._extract_document_info(all_ocr_results)
        
        # Calculate overall confidence
        overall_confidence = self._calculate_overall_confidence(page_results)
        
        return DocumentResult(
            document_type=document_info.get('type', 'unknown'),
            supplier=document_info.get('supplier', 'Unknown Supplier'),
            invoice_number=document_info.get('invoice_number', 'Unknown'),
            date=document_info.get('date', 'Unknown'),
            line_items=merged_line_items,
            page_results=page_results,
            overall_confidence=overall_confidence,
            total_processing_time=total_time,
            pages_processed=len(successful_pages),
            pages_failed=len(failed_pages)
        )
    
    def _merge_line_items(self, line_items: List[LineItem]) -> List[LineItem]:
        """
        Merge and deduplicate line items
        
        Args:
            line_items: List of LineItem objects
            
        Returns:
            Merged and deduplicated LineItem objects
        """
        if not line_items:
            return []
        
        # Group by description (case-insensitive)
        grouped_items = {}
        
        for item in line_items:
            # Normalize description for grouping
            normalized_desc = item.description.lower().strip()
            
            if normalized_desc in grouped_items:
                # Merge with existing item
                existing = grouped_items[normalized_desc]
                existing.quantity += item.quantity
                existing.total_price += item.total_price
                existing.confidence = max(existing.confidence, item.confidence)
                
                # Update unit price if needed
                if existing.quantity > 0:
                    existing.unit_price = existing.total_price / existing.quantity
                    existing.unit_price_excl_vat = existing.unit_price
                    existing.line_total_excl_vat = existing.total_price
            else:
                # Add new item
                grouped_items[normalized_desc] = item
        
        # Convert back to list
        merged_items = list(grouped_items.values())
        
        # Sort by total price (descending)
        merged_items.sort(key=lambda x: x.total_price, reverse=True)
        
        logger.info(f"📊 Merged {len(line_items)} line items into {len(merged_items)} unique items")
        return merged_items
    
    def _extract_document_info(self, ocr_results: List[OCRResult]) -> Dict[str, str]:
        """
        Extract document-level information from OCR results
        
        Args:
            ocr_results: List of OCRResult objects
            
        Returns:
            Dictionary with document information
        """
        # Convert OCR results to text
        text_lines = self._convert_to_text_lines(ocr_results)
        full_text = '\n'.join(text_lines)
        
        # Extract basic information
        document_info = {
            'type': 'invoice',  # Default
            'supplier': 'Unknown Supplier',
            'invoice_number': 'Unknown',
            'date': 'Unknown'
        }
        
        # Look for invoice number patterns
        invoice_patterns = [
            r'invoice\s*#?\s*(\w+)',
            r'inv\s*#?\s*(\w+)',
            r'invoice\s*number\s*:?\s*(\w+)',
            r'(\d{6,})',  # 6+ digit number
        ]
        
        for pattern in invoice_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                document_info['invoice_number'] = match.group(1)
                break
        
        # Look for date patterns
        date_patterns = [
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
            r'(\w+\s+\d{1,2},?\s+\d{4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, full_text)
            if match:
                document_info['date'] = match.group(1)
                break
        
        # Look for supplier name (usually in top portion)
        supplier_patterns = [
            r'^([A-Z][A-Z\s&]+(?:LTD|LIMITED|INC|LLC|CORP|COMPANY))',
            r'^([A-Z][A-Z\s&]+)',
        ]
        
        for line in text_lines[:10]:  # Check first 10 lines
            for pattern in supplier_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    supplier = match.group(1).strip()
                    if len(supplier) > 3:
                        document_info['supplier'] = supplier
                        break
            if document_info['supplier'] != 'Unknown Supplier':
                break
        
        return document_info
    
    def _convert_to_text_lines(self, ocr_results: List[OCRResult]) -> List[str]:
        """Convert OCR results to text lines"""
        if not ocr_results:
            return []
        
        # Sort by Y-coordinate to maintain line order
        sorted_results = sorted(ocr_results, key=lambda r: r.bounding_box[0][1])
        
        lines = []
        current_line = []
        current_y = None
        
        for result in sorted_results:
            y_pos = result.bounding_box[0][1]
            
            # If this is a new line (different Y position)
            if current_y is None or abs(y_pos - current_y) > 10:  # 10 pixel tolerance
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = []
                current_y = y_pos
            
            current_line.append(result.text)
        
        # Add the last line
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def _calculate_overall_confidence(self, page_results: List[PageResult]) -> float:
        """
        Calculate overall confidence from page results
        
        Args:
            page_results: List of PageResult objects
            
        Returns:
            Overall confidence score (0.0 to 1.0)
        """
        if not page_results:
            return 0.0
        
        # Calculate weighted average based on page confidence and processing success
        total_weight = 0
        weighted_sum = 0
        
        for page_result in page_results:
            if page_result.error is None:
                # Successful page gets full weight
                weight = 1.0
                confidence = page_result.confidence
            else:
                # Failed page gets reduced weight
                weight = 0.1
                confidence = 0.0
            
            weighted_sum += confidence * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return weighted_sum / total_weight
    
    def _create_minimal_result(self, file_path: str, error: str, processing_time: float) -> DocumentResult:
        """
        Create minimal result when processing fails
        
        Args:
            file_path: Path to the file
            error: Error message
            processing_time: Processing time taken
            
        Returns:
            Minimal DocumentResult
        """
        logger.warning(f"🚨 Creating minimal result due to processing failure: {error}")
        
        return DocumentResult(
            document_type='unknown',
            supplier='Unknown Supplier',
            invoice_number='Unknown',
            date='Unknown',
            line_items=[],
            page_results=[],
            overall_confidence=0.0,
            total_processing_time=processing_time,
            pages_processed=0,
            pages_failed=1
        )

# Global instance for easy access
multi_page_processor = MultiPageProcessor() 