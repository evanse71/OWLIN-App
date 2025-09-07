#!/usr/bin/env python3
"""
Language Detection Module

Detects English, Welsh, and bilingual documents using lexicon scoring
"""

import re
import logging
from typing import Literal, Dict, List, Tuple
from collections import Counter

from .config import get_ocr_config

logger = logging.getLogger(__name__)

# Welsh keywords for business documents
WELSH_KEYWORDS = {
    'invoice': ['anfoneb', 'anfonebau'],
    'total': ['cyfanswm', 'cyfanswm y cyfan', 'cyfanswm i dalu'],
    'vat': ['taw', 'treth ar werth'],
    'date': ['dyddiad', 'dyddiad anfoneb'],
    'delivery': ['cyflenwi', 'cyflenwad', 'danfon'],
    'receipt': ['derbyn', 'derbynneb'],
    'notes': ['nodiadau', 'nodyn'],
    'number': ['rhif', 'rhif anfoneb'],
    'terms': ['telerau', 'amodau'],
    'address': ['cyfeiriad', 'lleoliad'],
    'amount': ['swm', 'symiau'],
    'payment': ['taliad', 'talu'],
    'due': ['i dalu', 'ddyledus'],
    'subtotal': ['is-gyfanswm', 'cyfanswm rhag'],
    'tax': ['treth', 'trethi'],
    'company': ['cwmni', 'busnes'],
    'limited': ['cyfyngedig', 'cyf'],
    'ltd': ['cyf', 'cyfyngedig'],
    'plc': ['ccc', 'cwmni cyhoeddus cyfyngedig']
}

# English keywords for business documents
ENGLISH_KEYWORDS = {
    'invoice': ['invoice', 'bill', 'billing'],
    'total': ['total', 'amount', 'sum', 'grand total'],
    'vat': ['vat', 'value added tax', 'tax'],
    'date': ['date', 'dated', 'invoice date'],
    'delivery': ['delivery', 'delivered', 'shipping'],
    'receipt': ['receipt', 'payment receipt'],
    'notes': ['notes', 'note', 'remarks'],
    'number': ['number', 'invoice number', 'ref'],
    'terms': ['terms', 'conditions', 'payment terms'],
    'address': ['address', 'location'],
    'amount': ['amount', 'sum', 'total'],
    'payment': ['payment', 'pay'],
    'due': ['due', 'payable', 'owing'],
    'subtotal': ['subtotal', 'sub total'],
    'tax': ['tax', 'taxes'],
    'company': ['company', 'business', 'firm'],
    'limited': ['limited', 'ltd'],
    'ltd': ['ltd', 'limited'],
    'plc': ['plc', 'public limited company']
}

