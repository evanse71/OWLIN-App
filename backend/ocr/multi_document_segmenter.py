"""
Multi-Document Segmenter - Bulletproof Ingestion v3

Handles document segmentation, page processing, and feature extraction for
the bulletproof ingestion pipeline.
"""

import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path
import re
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class PageSegment:
    """Page segment data structure"""
    id: str
    file_id: str
    page_index: int
    doc_type: str
    supplier_guess: str
    page_numbers: List[int]
    text: str
    phash: str
    header_simhash: str
    footer_simhash: str
    features: Dict[str, Any]
    confidence: float
    upload_time: datetime

@dataclass
class DocumentSegment:
    """Document segment data structure"""
    id: str
    file_id: str
    doc_type: str
    supplier_guess: str
    page_range: List[int]
    fingerprint_hashes: Dict[str, str]
    segments: List[PageSegment]
    confidence: float
    stitch_group_id: Optional[str]
    created_at: datetime

class MultiDocumentSegmenter:
    """Multi-document segmentation system"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.segment_confidence_threshold = self.config.get('segment_confidence_threshold', 0.7)
        self.min_segment_pages = self.config.get('min_segment_pages', 1)
        self.max_segment_pages = self.config.get('max_segment_pages', 10)
        
    def process_files(self, files: List[Dict[str, Any]]) -> List[DocumentSegment]:
        """
        Process multiple files and create document segments
        
        Args:
            files: List of file data with paths, images, and OCR text
            
        Returns:
            List of document segments
        """
        logger.info(f"🔄 Starting multi-document segmentation for {len(files)} files")
        
        all_segments = []
        
        for file_data in files:
            file_id = file_data.get('id', str(uuid.uuid4()))
            file_path = file_data.get('file_path', '')
            images = file_data.get('images', [])
            ocr_texts = file_data.get('ocr_texts', [])
            
            logger.info(f"📄 Processing file {file_id} with {len(images)} pages")
            
            # Process each page in the file
            page_segments = []
            for i, (image, ocr_text) in enumerate(zip(images, ocr_texts)):
                page_segment = self._process_page(file_id, i, image, ocr_text, file_path)
                if page_segment:
                    page_segments.append(page_segment)
            
            # Group pages into document segments
            document_segments = self._group_pages_into_segments(file_id, page_segments)
            all_segments.extend(document_segments)
            
            logger.info(f"✅ Created {len(document_segments)} document segments from file {file_id}")
        
        logger.info(f"🎯 Completed segmentation: {len(all_segments)} total document segments")
        return all_segments
    
    def _process_page(self, file_id: str, page_index: int, image: Any, ocr_text: str, file_path: str) -> Optional[PageSegment]:
        """
        Process a single page and extract features
        
        Args:
            file_id: File identifier
            page_index: Page index within file
            image: Page image
            ocr_text: OCR text content
            file_path: File path
            
        Returns:
            PageSegment object or None if processing failed
        """
        try:
            page_id = f"{file_id}_page_{page_index}"
            
            # Extract features
            features = self._extract_page_features(image, ocr_text)
            
            # Classify document type
            doc_type = self._classify_document_type(ocr_text, features)
            
            # Extract supplier guess
            supplier_guess = self._extract_supplier_guess(ocr_text)
            
            # Compute fingerprints
            phash = self._compute_phash(image)
            header_simhash = self._compute_header_simhash(ocr_text)
            footer_simhash = self._compute_footer_simhash(ocr_text)
            
            # Calculate confidence
            confidence = self._calculate_confidence(features, doc_type)
            
            return PageSegment(
                id=page_id,
                file_id=file_id,
                page_index=page_index,
                doc_type=doc_type,
                supplier_guess=supplier_guess,
                page_numbers=[page_index],
                text=ocr_text,
                phash=phash,
                header_simhash=header_simhash,
                footer_simhash=footer_simhash,
                features=features,
                confidence=confidence,
                upload_time=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to process page {page_index} in file {file_id}: {e}")
            return None
    
    def _extract_page_features(self, image: Any, ocr_text: str) -> Dict[str, Any]:
        """
        Extract features from page image and text
        
        Args:
            image: Page image
            ocr_text: OCR text content
            
        Returns:
            Dictionary of extracted features
        """
        features = {}
        
        # Text-based features
        features['text_length'] = len(ocr_text)
        features['word_count'] = len(ocr_text.split())
        features['line_count'] = ocr_text.count('\n')
        
        # Document type indicators
        text_lower = ocr_text.lower()
        features['has_invoice_keywords'] = any(kw in text_lower for kw in ['invoice', 'bill', 'statement'])
        features['has_delivery_keywords'] = any(kw in text_lower for kw in ['delivery', 'goods received', 'pod'])
        features['has_receipt_keywords'] = any(kw in text_lower for kw in ['receipt', 'payment', 'transaction'])
        features['has_utility_keywords'] = any(kw in text_lower for kw in ['energy', 'kwh', 'utility', 'meter'])
        
        # Layout features
        features['has_table'] = self._detect_table_layout(ocr_text)
        features['has_header'] = self._detect_header(ocr_text)
        features['has_footer'] = self._detect_footer(ocr_text)
        features['has_page_numbers'] = bool(re.search(r'\b(?:page|p)\s*\d+\s*(?:of\s*\d+)?\b', ocr_text, re.IGNORECASE))
        
        # Amount features
        features['has_currency'] = bool(re.search(r'[£$€]\s*[\d,]+\.?\d*', ocr_text))
        features['has_totals'] = bool(re.search(r'\b(?:total|amount|sum|due)\s*:?\s*[£$€]?\s*[\d,]+\.?\d*\b', ocr_text, re.IGNORECASE))
        
        return features
    
    def _classify_document_type(self, text: str, features: Dict[str, Any]) -> str:
        """
        Classify document type based on features
        
        Args:
            text: OCR text content
            features: Extracted features
            
        Returns:
            Document type (invoice, delivery, receipt, utility, other)
        """
        text_lower = text.lower()
        
        # Calculate scores for each document type
        scores = {
            'invoice': 0.0,
            'delivery': 0.0,
            'receipt': 0.0,
            'utility': 0.0,
            'other': 0.0
        }
        
        # Invoice indicators
        if features.get('has_invoice_keywords', False):
            scores['invoice'] += 0.4
        if features.get('has_currency', False):
            scores['invoice'] += 0.2
        if features.get('has_totals', False):
            scores['invoice'] += 0.2
        if re.search(r'\b(?:invoice|inv)\s*#?\s*:?\s*([A-Za-z0-9\-_/]{3,20})\b', text, re.IGNORECASE):
            scores['invoice'] += 0.3
        
        # Delivery indicators
        if features.get('has_delivery_keywords', False):
            scores['delivery'] += 0.4
        if re.search(r'\b(?:delivery|goods received|pod)\b', text_lower):
            scores['delivery'] += 0.3
        
        # Receipt indicators
        if features.get('has_receipt_keywords', False):
            scores['receipt'] += 0.4
        if re.search(r'\b(?:receipt|payment|transaction)\b', text_lower):
            scores['receipt'] += 0.3
        
        # Utility indicators
        if features.get('has_utility_keywords', False):
            scores['utility'] += 0.4
        if re.search(r'\b(?:energy|kwh|meter|utility)\b', text_lower):
            scores['utility'] += 0.3
        
        # Find the document type with highest score
        best_type = max(scores, key=scores.get)
        
        # If no strong indicators, default to 'other'
        if scores[best_type] < 0.3:
            return 'other'
        
        return best_type
    
    def _extract_supplier_guess(self, text: str) -> str:
        """
        Extract supplier name from text
        
        Args:
            text: OCR text content
            
        Returns:
            Extracted supplier name or empty string
        """
        patterns = [
            r'\b([A-Z][A-Z\s&\.]+(?:LTD|LIMITED|INC|CORP|LLC|CO|COMPANY))\b',
            r'^(?:from|supplier|company):\s*([A-Za-z\s&\.]+)',
            r'\b([A-Z][A-Z\s&\.]{3,20})\s+(?:invoice|delivery|receipt)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0].strip()
        
        return ""
    
    def _compute_phash(self, image: Any) -> str:
        """
        Compute perceptual hash for image
        
        Args:
            image: Page image
            
        Returns:
            Perceptual hash as hexadecimal string
        """
        try:
            # For now, return a placeholder hash
            # In a real implementation, this would use imagehash or similar
            return hashlib.md5(str(image).encode()).hexdigest()[:16]
        except Exception as e:
            logger.error(f"Failed to compute perceptual hash: {e}")
            return "0" * 16
    
    def _compute_header_simhash(self, text: str) -> str:
        """
        Compute simhash for header section
        
        Args:
            text: OCR text content
            
        Returns:
            Header simhash as hexadecimal string
        """
        try:
            # Extract header (first 10% of text)
            header_length = max(1, len(text) // 10)
            header_text = text[:header_length]
            
            # Simple hash for now
            return hashlib.md5(header_text.encode()).hexdigest()[:16]
        except Exception as e:
            logger.error(f"Failed to compute header simhash: {e}")
            return "0" * 16
    
    def _compute_footer_simhash(self, text: str) -> str:
        """
        Compute simhash for footer section
        
        Args:
            text: OCR text content
            
        Returns:
            Footer simhash as hexadecimal string
        """
        try:
            # Extract footer (last 10% of text)
            footer_length = max(1, len(text) // 10)
            footer_text = text[-footer_length:]
            
            # Simple hash for now
            return hashlib.md5(footer_text.encode()).hexdigest()[:16]
        except Exception as e:
            logger.error(f"Failed to compute footer simhash: {e}")
            return "0" * 16
    
    def _calculate_confidence(self, features: Dict[str, Any], doc_type: str) -> float:
        """
        Calculate confidence score for page classification
        
        Args:
            features: Extracted features
            doc_type: Classified document type
            
        Returns:
            Confidence score (0-1)
        """
        confidence = 0.5  # Base confidence
        
        # Boost confidence based on feature strength
        if features.get('has_invoice_keywords', False) and doc_type == 'invoice':
            confidence += 0.3
        elif features.get('has_delivery_keywords', False) and doc_type == 'delivery':
            confidence += 0.3
        elif features.get('has_receipt_keywords', False) and doc_type == 'receipt':
            confidence += 0.3
        elif features.get('has_utility_keywords', False) and doc_type == 'utility':
            confidence += 0.3
        
        # Boost confidence based on text quality
        if features.get('text_length', 0) > 100:
            confidence += 0.1
        if features.get('word_count', 0) > 50:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _detect_table_layout(self, text: str) -> bool:
        """Detect if text contains table-like layout"""
        # Look for table indicators
        table_patterns = [
            r'\b(?:qty|quantity|description|unit|price|amount|total)\b',
            r'\d+\s+\d+\.?\d*\s+\d+\.?\d*',  # Number patterns
            r'^\s*\w+\s+\w+\s+\w+',  # Multiple columns
        ]
        
        for pattern in table_patterns:
            if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                return True
        
        return False
    
    def _detect_header(self, text: str) -> bool:
        """Detect if text has a header section"""
        # Look for header indicators
        header_patterns = [
            r'^(?:invoice|bill|statement|delivery|receipt)',
            r'^\s*[A-Z][A-Z\s&\.]+(?:LTD|LIMITED|INC|CORP|LLC|CO|COMPANY)',
            r'\b(?:invoice|inv)\s*#?\s*:?\s*([A-Za-z0-9\-_/]{3,20})\b'
        ]
        
        lines = text.split('\n')
        for line in lines[:3]:  # Check first 3 lines
            for pattern in header_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    return True
        
        return False
    
    def _detect_footer(self, text: str) -> bool:
        """Detect if text has a footer section"""
        # Look for footer indicators
        footer_patterns = [
            r'\b(?:page|p)\s*\d+\s*(?:of\s*\d+)?\b',
            r'\b(?:total|amount|due|balance)\s*:?\s*[£$€]?\s*[\d,]+\.?\d*\b',
            r'^\s*\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\s*$'  # Date at end
        ]
        
        lines = text.split('\n')
        for line in lines[-3:]:  # Check last 3 lines
            for pattern in footer_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    return True
        
        return False
    
    def _group_pages_into_segments(self, file_id: str, page_segments: List[PageSegment]) -> List[DocumentSegment]:
        """
        Group pages into document segments
        
        Args:
            file_id: File identifier
            page_segments: List of page segments
            
        Returns:
            List of document segments
        """
        if not page_segments:
            return []
        
        # Sort pages by index
        page_segments.sort(key=lambda x: x.page_index)
        
        segments = []
        current_segment = None
        
        for page_segment in page_segments:
            # Check if this page starts a new segment
            if self._should_start_new_segment(page_segment, current_segment):
                # Save current segment if exists
                if current_segment:
                    segments.append(current_segment)
                
                # Start new segment
                current_segment = DocumentSegment(
                    id=f"seg_{file_id}_{len(segments)}",
                    file_id=file_id,
                    doc_type=page_segment.doc_type,
                    supplier_guess=page_segment.supplier_guess,
                    page_range=[page_segment.page_index],
                    fingerprint_hashes={
                        'phash': page_segment.phash,
                        'header_simhash': page_segment.header_simhash,
                        'footer_simhash': page_segment.footer_simhash,
                        'text_hash': hashlib.md5(page_segment.text.encode()).hexdigest()
                    },
                    segments=[page_segment],
                    confidence=page_segment.confidence,
                    stitch_group_id=None,
                    created_at=datetime.now()
                )
            else:
                # Add page to current segment
                if current_segment:
                    current_segment.page_range.append(page_segment.page_index)
                    current_segment.segments.append(page_segment)
                    current_segment.text += f"\n--- PAGE {page_segment.page_index} ---\n{page_segment.text}"
                    
                    # Update fingerprint hashes
                    current_segment.fingerprint_hashes['text_hash'] = hashlib.md5(
                        current_segment.text.encode()
                    ).hexdigest()
        
        # Add final segment
        if current_segment:
            segments.append(current_segment)
        
        return segments
    
    def _should_start_new_segment(self, page_segment: PageSegment, current_segment: Optional[DocumentSegment]) -> bool:
        """
        Determine if a page should start a new segment
        
        Args:
            page_segment: Current page segment
            current_segment: Current document segment
            
        Returns:
            True if should start new segment
        """
        if not current_segment:
            return True
        
        # Check for document type change
        if page_segment.doc_type != current_segment.doc_type:
            return True
        
        # Check for supplier change
        if (page_segment.supplier_guess and current_segment.supplier_guess and 
            page_segment.supplier_guess != current_segment.supplier_guess):
            return True
        
        # Check for totals block (end of invoice)
        text_lower = page_segment.text.lower()
        if any(keyword in text_lower for keyword in ['total', 'amount due', 'grand total', 'final total']):
            return False  # This is likely the end of a segment
        
        return False 