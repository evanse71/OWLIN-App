#!/usr/bin/env python3
"""
LLM Assist Functions

LLM-powered assistance for OCR processing (disabled by default)
"""

import json
import logging
import sys
import os
from typing import Optional, Dict, Any, List

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from llm.runtime import get_llm_runtime, LlmUnavailable, LlmTimeout

logger = logging.getLogger(__name__)

def llm_guess_doctype(text: str) -> Optional[Dict[str, str]]:
    """
    Use LLM to guess document type
    
    Args:
        text: Document text
        
    Returns:
        Dict with 'label' and 'why' keys, or None if LLM unavailable
    """
    try:
        runtime = get_llm_runtime()
        if not runtime.is_available():
            return None
        
        # Create prompt for document type classification
        prompt = f"""Analyze this document text and classify it as one of: invoice, delivery_note, receipt, utility, other.

Document text:
{text[:1000]}  # Limit to first 1000 chars

Respond with JSON only:
{{"label": "invoice|delivery_note|receipt|utility|other", "why": "brief explanation"}}

JSON:"""
        
        # Generate response
        response = runtime.generate(prompt, max_tokens=128, timeout_ms=800)
        
        # Parse JSON response
        try:
            # Clean the response (remove markdown if present)
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            
            result = json.loads(cleaned_response.strip())
            
            # Validate response format
            if 'label' not in result or 'why' not in result:
                logger.warning("⚠️ LLM response missing required fields")
                return None
            
            # Validate label
            valid_labels = ['invoice', 'delivery_note', 'receipt', 'utility', 'other']
            if result['label'] not in valid_labels:
                logger.warning(f"⚠️ LLM returned invalid label: {result['label']}")
                return None
            
            logger.info(f"🤖 LLM classified as: {result['label']} - {result['why']}")
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ Failed to parse LLM response as JSON: {e}")
            return None
            
    except (LlmUnavailable, LlmTimeout) as e:
        logger.debug(f"LLM unavailable for doctype guess: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ LLM doctype guess failed: {e}")
        return None

def llm_normalize_supplier(text: str) -> Optional[Dict[str, str]]:
    """
    Use LLM to normalize supplier name
    
    Args:
        text: Document text containing supplier information
        
    Returns:
        Dict with 'name' and 'why' keys, or None if LLM unavailable
    """
    try:
        runtime = get_llm_runtime()
        if not runtime.is_available():
            return None
        
        # Create prompt for supplier normalization
        prompt = f"""Extract and normalize the supplier/company name from this document text.

Document text:
{text[:800]}  # Limit to first 800 chars

Respond with JSON only:
{{"name": "Normalized Supplier Name", "why": "brief explanation"}}

JSON:"""
        
        # Generate response
        response = runtime.generate(prompt, max_tokens=128, timeout_ms=800)
        
        # Parse JSON response
        try:
            # Clean the response
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            
            result = json.loads(cleaned_response.strip())
            
            # Validate response format
            if 'name' not in result or 'why' not in result:
                logger.warning("⚠️ LLM response missing required fields")
                return None
            
            # Basic validation
            if not result['name'] or len(result['name']) > 200:
                logger.warning("⚠️ LLM returned invalid supplier name")
                return None
            
            logger.info(f"🤖 LLM normalized supplier: {result['name']} - {result['why']}")
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ Failed to parse LLM response as JSON: {e}")
            return None
            
    except (LlmUnavailable, LlmTimeout) as e:
        logger.debug(f"LLM unavailable for supplier normalization: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ LLM supplier normalization failed: {e}")
        return None

def llm_explain_reasons(reasons: List[str]) -> Optional[str]:
    """
    Use LLM to explain validation/policy reasons in user-friendly terms
    
    Args:
        reasons: List of reason codes
        
    Returns:
        Human-readable explanation, or None if LLM unavailable
    """
    try:
        runtime = get_llm_runtime()
        if not runtime.is_available():
            return None
        
        # Create prompt for reason explanation
        prompt = f"""Explain these document processing reasons in simple, user-friendly terms:

Reasons: {', '.join(reasons)}

Provide a brief, clear explanation that a business user would understand. Focus on what the issue means and what action might be needed.

Explanation:"""
        
        # Generate response
        response = runtime.generate(prompt, max_tokens=200, timeout_ms=800)
        
        # Clean and return response
        explanation = response.strip()
        if explanation:
            logger.info(f"🤖 LLM explained reasons: {explanation[:100]}...")
            return explanation
        
        return None
        
    except (LlmUnavailable, LlmTimeout) as e:
        logger.debug(f"LLM unavailable for reason explanation: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ LLM reason explanation failed: {e}")
        return None

def check_hard_signals(text: str, llm_label: str) -> bool:
    """
    Check if LLM suggestion agrees with hard signals in the text
    
    Args:
        text: Document text
        llm_label: LLM-suggested document type
        
    Returns:
        True if LLM suggestion agrees with hard signals
    """
    text_lower = text.lower()
    
    # Hard signals for different document types
    hard_signals = {
        'invoice': [
            'invoice', 'bill', 'total amount', 'amount due', 'payment terms',
            'vat', 'tax', 'subtotal', 'balance due'
        ],
        'receipt': [
            'receipt', 'change', 'cash', 'card', 'payment', 'total',
            'thank you', 'transaction'
        ],
        'delivery_note': [
            'delivery', 'delivered', 'shipment', 'order', 'packing',
            'quantity', 'qty', 'units'
        ],
        'utility': [
            'utility', 'gas', 'electric', 'water', 'bill', 'usage',
            'meter', 'consumption', 'account number'
        ]
    }
    
    # Check if LLM label has hard signals
    if llm_label in hard_signals:
        signals = hard_signals[llm_label]
        signal_count = sum(1 for signal in signals if signal in text_lower)
        
        # Require at least 2 hard signals for agreement
        return signal_count >= 2
    
    # For 'other' type, we're more lenient
    if llm_label == 'other':
        # Check if there are NO strong signals for other types
        all_signals = []
        for signals in hard_signals.values():
            all_signals.extend(signals)
        
        signal_count = sum(1 for signal in all_signals if signal in text_lower)
        return signal_count < 2
    
    return False 