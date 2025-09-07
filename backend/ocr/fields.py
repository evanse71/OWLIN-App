#!/usr/bin/env python3
"""
Field Extraction Module

Extracts structured data fields from OCR results
"""

import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def extract_vat_summary(words: List[Dict[str, Any]], segments: List[Dict[str, Any]], lang: str = "en") -> Dict[str, Any]:
    """
    Extract VAT summary information from document
    
    Args:
        words: List of word objects with text and position
        segments: List of text segments
        lang: Language code ('en' or 'cy')
        
    Returns:
        Dictionary with VAT summary data
    """
    vat_summary = {
        'rates': [],
        'subtotal': None,
        'vat_total': None,
        'total': None,
        'confidence': 0.0
    }
    
    # Language-specific VAT patterns
    vat_patterns = {
        'en': {
            'vat_rate': r'(?:VAT|Tax)\s*(\d+(?:\.\d+)?)\s*%',
            'subtotal': r'(?:Sub\s*)?Total\s*(?:[£€$])?(\d+(?:,\d+)*(?:\.\d{2})?)',
            'vat_total': r'(?:VAT|Tax)\s*(?:[£€$])?(\d+(?:,\d+)*(?:\.\d{2})?)',
            'total': r'(?:Grand\s*)?Total\s*(?:[£€$])?(\d+(?:,\d+)*(?:\.\d{2})?)'
        },
        'cy': {
            'vat_rate': r'(?:TAW|Treth)\s*(\d+(?:\.\d+)?)\s*%',
            'subtotal': r'(?:Is\s*)?Gyfanswm\s*(?:[£€$])?(\d+(?:,\d+)*(?:\.\d{2})?)',
            'vat_total': r'(?:TAW|Treth)\s*(?:[£€$])?(\d+(?:,\d+)*(?:\.\d{2})?)',
            'total': r'(?:Cyfanswm)\s*(?:[£€$])?(\d+(?:,\d+)*(?:\.\d{2})?)'
        }
    }
    
    patterns = vat_patterns.get(lang, vat_patterns['en'])
    
    # Extract text from words
    text = ' '.join([word.get('text', '') for word in words])
    
    # Find VAT rates - look for patterns like "VAT 20%" or "20%"
    vat_rate_pattern = r'(\d+(?:\.\d+)?)\s*%'
    vat_rate_matches = re.finditer(vat_rate_pattern, text)
    for match in vat_rate_matches:
        rate = float(match.group(1))
        vat_summary['rates'].append({
            'rate': rate,
            'position': match.span(),
            'confidence': 0.9
        })
    
    # Simple approach: look for specific patterns in order
    if lang == 'en':
        # Look for "Subtotal £X.XX"
        subtotal_match = re.search(r'Subtotal\s+[£€$]?(\d+(?:,\d+)*(?:\.\d{2})?)', text, re.IGNORECASE)
        if subtotal_match:
            amount_str = subtotal_match.group(1).replace(',', '')
            vat_summary['subtotal'] = {
                'amount': float(amount_str),
                'position': subtotal_match.span(),
                'confidence': 0.8
            }
        
        # Look for "VAT £X.XX"
        vat_total_match = re.search(r'VAT\s+[£€$]?(\d+(?:,\d+)*(?:\.\d{2})?)', text, re.IGNORECASE)
        if vat_total_match:
            amount_str = vat_total_match.group(1).replace(',', '')
            vat_summary['vat_total'] = {
                'amount': float(amount_str),
                'position': vat_total_match.span(),
                'confidence': 0.8
            }
        
        # Look for "Total £X.XX" (but not "Subtotal")
        total_match = re.search(r'(?<!Sub)Total\s+[£€$]?(\d+(?:,\d+)*(?:\.\d{2})?)', text, re.IGNORECASE)
        if total_match:
            amount_str = total_match.group(1).replace(',', '')
            vat_summary['total'] = {
                'amount': float(amount_str),
                'position': total_match.span(),
                'confidence': 0.8
            }
    else:
        # Welsh patterns
        subtotal_match = re.search(r'Is-gyfanswm\s+[£€$]?(\d+(?:,\d+)*(?:\.\d{2})?)', text, re.IGNORECASE)
        if subtotal_match:
            amount_str = subtotal_match.group(1).replace(',', '')
            vat_summary['subtotal'] = {
                'amount': float(amount_str),
                'position': subtotal_match.span(),
                'confidence': 0.8
            }
        
        vat_total_match = re.search(r'TAW\s+[£€$]?(\d+(?:,\d+)*(?:\.\d{2})?)', text, re.IGNORECASE)
        if vat_total_match:
            amount_str = vat_total_match.group(1).replace(',', '')
            vat_summary['vat_total'] = {
                'amount': float(amount_str),
                'position': vat_total_match.span(),
                'confidence': 0.8
            }
        
        total_match = re.search(r'Cyfanswm\s+[£€$]?(\d+(?:,\d+)*(?:\.\d{2})?)', text, re.IGNORECASE)
        if total_match:
            amount_str = total_match.group(1).replace(',', '')
            vat_summary['total'] = {
                'amount': float(amount_str),
                'position': total_match.span(),
                'confidence': 0.8
            }
    
    # Calculate confidence based on found fields
    found_fields = sum([
        1 if vat_summary['rates'] else 0,
        1 if vat_summary['subtotal'] else 0,
        1 if vat_summary['vat_total'] else 0,
        1 if vat_summary['total'] else 0
    ])
    vat_summary['confidence'] = found_fields / 4.0
    
    return vat_summary 