def detect_lang(text: str) -> Literal["en", "cy", "bi"]:
    """
    Detect language using lightweight lexicon scoring
    
    Args:
        text: Document text to analyze
        
    Returns:
        "en" for English, "cy" for Welsh, "bi" for bilingual
    """
    if not text or len(text.strip()) < 10:
        return "en"  # Default to English for very short text
    
    # Normalize text
    text_lower = text.lower()
    words = re.findall(r'\b\w+\b', text_lower)
    
    config = get_ocr_config()
    min_tokens = config.get_lang_detect("min_tokens", 6)
    bilingual_ratio = config.get_lang_detect("bilingual_overlap_ratio", 0.25)
    
    if len(words) < min_tokens:
        return "en"  # Default for very short text
    
    # Score each language
    welsh_score = _score_language(text_lower, WELSH_KEYWORDS)
    english_score = _score_language(text_lower, ENGLISH_KEYWORDS)
    
    logger.debug(f"Language scores - Welsh: {welsh_score:.3f}, English: {english_score:.3f}")
    
    # Determine thresholds (adjust based on text length)
    base_threshold = 0.1
    length_factor = min(len(words) / 50, 2.0)  # Cap at 2x for very long documents
    threshold = base_threshold * length_factor
    
    # Check for explicit bilingual indicators
    bilingual_indicators = ['/', '|', 'and', 'ac', 'or', 'neu']
    has_bilingual_format = any(indicator in text_lower for indicator in bilingual_indicators)
    
    # Check for bilingual
    if welsh_score > threshold and english_score > threshold:
        # Calculate overlap ratio
        welsh_tokens = _get_matched_tokens(text_lower, WELSH_KEYWORDS)
        english_tokens = _get_matched_tokens(text_lower, ENGLISH_KEYWORDS)
        
        if welsh_tokens and english_tokens:
            overlap = len(set(welsh_tokens) & set(english_tokens))
            total_unique = len(set(welsh_tokens) | set(english_tokens))
            
            if total_unique > 0:
                overlap_ratio = overlap / total_unique
                if overlap_ratio >= bilingual_ratio or has_bilingual_format:
                    logger.info(f"Detected bilingual document (overlap: {overlap_ratio:.3f}, format: {has_bilingual_format})")
                    return "bi"
    
    # Return the language with higher score
    if welsh_score > english_score and welsh_score > threshold:
        logger.info(f"Detected Welsh document (score: {welsh_score:.3f})")
        return "cy"
    elif english_score > threshold:
        logger.info(f"Detected English document (score: {english_score:.3f})")
        return "en"
    else:
        logger.info(f"Defaulting to English (scores below threshold)")
        return "en"

def _score_language(text: str, keywords: Dict[str, List[str]]) -> float:
    """Score text against a language's keyword set"""
    score = 0.0
    total_keywords = 0
    
    for category, words in keywords.items():
        category_score = 0
        for word in words:
            if word in text:
                category_score += 1
        
        if words:  # Avoid division by zero
            category_score = category_score / len(words)
            score += category_score
            total_keywords += 1
    
    return score / total_keywords if total_keywords > 0 else 0.0

def _get_matched_tokens(text: str, keywords: Dict[str, List[str]]) -> List[str]:
    """Get list of matched tokens from text"""
    matched = []
    for category, words in keywords.items():
        for word in words:
            if word in text:
                matched.append(word)
    return matched

def get_bilingual_field_mapping() -> Dict[str, Dict[str, str]]:
    """Get bilingual field mappings for extraction"""
    return {
        'invoice_number': {
            'en': ['invoice number', 'invoice no', 'bill number', 'ref', 'reference'],
            'cy': ['rhif anfoneb', 'rhif', 'cyfeirnod']
        },
        'total': {
            'en': ['total', 'total amount', 'amount due', 'grand total', 'sum'],
            'cy': ['cyfanswm', 'cyfanswm y cyfan', 'cyfanswm i dalu', 'swm']
        },
        'vat': {
            'en': ['vat', 'value added tax', 'tax'],
            'cy': ['taw', 'treth ar werth', 'treth']
        },
        'date': {
            'en': ['date', 'invoice date', 'dated'],
            'cy': ['dyddiad', 'dyddiad anfoneb']
        },
        'supplier': {
            'en': ['from', 'supplier', 'company', 'business'],
            'cy': ['oddi wrth', 'cyflenwr', 'cwmni', 'busnes']
        }
    }

def get_language_specific_patterns(lang: str) -> Dict[str, str]:
    """Get language-specific regex patterns"""
    if lang == "cy":
        return {
            'date': r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',  # Same as English for now
            'currency': r'[£€$](\d+[,\d]*\.?\d*)',
            'vat_rate': r'(TAW|Taw|taw)\s*(\d+\.?\d*)%?',
            'total': r'(Cyfanswm|cyfanswm)\s*[£€$]?(\d+[,\d]*\.?\d*)'
        }
    else:  # English or default
        return {
            'date': r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',
            'currency': r'[£€$](\d+[,\d]*\.?\d*)',
            'vat_rate': r'(VAT|Vat|vat)\s*(\d+\.?\d*)%?',
            'total': r'(Total|total)\s*[£€$]?(\d+[,\d]*\.?\d*)'
        } 