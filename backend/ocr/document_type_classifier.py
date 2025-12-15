#!/usr/bin/env python3
"""
Deterministic Document Type Classifier

Classifies documents as invoice, delivery_note, or unknown using a layered approach:
- Layer 1: High-signal keywords (per-page)
- Layer 2: Field presence patterns
- Layer 3: Layout cues (optional, offline)

Returns classification with confidence score and human-readable reasons.
"""

import re
import json
import logging
from dataclasses import dataclass
from typing import List, Dict, Literal, Optional, Tuple

logger = logging.getLogger(__name__)

@dataclass
class DocumentClassification:
    """Document classification result"""
    doc_type: Literal["invoice", "delivery_note", "unknown"]
    confidence: float  # 0-100 scale
    reasons: List[str]  # Human-readable reasons for classification


class DocumentTypeClassifier:
    """Deterministic document type classifier"""
    
    # Layer 1: High-signal keywords (case-insensitive)
    DELIVERY_NOTE_KEYWORDS = [
        "DELIVERY NOTE",
        "DEL NOTE",
        "D/N",
        "DELIVERY",
        "GOODS RECEIPT",
        "POD",  # Proof of Delivery
        "RECEIVED BY",
        "DRIVER",
        "SIGNATURE",
        "DELIVERED TO",
        "GOODS RECEIVED NOTE",
        "GRN",
        "DELIVERY RECEIPT",
        "PACKING LIST",
        "DISPATCH NOTE"
    ]
    
    INVOICE_KEYWORDS = [
        "INVOICE",
        "TAX INVOICE",
        "VAT INVOICE",
        "INVOICE NUMBER",
        "VAT REG",
        "TOTAL DUE",
        "AMOUNT DUE",
        "PAYMENT TERMS",
        "DUE DATE",
        "BILL TO",
        "INVOICE DATE",
        "TAX REGISTRATION",
        "VAT REGISTRATION",
        "INVOICE NO",
        "INV NO"
    ]
    
    # Layer 2: Field patterns (regex)
    INVOICE_FIELD_PATTERNS = {
        "invoice_number": [
            r'\b(?:invoice|inv)\s*(?:no|number|#)?\s*:?\s*([A-Z0-9\-/]+)',
            r'\b(?:invoice|inv)\s*#?\s*([A-Z0-9\-/]+)',
        ],
        "vat_reg": [
            r'\b(?:vat|tax)\s*(?:reg|registration|reg\.?)\s*:?\s*([A-Z0-9]+)',
            r'\b(?:vat|tax)\s*(?:no|number)\s*:?\s*([A-Z0-9]+)',
        ],
        "totals": [
            r'\b(?:total|grand\s+total|amount\s+due|balance\s+due)\s*:?\s*[£€$]?\s*([\d,]+\.?\d*)',
            r'\b(?:subtotal|net\s+amount)\s*:?\s*[£€$]?\s*([\d,]+\.?\d*)',
        ],
        "vat_rate": [
            r'\b(?:vat|tax)\s*(?:rate|%)?\s*:?\s*(\d+(?:\.\d+)?)\s*%',
            r'\b(\d+(?:\.\d+)?)\s*%\s*(?:vat|tax)',
        ],
    }
    
    DELIVERY_NOTE_FIELD_PATTERNS = {
        "delivery_date": [
            r'\b(?:delivery|delivered)\s*(?:date|on)\s*:?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
            r'\b(?:date\s+of\s+delivery)\s*:?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
        ],
        "received_by": [
            r'\b(?:received\s+by|signed\s+by|authorized\s+by)\s*:?\s*([A-Z][A-Za-z\s]+)',
            r'\b(?:signature)\s*:?\s*([A-Z][A-Za-z\s]+)',
        ],
        "delivered_to": [
            r'\b(?:delivered\s+to|ship\s+to|delivery\s+address)\s*:?\s*([A-Z][A-Za-z0-9\s,]+)',
        ],
        "signature_box": [
            r'\b(?:signature|sign)\s*(?:box|field|area)',
            r'\b(?:authorized\s+signature)',
        ],
    }
    
    def classify(self, text: str, pages: Optional[List[str]] = None) -> DocumentClassification:
        """
        Classify document type from text content.
        
        Args:
            text: Full document text (or combined from pages)
            pages: Optional list of per-page text for multi-page analysis
            
        Returns:
            DocumentClassification with type, confidence, and reasons
        """
        if not text or len(text.strip()) < 10:
            return DocumentClassification(
                doc_type="unknown",
                confidence=0.0,
                reasons=["Text too short for classification"]
            )
        
        text_upper = text.upper()
        reasons = []
        
        # Layer 1: Keyword matching (per-page if available)
        invoice_keyword_matches = []
        delivery_keyword_matches = []
        
        if pages:
            # Analyze per-page for better coverage
            for i, page_text in enumerate(pages):
                page_upper = page_text.upper()
                page_invoice_matches = []
                page_delivery_matches = []
                
                for keyword in self.INVOICE_KEYWORDS:
                    if keyword in page_upper:
                        page_invoice_matches.append(keyword)
                        if keyword not in invoice_keyword_matches:
                            invoice_keyword_matches.append(keyword)
                
                for keyword in self.DELIVERY_NOTE_KEYWORDS:
                    if keyword in page_upper:
                        page_delivery_matches.append(keyword)
                        if keyword not in delivery_keyword_matches:
                            delivery_keyword_matches.append(keyword)
                
                if page_invoice_matches:
                    reasons.append(f"Found invoice keywords on page {i+1}: {', '.join(page_invoice_matches[:3])}")
                if page_delivery_matches:
                    reasons.append(f"Found delivery note keywords on page {i+1}: {', '.join(page_delivery_matches[:3])}")
        else:
            # Single text analysis
            for keyword in self.INVOICE_KEYWORDS:
                if keyword in text_upper:
                    invoice_keyword_matches.append(keyword)
            
            for keyword in self.DELIVERY_NOTE_KEYWORDS:
                if keyword in text_upper:
                    delivery_keyword_matches.append(keyword)
        
        # Calculate keyword scores
        invoice_keyword_score = len(invoice_keyword_matches)
        delivery_keyword_score = len(delivery_keyword_matches)
        
        if invoice_keyword_matches:
            reasons.append(f"Found {len(invoice_keyword_matches)} invoice keyword(s): {', '.join(invoice_keyword_matches[:5])}")
        if delivery_keyword_matches:
            reasons.append(f"Found {len(delivery_keyword_matches)} delivery note keyword(s): {', '.join(delivery_keyword_matches[:5])}")
        
        # Layer 2: Field presence patterns
        invoice_field_score = 0
        delivery_field_score = 0
        
        # Check invoice fields
        for field_type, patterns in self.INVOICE_FIELD_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    invoice_field_score += 1
                    reasons.append(f"Found invoice field: {field_type}")
                    break  # Count each field type only once
        
        # Check delivery note fields
        for field_type, patterns in self.DELIVERY_NOTE_FIELD_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    delivery_field_score += 1
                    reasons.append(f"Found delivery note field: {field_type}")
                    break  # Count each field type only once
        
        # Calculate combined scores
        # Keywords are weighted more heavily (2x) than field patterns
        invoice_total_score = (invoice_keyword_score * 2) + invoice_field_score
        delivery_total_score = (delivery_keyword_score * 2) + delivery_field_score
        
        # Determine document type
        if invoice_total_score == 0 and delivery_total_score == 0:
            return DocumentClassification(
                doc_type="unknown",
                confidence=0.0,
                reasons=["No clear document type indicators found"] + reasons
            )
        
        # Calculate confidence based on score difference and absolute scores
        if invoice_total_score > delivery_total_score:
            doc_type = "invoice"
            score_diff = invoice_total_score - delivery_total_score
            # Base confidence: 50% + (score_diff * 10%) + (absolute_score * 5%)
            # Cap at 95% to leave room for uncertainty
            confidence = min(95.0, 50.0 + (score_diff * 10.0) + (invoice_total_score * 5.0))
            # Boost confidence if we have both keywords and fields
            if invoice_keyword_score > 0 and invoice_field_score > 0:
                confidence = min(95.0, confidence + 10.0)
                reasons.append("Strong invoice indicators: both keywords and fields present")
        elif delivery_total_score > invoice_total_score:
            doc_type = "delivery_note"
            score_diff = delivery_total_score - invoice_total_score
            confidence = min(95.0, 50.0 + (score_diff * 10.0) + (delivery_total_score * 5.0))
            # Boost confidence if we have both keywords and fields
            if delivery_keyword_score > 0 and delivery_field_score > 0:
                confidence = min(95.0, confidence + 10.0)
                reasons.append("Strong delivery note indicators: both keywords and fields present")
        else:
            # Equal scores - ambiguous
            doc_type = "unknown"
            confidence = max(30.0, min(60.0, (invoice_total_score + delivery_total_score) * 5.0))
            reasons.append("Ambiguous classification: equal scores for invoice and delivery note")
        
        # Page coverage boost (if multi-page)
        if pages and len(pages) > 1:
            # Check if indicators appear on multiple pages
            invoice_pages = sum(1 for page in pages if any(kw in page.upper() for kw in self.INVOICE_KEYWORDS))
            delivery_pages = sum(1 for page in pages if any(kw in page.upper() for kw in self.DELIVERY_NOTE_KEYWORDS))
            
            if doc_type == "invoice" and invoice_pages > 1:
                confidence = min(95.0, confidence + 5.0)
                reasons.append(f"Invoice keywords found on {invoice_pages} pages")
            elif doc_type == "delivery_note" and delivery_pages > 1:
                confidence = min(95.0, confidence + 5.0)
                reasons.append(f"Delivery note keywords found on {delivery_pages} pages")
        
        # Ensure minimum confidence for non-unknown types
        if doc_type != "unknown" and confidence < 50.0:
            confidence = 50.0
            reasons.append("Minimum confidence threshold applied")
        
        return DocumentClassification(
            doc_type=doc_type,
            confidence=confidence,
            reasons=reasons if reasons else ["Classification based on text analysis"]
        )


# Global instance
_classifier_instance: Optional[DocumentTypeClassifier] = None

def classify_document_type(text: str, pages: Optional[List[str]] = None) -> DocumentClassification:
    """
    Classify document type (convenience function).
    
    Args:
        text: Document text content
        pages: Optional list of per-page text
        
    Returns:
        DocumentClassification result
    """
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = DocumentTypeClassifier()
    
    return _classifier_instance.classify(text, pages)

