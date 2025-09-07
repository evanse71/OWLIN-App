"""
Canonical Builder - Bulletproof Ingestion v3

Builds canonical document entities from stitch groups and segments.
Handles parsing with Qwen2.5-VL and creates the final truth entities.
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class CanonicalInvoice:
    """Canonical invoice entity - the final truth"""
    canonical_id: str
    supplier_name: str
    invoice_number: str
    invoice_date: str
    currency: str
    subtotal: float
    tax: float
    total_amount: float
    field_confidence: Dict[str, float]
    warnings: List[str]
    raw_extraction: Dict[str, Any]
    source_segments: List[str]
    source_pages: List[int]
    confidence: float
    created_at: datetime

@dataclass
class CanonicalDocument:
    """Canonical document entity (non-invoice)"""
    canonical_id: str
    doc_type: str  # delivery, receipt, utility, other
    supplier_name: str
    document_number: str
    document_date: str
    content: Dict[str, Any]
    confidence: float
    source_segments: List[str]
    source_pages: List[int]
    created_at: datetime

class CanonicalBuilder:
    """Canonical entity builder"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.min_confidence = self.config.get('canonical_builder_min_confidence', 0.60)
        
    def build_canonical_invoice(self, stitch_group: Any, segments: List[Dict[str, Any]]) -> Optional[CanonicalInvoice]:
        """
        Build canonical invoice from stitch group
        
        Args:
            stitch_group: StitchGroup object
            segments: List of segment data
            
        Returns:
            CanonicalInvoice object or None if failed
        """
        try:
            # Get all text from segments in the group
            all_text = ""
            source_segments = []
            source_pages = []
            
            for segment in stitch_group.segments:
                segment_id = segment.get('id', 'unknown')
                source_segments.append(segment_id)
                
                text = segment.get('text', '')
                if text:
                    all_text += f"\n--- SEGMENT {segment_id} ---\n{text}"
                
                # Get page numbers
                pages = segment.get('page_numbers', [])
                if pages:
                    source_pages.extend(pages)
            
            # Try LLM parsing first
            llm_result = self._parse_with_llm(all_text)
            if llm_result:
                return self._create_canonical_invoice_from_llm(
                    llm_result, stitch_group, source_segments, source_pages
                )
            
            # Fallback to rule-based parsing
            rule_result = self._parse_with_rules(all_text)
            if rule_result:
                return self._create_canonical_invoice_from_rules(
                    rule_result, stitch_group, source_segments, source_pages
                )
            
            logger.warning(f"Failed to parse canonical invoice for group {stitch_group.group_id}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to build canonical invoice: {e}")
            return None
    
    def _parse_with_llm(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parse text using Qwen2.5-VL LLM
        
        Args:
            text: Combined text from segments
            
        Returns:
            Parsed result dictionary or None if failed
        """
        try:
            # Import LLM client
            from backend.llm.llm_client import parse_invoice
            from backend.types.parsed_invoice import InvoiceParsingPayload
            
            # Create payload for LLM
            payload = InvoiceParsingPayload(
                text=text,
                tables=None,
                page_images=None,
                hints={}
            )
            
            # Parse with LLM
            result = parse_invoice(payload)
            
            # Convert to dictionary
            return {
                'supplier_name': result.supplier_name,
                'invoice_number': result.invoice_number,
                'invoice_date': result.invoice_date,
                'currency': result.currency,
                'subtotal': result.subtotal,
                'tax': result.tax,
                'total_amount': result.total_amount,
                'line_items': result.line_items,
                'field_confidence': result.field_confidence,
                'warnings': result.warnings,
                'raw_extraction': result.raw_extraction
            }
            
        except Exception as e:
            logger.warning(f"LLM parsing failed: {e}")
            return None
    
    def _parse_with_rules(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parse text using rule-based extraction
        
        Args:
            text: Combined text from segments
            
        Returns:
            Parsed result dictionary or None if failed
        """
        try:
            result = {
                'supplier_name': '',
                'invoice_number': '',
                'invoice_date': '',
                'currency': 'GBP',
                'subtotal': 0.0,
                'tax': 0.0,
                'total_amount': 0.0,
                'line_items': [],
                'field_confidence': {},
                'warnings': [],
                'raw_extraction': {'method': 'rule-based'}
            }
            
            # Extract supplier name
            supplier_patterns = [
                r'\b([A-Z][A-Z\s&\.]+(?:LTD|LIMITED|INC|CORP|LLC|CO|COMPANY))\b',
                r'^(?:from|supplier|company):\s*([A-Za-z\s&\.]+)',
                r'\b([A-Z][A-Z\s&\.]{3,20})\s+(?:invoice|delivery|receipt)'
            ]
            
            for pattern in supplier_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    result['supplier_name'] = matches[0].strip()
                    result['field_confidence']['supplier_name'] = 0.8
                    break
            
            # Extract invoice number
            invoice_patterns = [
                r'\b(?:invoice|inv)\s*#?\s*:?\s*([A-Za-z0-9\-_/]{3,20})\b',
                r'\b(INV[0-9\-_/]{3,20})\b',
                r'\b([A-Z]{2,4}[0-9]{3,8})\b'
            ]
            
            for pattern in invoice_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    result['invoice_number'] = matches[0]
                    result['field_confidence']['invoice_number'] = 0.8
                    break
            
            # Extract invoice date
            date_patterns = [
                r'\b(?:date|dated|invoice date)\s*:?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b',
                r'\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b',
                r'\b(\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})\b'
            ]
            
            for pattern in date_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    result['invoice_date'] = matches[0]
                    result['field_confidence']['invoice_date'] = 0.7
                    break
            
            # Extract total amount
            total_patterns = [
                r'\b(?:total|amount|sum|due)\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)\b',
                r'[£$€]\s*([\d,]+\.?\d*)\s*(?:total|amount)',
                r'\b(?:grand total|final total)\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)\b'
            ]
            
            for pattern in total_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    try:
                        total = float(matches[0].replace(',', ''))
                        result['total_amount'] = total
                        result['field_confidence']['total_amount'] = 0.8
                        break
                    except:
                        continue
            
            # Extract currency
            currency_patterns = [
                r'[£$€]',
                r'\b(?:gbp|pounds?|euros?|dollars?)\b'
            ]
            
            for pattern in currency_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    result['currency'] = matches[0].upper()
                    break
            
            return result
            
        except Exception as e:
            logger.error(f"Rule-based parsing failed: {e}")
            return None
    
    def _create_canonical_invoice_from_llm(self, llm_result: Dict[str, Any], 
                                         stitch_group: Any, source_segments: List[str], 
                                         source_pages: List[int]) -> CanonicalInvoice:
        """Create canonical invoice from LLM result"""
        return CanonicalInvoice(
            canonical_id=f"canonical_inv_{stitch_group.group_id}",
            supplier_name=llm_result.get('supplier_name', ''),
            invoice_number=llm_result.get('invoice_number', ''),
            invoice_date=llm_result.get('invoice_date', ''),
            currency=llm_result.get('currency', 'GBP'),
            subtotal=llm_result.get('subtotal', 0.0),
            tax=llm_result.get('tax', 0.0),
            total_amount=llm_result.get('total_amount', 0.0),
            field_confidence=llm_result.get('field_confidence', {}),
            warnings=llm_result.get('warnings', []),
            raw_extraction=llm_result.get('raw_extraction', {}),
            source_segments=source_segments,
            source_pages=source_pages,
            confidence=stitch_group.confidence,
            created_at=datetime.now()
        )
    
    def _create_canonical_invoice_from_rules(self, rule_result: Dict[str, Any], 
                                           stitch_group: Any, source_segments: List[str], 
                                           source_pages: List[int]) -> CanonicalInvoice:
        """Create canonical invoice from rule-based result"""
        return CanonicalInvoice(
            canonical_id=f"canonical_inv_{stitch_group.group_id}",
            supplier_name=rule_result.get('supplier_name', ''),
            invoice_number=rule_result.get('invoice_number', ''),
            invoice_date=rule_result.get('invoice_date', ''),
            currency=rule_result.get('currency', 'GBP'),
            subtotal=rule_result.get('subtotal', 0.0),
            tax=rule_result.get('tax', 0.0),
            total_amount=rule_result.get('total_amount', 0.0),
            field_confidence=rule_result.get('field_confidence', {}),
            warnings=rule_result.get('warnings', []),
            raw_extraction=rule_result.get('raw_extraction', {}),
            source_segments=source_segments,
            source_pages=source_pages,
            confidence=stitch_group.confidence * 0.8,  # Reduce confidence for rule-based
            created_at=datetime.now()
        )
    
    def build_canonical_document(self, stitch_group: Any, segments: List[Dict[str, Any]]) -> Optional[CanonicalDocument]:
        """
        Build canonical document (non-invoice) from stitch group
        
        Args:
            stitch_group: StitchGroup object
            segments: List of segment data
            
        Returns:
            CanonicalDocument object or None if failed
        """
        try:
            # Get all text from segments in the group
            all_text = ""
            source_segments = []
            source_pages = []
            
            for segment in stitch_group.segments:
                segment_id = segment.get('id', 'unknown')
                source_segments.append(segment_id)
                
                text = segment.get('text', '')
                if text:
                    all_text += f"\n--- SEGMENT {segment_id} ---\n{text}"
                
                # Get page numbers
                pages = segment.get('page_numbers', [])
                if pages:
                    source_pages.extend(pages)
            
            # Extract basic information
            supplier_name = stitch_group.supplier_guess or ""
            document_number = stitch_group.invoice_numbers[0] if stitch_group.invoice_numbers else ""
            document_date = stitch_group.dates[0] if stitch_group.dates else ""
            
            # Create content based on document type
            content = {
                'text': all_text,
                'doc_type': stitch_group.doc_type,
                'segments_count': len(stitch_group.segments),
                'extracted_features': self._extract_document_features(all_text, stitch_group.doc_type)
            }
            
            return CanonicalDocument(
                canonical_id=f"canonical_doc_{stitch_group.group_id}",
                doc_type=stitch_group.doc_type,
                supplier_name=supplier_name,
                document_number=document_number,
                document_date=document_date,
                content=content,
                confidence=stitch_group.confidence,
                source_segments=source_segments,
                source_pages=source_pages,
                created_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to build canonical document: {e}")
            return None
    
    def _extract_document_features(self, text: str, doc_type: str) -> Dict[str, Any]:
        """Extract features specific to document type"""
        features = {}
        
        if doc_type == 'delivery':
            # Extract delivery-specific features
            features['items'] = self._extract_delivery_items(text)
            features['delivery_date'] = self._extract_delivery_date(text)
            features['received_by'] = self._extract_received_by(text)
        elif doc_type == 'receipt':
            # Extract receipt-specific features
            features['transaction_id'] = self._extract_transaction_id(text)
            features['payment_method'] = self._extract_payment_method(text)
            features['items'] = self._extract_receipt_items(text)
        elif doc_type == 'utility':
            # Extract utility-specific features
            features['meter_readings'] = self._extract_meter_readings(text)
            features['consumption'] = self._extract_consumption(text)
            features['billing_period'] = self._extract_billing_period(text)
        
        return features
    
    def _extract_delivery_items(self, text: str) -> List[Dict[str, Any]]:
        """Extract delivery items from text"""
        items = []
        # Basic pattern matching for delivery items
        patterns = [
            r'(\d+)\s*(?:x|×)?\s*([A-Za-z\s]+?)(?:\s+@\s*[£$€]?\s*[\d,]+\.?\d*)?\s*$',
            r'([A-Za-z\s]+?)\s*(\d+)\s*(?:units?|pcs?|kg|g|l|ml)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 2:
                    items.append({
                        'quantity': match[0],
                        'description': match[1].strip()
                    })
                else:
                    items.append({'description': match.strip()})
        
        return items
    
    def _extract_delivery_date(self, text: str) -> str:
        """Extract delivery date from text"""
        patterns = [
            r'(?:delivered|delivery)\s+(?:on|date)?\s*:?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
            r'(?:delivered|delivery)\s+(?:on|date)?\s*:?\s*(\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0]
        
        return ""
    
    def _extract_received_by(self, text: str) -> str:
        """Extract received by from text"""
        patterns = [
            r'(?:received|signed)\s+(?:by|for)\s*:?\s*([A-Za-z\s]+)',
            r'(?:received|signed)\s*:?\s*([A-Za-z\s]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0].strip()
        
        return ""
    
    def _extract_transaction_id(self, text: str) -> str:
        """Extract transaction ID from receipt"""
        patterns = [
            r'(?:transaction|ref|reference|id)\s*#?\s*:?\s*([A-Za-z0-9\-_/]+)',
            r'#([A-Za-z0-9\-_/]{6,})',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0]
        
        return ""
    
    def _extract_payment_method(self, text: str) -> str:
        """Extract payment method from receipt"""
        payment_methods = ['cash', 'card', 'credit', 'debit', 'paypal', 'bank transfer']
        
        for method in payment_methods:
            if method in text.lower():
                return method.title()
        
        return "Unknown"
    
    def _extract_receipt_items(self, text: str) -> List[Dict[str, Any]]:
        """Extract receipt items from text"""
        items = []
        # Similar to delivery items but for receipts
        patterns = [
            r'([A-Za-z\s]+?)\s+[£$€]?\s*([\d,]+\.?\d*)',
            r'(\d+)\s*(?:x|×)?\s*([A-Za-z\s]+?)\s*[£$€]?\s*([\d,]+\.?\d*)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    if len(match) == 2:
                        items.append({
                            'description': match[0].strip(),
                            'amount': match[1]
                        })
                    elif len(match) == 3:
                        items.append({
                            'quantity': match[0],
                            'description': match[1].strip(),
                            'amount': match[2]
                        })
        
        return items
    
    def _extract_meter_readings(self, text: str) -> Dict[str, Any]:
        """Extract meter readings from utility bill"""
        readings = {}
        patterns = [
            r'(?:meter|reading)\s*:?\s*(\d+)',
            r'(?:current|present)\s*:?\s*(\d+)',
            r'(?:previous|last)\s*:?\s*(\d+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                readings['reading'] = matches[0]
                break
        
        return readings
    
    def _extract_consumption(self, text: str) -> str:
        """Extract consumption from utility bill"""
        patterns = [
            r'consumption\s*:?\s*(\d+(?:\.\d+)?)\s*(kwh|kw|units?)',
            r'usage\s*:?\s*(\d+(?:\.\d+)?)\s*(kwh|kw|units?)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return f"{matches[0][0]} {matches[0][1]}"
        
        return ""
    
    def _extract_billing_period(self, text: str) -> str:
        """Extract billing period from utility bill"""
        patterns = [
            r'(?:billing|bill)\s+(?:period|date)\s*:?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
            r'(?:from|between)\s+(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\s+(?:to|and)\s+(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                if isinstance(matches[0], tuple):
                    return f"{matches[0][0]} to {matches[0][1]}"
                else:
                    return matches[0]
        
        return ""
    
    def build_canonical_entities(self, stitch_groups: List[Any], segments: List[Dict[str, Any]]) -> Tuple[List[CanonicalInvoice], List[CanonicalDocument]]:
        """
        Build all canonical entities from stitch groups
        
        Args:
            stitch_groups: List of StitchGroup objects
            segments: List of segment data
            
        Returns:
            Tuple of (canonical_invoices, canonical_documents)
        """
        canonical_invoices = []
        canonical_documents = []
        
        for stitch_group in stitch_groups:
            if stitch_group.confidence < self.min_confidence:
                logger.warning(f"Skipping low-confidence stitch group {stitch_group.group_id}")
                continue
            
            if stitch_group.doc_type == 'invoice':
                canonical_inv = self.build_canonical_invoice(stitch_group, segments)
                if canonical_inv:
                    canonical_invoices.append(canonical_inv)
            else:
                canonical_doc = self.build_canonical_document(stitch_group, segments)
                if canonical_doc:
                    canonical_documents.append(canonical_doc)
        
        logger.info(f"✅ Built {len(canonical_invoices)} canonical invoices and {len(canonical_documents)} canonical documents")
        return canonical_invoices, canonical_documents 