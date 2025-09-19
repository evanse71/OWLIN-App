"""
Document Type Classifier for OWLIN

This module implements a rule-based document classifier that distinguishes between
invoices, delivery notes, receipts, credit notes, utility bills, and purchase orders.
It uses keyword matching, layout analysis, and pattern recognition to classify
documents with confidence scores.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
import re
import json
from dataclasses import dataclass
from rapidfuzz import fuzz


@dataclass
class ClassificationResult:
    """Result of document classification"""
    doc_type: str
    confidence: float
    keywords_found: List[str]
    layout_features: Dict[str, Any]
    text_patterns: List[str]
    reasoning: str


class DocumentClassifier:
    """
    Rule-based document classifier with confidence scoring.
    
    Uses multiple strategies:
    1. Keyword-based classification
    2. Layout pattern recognition
    3. Text structure analysis
    4. Amount/quantity pattern matching
    """
    
    def __init__(self):
        self.classification_rules = self._initialize_rules()
        self.keyword_patterns = self._initialize_keyword_patterns()
        self.layout_patterns = self._initialize_layout_patterns()
    
    def classify_document(self, text: str, layout_info: Optional[Dict[str, Any]] = None) -> ClassificationResult:
        """
        Classify a document based on its text content and layout.
        
        Args:
            text: Full text content of the document
            layout_info: Optional layout information (tables, sections, etc.)
            
        Returns:
            ClassificationResult with document type and confidence
        """
        text_lower = text.lower()
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Calculate scores for each document type
        scores = {}
        all_keywords = []
        all_patterns = []
        layout_features = layout_info or {}
        
        for doc_type, rules in self.classification_rules.items():
            score, keywords, patterns = self._calculate_type_score(
                text_lower, lines, rules, layout_features
            )
            scores[doc_type] = score
            all_keywords.extend(keywords)
            all_patterns.extend(patterns)
        
        # Find the best classification
        best_type = max(scores.items(), key=lambda x: x[1])
        doc_type, confidence = best_type
        
        # Generate reasoning
        reasoning = self._generate_reasoning(doc_type, scores, all_keywords)
        
        return ClassificationResult(
            doc_type=doc_type,
            confidence=confidence,
            keywords_found=list(set(all_keywords)),
            layout_features=layout_features,
            text_patterns=list(set(all_patterns)),
            reasoning=reasoning
        )
    
    def _initialize_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize classification rules for each document type"""
        return {
            'invoice': {
                'keywords': {
                    'invoice': 0.3,
                    'bill': 0.2,
                    'amount due': 0.4,
                    'total': 0.2,
                    'vat': 0.3,
                    'net': 0.2,
                    'gross': 0.2,
                    'payment terms': 0.3,
                    'due date': 0.3,
                    'invoice number': 0.4,
                    'invoice date': 0.4,
                    'subtotal': 0.2,
                    'tax': 0.2
                },
                'patterns': [
                    r'invoice\s*#?\s*:?\s*([a-z0-9\-/]+)',
                    r'invoice\s+date\s*:?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
                    r'amount\s+due\s*:?\s*[£$€]?\s*(\d+[.,]\d{2})',
                    r'payment\s+terms\s*:?\s*(\d+)\s+days?',
                    r'vat\s+rate\s*:?\s*(\d+[.,]?\d*)\s*%'
                ],
                'layout_indicators': {
                    'has_line_items': 0.3,
                    'has_totals_section': 0.2,
                    'has_payment_terms': 0.2,
                    'has_vat_breakdown': 0.2
                },
                'negative_keywords': ['delivery', 'receipt', 'credit note', 'utility']
            },
            
            'delivery_note': {
                'keywords': {
                    'delivery note': 0.5,
                    'delivery': 0.3,
                    'delivered': 0.2,
                    'received': 0.2,
                    'quantity': 0.3,
                    'delivered by': 0.3,
                    'delivery date': 0.4,
                    'signature': 0.2,
                    'goods received': 0.3,
                    'packing list': 0.2
                },
                'patterns': [
                    r'delivery\s+note\s*#?\s*:?\s*([a-z0-9\-/]+)',
                    r'delivery\s+date\s*:?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
                    r'delivered\s+by\s*:?\s*([a-z\s]+)',
                    r'quantity\s+delivered\s*:?\s*(\d+)',
                    r'signature\s*:?\s*([a-z\s]+)'
                ],
                'layout_indicators': {
                    'has_quantity_column': 0.3,
                    'has_signature_section': 0.2,
                    'has_delivery_info': 0.3,
                    'no_payment_terms': 0.2
                },
                'negative_keywords': ['invoice', 'amount due', 'payment', 'vat']
            },
            
            'receipt': {
                'keywords': {
                    'receipt': 0.4,
                    'thank you': 0.2,
                    'cash': 0.2,
                    'card': 0.2,
                    'change': 0.2,
                    'tendered': 0.2,
                    'store': 0.2,
                    'retail': 0.2,
                    'pos': 0.3,
                    'transaction': 0.2
                },
                'patterns': [
                    r'receipt\s*#?\s*:?\s*([a-z0-9\-/]+)',
                    r'transaction\s+id\s*:?\s*([a-z0-9\-/]+)',
                    r'cash\s+tendered\s*:?\s*[£$€]?\s*(\d+[.,]\d{2})',
                    r'change\s+given\s*:?\s*[£$€]?\s*(\d+[.,]\d{2})',
                    r'card\s+ending\s+in\s+(\d{4})'
                ],
                'layout_indicators': {
                    'has_transaction_id': 0.3,
                    'has_payment_method': 0.2,
                    'has_change_info': 0.2,
                    'compact_layout': 0.2
                },
                'negative_keywords': ['invoice', 'delivery', 'credit note']
            },
            
            'credit_note': {
                'keywords': {
                    'credit note': 0.5,
                    'credit': 0.3,
                    'refund': 0.3,
                    'return': 0.2,
                    'adjustment': 0.2,
                    'debit': 0.2,
                    'original invoice': 0.3,
                    'credit amount': 0.3,
                    'reason for credit': 0.3
                },
                'patterns': [
                    r'credit\s+note\s*#?\s*:?\s*([a-z0-9\-/]+)',
                    r'original\s+invoice\s*#?\s*:?\s*([a-z0-9\-/]+)',
                    r'credit\s+amount\s*:?\s*[£$€]?\s*(\d+[.,]\d{2})',
                    r'reason\s+for\s+credit\s*:?\s*([a-z\s]+)',
                    r'refund\s+amount\s*:?\s*[£$€]?\s*(\d+[.,]\d{2})'
                ],
                'layout_indicators': {
                    'has_original_invoice_ref': 0.3,
                    'has_credit_reason': 0.2,
                    'has_negative_amounts': 0.3,
                    'references_original': 0.2
                },
                'negative_keywords': ['invoice', 'delivery', 'receipt']
            },
            
            'utility_bill': {
                'keywords': {
                    'utility': 0.3,
                    'electricity': 0.4,
                    'gas': 0.4,
                    'water': 0.4,
                    'telephone': 0.3,
                    'internet': 0.3,
                    'broadband': 0.3,
                    'account number': 0.3,
                    'meter reading': 0.3,
                    'usage': 0.2,
                    'kwh': 0.3,
                    'cubic meters': 0.2,
                    'standing charge': 0.2
                },
                'patterns': [
                    r'account\s+number\s*:?\s*([a-z0-9\-/]+)',
                    r'meter\s+reading\s*:?\s*(\d+[.,]\d*)',
                    r'usage\s*:?\s*(\d+[.,]\d*)\s*(kwh|m3|units)',
                    r'standing\s+charge\s*:?\s*[£$€]?\s*(\d+[.,]\d{2})',
                    r'previous\s+reading\s*:?\s*(\d+[.,]\d*)'
                ],
                'layout_indicators': {
                    'has_account_number': 0.3,
                    'has_meter_readings': 0.3,
                    'has_usage_info': 0.2,
                    'has_standing_charges': 0.2
                },
                'negative_keywords': ['invoice', 'delivery', 'receipt', 'credit note']
            },
            
            'purchase_order': {
                'keywords': {
                    'purchase order': 0.5,
                    'po number': 0.4,
                    'order number': 0.3,
                    'order date': 0.3,
                    'requested by': 0.2,
                    'authorized by': 0.2,
                    'terms and conditions': 0.2,
                    'delivery address': 0.2,
                    'billing address': 0.2,
                    'order total': 0.2
                },
                'patterns': [
                    r'purchase\s+order\s*#?\s*:?\s*([a-z0-9\-/]+)',
                    r'po\s+number\s*:?\s*([a-z0-9\-/]+)',
                    r'order\s+date\s*:?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
                    r'requested\s+by\s*:?\s*([a-z\s]+)',
                    r'authorized\s+by\s*:?\s*([a-z\s]+)'
                ],
                'layout_indicators': {
                    'has_po_number': 0.3,
                    'has_authorization': 0.2,
                    'has_delivery_address': 0.2,
                    'has_terms': 0.2
                },
                'negative_keywords': ['invoice', 'delivery', 'receipt', 'credit note']
            }
        }
    
    def _initialize_keyword_patterns(self) -> Dict[str, List[str]]:
        """Initialize keyword patterns for fuzzy matching"""
        return {
            'invoice': ['invoice', 'bill', 'statement', 'account'],
            'delivery_note': ['delivery', 'dispatch', 'shipping', 'goods received'],
            'receipt': ['receipt', 'till', 'pos', 'transaction'],
            'credit_note': ['credit', 'refund', 'return', 'adjustment'],
            'utility_bill': ['utility', 'electricity', 'gas', 'water', 'telephone'],
            'purchase_order': ['purchase order', 'po', 'order', 'requisition']
        }
    
    def _initialize_layout_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize layout-based classification patterns"""
        return {
            'invoice': {
                'has_header': True,
                'has_line_items': True,
                'has_totals': True,
                'has_payment_terms': True,
                'layout_type': 'formal'
            },
            'delivery_note': {
                'has_header': True,
                'has_quantities': True,
                'has_signature': True,
                'layout_type': 'simple'
            },
            'receipt': {
                'has_header': False,
                'has_items': True,
                'has_payment_info': True,
                'layout_type': 'compact'
            }
        }
    
    def _calculate_type_score(
        self, 
        text_lower: str, 
        lines: List[str], 
        rules: Dict[str, Any], 
        layout_features: Dict[str, Any]
    ) -> Tuple[float, List[str], List[str]]:
        """Calculate classification score for a document type"""
        score = 0.0
        keywords_found = []
        patterns_found = []
        
        # Keyword scoring
        for keyword, weight in rules['keywords'].items():
            if keyword in text_lower:
                score += weight
                keywords_found.append(keyword)
        
        # Pattern matching
        for pattern in rules['patterns']:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                score += 0.1 * len(matches)
                patterns_found.append(pattern)
        
        # Layout scoring
        for feature, weight in rules['layout_indicators'].items():
            if layout_features.get(feature, False):
                score += weight
        
        # Negative keyword penalties
        for neg_keyword in rules.get('negative_keywords', []):
            if neg_keyword in text_lower:
                score -= 0.2
        
        # Normalize score to 0-1 range
        score = max(0.0, min(1.0, score))
        
        return score, keywords_found, patterns_found
    
    def _generate_reasoning(
        self, 
        doc_type: str, 
        scores: Dict[str, float], 
        keywords: List[str]
    ) -> str:
        """Generate human-readable reasoning for classification"""
        reasoning_parts = []
        
        # Primary reasoning
        reasoning_parts.append(f"Classified as {doc_type} with confidence {scores[doc_type]:.2f}")
        
        # Keyword evidence
        if keywords:
            reasoning_parts.append(f"Found keywords: {', '.join(keywords[:5])}")
        
        # Alternative classifications
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_scores) > 1:
            alt_type, alt_score = sorted_scores[1]
            reasoning_parts.append(f"Alternative: {alt_type} ({alt_score:.2f})")
        
        return ". ".join(reasoning_parts)


def classify_document_text(text: str, layout_info: Optional[Dict[str, Any]] = None) -> ClassificationResult:
    """
    Convenience function to classify document text.
    
    Args:
        text: Document text content
        layout_info: Optional layout information
        
    Returns:
        ClassificationResult
    """
    classifier = DocumentClassifier()
    return classifier.classify_document(text, layout_info)


def save_classification_result(
    db, 
    file_id: str, 
    result: ClassificationResult
) -> str:
    """
    Save classification result to database.
    
    Args:
        db: Database connection
        result: Classification result
        
    Returns:
        Classification ID
    """
    import uuid
    import json
    
    classification_id = str(uuid.uuid4())
    
    cursor = db.cursor()
    cursor.execute(
        """
        INSERT INTO document_classification (
            id, file_id, doc_type, confidence, classification_method,
            keywords_found, layout_features, text_patterns
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            classification_id,
            file_id,
            result.doc_type,
            result.confidence,
            'rule_based',
            json.dumps(result.keywords_found),
            json.dumps(result.layout_features),
            json.dumps(result.text_patterns)
        )
    )
    
    # Update the uploaded_files table with classification
    cursor.execute(
        """
        UPDATE uploaded_files 
        SET doc_type = ?, doc_type_confidence = ?
        WHERE id = ?
        """,
        (result.doc_type, result.confidence, file_id)
    )
    
    db.commit()
    return classification_id