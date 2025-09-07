#!/usr/bin/env python3
"""
Simple Document Type Classifier
Tags pages as invoice/delivery_note/other using keyword sets
"""

import re
from typing import Dict, List

# Keyword sets for document classification
INVOICE_KEYWORDS = [
    r'\b(?:invoice|bill|statement|account)\s*(?:no|number|#)\b',
    r'\b(?:total|amount|subtotal|vat|tax)\s*(?:due|payable)\b',
    r'\b(?:payment|terms|due\s*date)\b',
    r'\b(?:tax\s*invoice|vat\s*invoice)\b',
    r'\b(?:please\s*pay|payment\s*required)\b',
    r'\b(?:grand\s*total|final\s*amount)\b'
]

DELIVERY_NOTE_KEYWORDS = [
    r'\b(?:delivery\s*note|goods\s*received|received\s*note)\b',
    r'\b(?:delivered\s*by|delivery\s*date)\b',
    r'\b(?:signature\s*required|received\s*by)\b',
    r'\b(?:delivery\s*confirmation|goods\s*delivered)\b',
    r'\b(?:quantity\s*received|items\s*received)\b'
]

def classify_document_type(text: str) -> Dict[str, any]:
    """
    Classify document type based on text content
    
    Args:
        text: Document text content
        
    Returns:
        Dict with classification results
    """
    if not text:
        return {
            "type": "unknown",
            "confidence": 0,
            "keywords_found": [],
            "reason": "No text content"
        }
    
    text_lower = text.lower()
    
    # Count keyword matches
    invoice_matches = []
    delivery_matches = []
    
    for pattern in INVOICE_KEYWORDS:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        invoice_matches.extend(matches)
    
    for pattern in DELIVERY_NOTE_KEYWORDS:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        delivery_matches.extend(matches)
    
    # Calculate confidence scores
    invoice_score = len(invoice_matches)
    delivery_score = len(delivery_matches)
    
    # Determine document type
    if invoice_score > delivery_score and invoice_score >= 2:
        doc_type = "invoice"
        confidence = min(100, 50 + (invoice_score * 20))
        keywords_found = invoice_matches
        reason = f"Invoice keywords found: {invoice_score}"
    elif delivery_score > invoice_score and delivery_score >= 2:
        doc_type = "delivery_note"
        confidence = min(100, 50 + (delivery_score * 20))
        keywords_found = delivery_matches
        reason = f"Delivery note keywords found: {delivery_score}"
    elif invoice_score == delivery_score and invoice_score >= 1:
        doc_type = "mixed"
        confidence = 60
        keywords_found = invoice_matches + delivery_matches
        reason = f"Both invoice and delivery note keywords found"
    else:
        doc_type = "other"
        confidence = max(0, 30 - (len(text.split()) // 100))  # Lower confidence for longer texts
        keywords_found = []
        reason = "No clear document type indicators"
    
    return {
        "type": doc_type,
        "confidence": confidence,
        "keywords_found": keywords_found[:5],  # Limit to first 5
        "reason": reason,
        "scores": {
            "invoice": invoice_score,
            "delivery_note": delivery_score
        }
    }

def classify_pages(pages: List[Dict[str, any]]) -> List[Dict[str, any]]:
    """
    Classify multiple pages
    
    Args:
        pages: List of page dictionaries with 'text' key
        
    Returns:
        List of classification results
    """
    results = []
    for i, page in enumerate(pages):
        text = page.get("text", "")
        classification = classify_document_type(text)
        classification["page_index"] = i
        results.append(classification)
    
    return results 