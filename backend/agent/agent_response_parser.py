"""
Agent Response Parser Module

Parses raw agent responses into structured output for the frontend.
This module extracts actions, confidence scores, and other structured data from agent responses.
"""

import logging
import re
import json
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

def parse_agent_response(raw_response: str) -> Dict[str, Any]:
    """
    Parse a raw agent response into structured output.
    
    Args:
        raw_response: Raw markdown response from the agent
        
    Returns:
        Dictionary with structured fields:
        - markdown: Original agent response
        - actions: List of suggested actions
        - confidence: Estimated confidence score (0-100)
        - entities: Extracted entities (suppliers, amounts, etc.)
        - urgency: Urgency level (low, medium, high)
    """
    try:
        logger.debug(f"🔍 Parsing agent response ({len(raw_response)} chars)")
        
        # Initialize result structure
        result = {
            "markdown": raw_response,
            "actions": [],
            "confidence": 75,  # Default confidence
            "entities": {},
            "urgency": "medium"
        }
        
        # Extract actions
        result["actions"] = _extract_actions(raw_response)
        
        # Extract confidence score
        result["confidence"] = _extract_confidence(raw_response)
        
        # Extract entities
        result["entities"] = _extract_entities(raw_response)
        
        # Determine urgency
        result["urgency"] = _determine_urgency(raw_response)
        
        # Extract structured data if present
        structured_data = _extract_structured_data(raw_response)
        if structured_data:
            result.update(structured_data)
        
        logger.debug(f"✅ Parsed response with {len(result['actions'])} actions, confidence: {result['confidence']}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error parsing agent response: {str(e)}")
        return {
            "markdown": raw_response,
            "actions": [],
            "confidence": 50,
            "entities": {},
            "urgency": "medium",
            "error": "Failed to parse response"
        }

def _extract_actions(response: str) -> List[Dict[str, Any]]:
    """
    Extract suggested actions from the response.
    
    Args:
        response: Raw agent response
        
    Returns:
        List of action dictionaries
    """
    actions = []
    
    # Common action patterns
    action_patterns = [
        (r"suggest_credit", "credit_suggestion"),
        (r"generate.*email", "email_generation"),
        (r"escalate", "escalation"),
        (r"flag.*issue", "flag_issue"),
        (r"contact.*supplier", "contact_supplier"),
        (r"review.*invoice", "review_invoice"),
        (r"approve.*payment", "approve_payment"),
        (r"reject.*invoice", "reject_invoice"),
        (r"request.*credit", "request_credit"),
        (r"investigate.*discrepancy", "investigate_discrepancy")
    ]
    
    response_lower = response.lower()
    
    for pattern, action_type in action_patterns:
        if re.search(pattern, response_lower):
            actions.append({
                "type": action_type,
                "description": f"Suggested: {action_type.replace('_', ' ').title()}",
                "priority": "medium"
            })
    
    # Extract specific action mentions
    action_mentions = [
        "email the supplier",
        "contact the supplier",
        "request a credit",
        "flag for review",
        "escalate the issue",
        "approve the invoice",
        "reject the invoice",
        "investigate further"
    ]
    
    for mention in action_mentions:
        if mention in response_lower:
            actions.append({
                "type": "custom_action",
                "description": mention.title(),
                "priority": "medium"
            })
    
    return actions

def _extract_confidence(response: str) -> int:
    """
    Extract confidence score from the response.
    
    Args:
        response: Raw agent response
        
    Returns:
        Confidence score (0-100)
    """
    # Look for explicit confidence mentions
    confidence_patterns = [
        r"confidence.*?(\d+)",
        r"(\d+)%.*confidence",
        r"(\d+)%.*sure",
        r"(\d+)%.*certain"
    ]
    
    for pattern in confidence_patterns:
        match = re.search(pattern, response.lower())
        if match:
            confidence = int(match.group(1))
            return min(max(confidence, 0), 100)
    
    # Estimate confidence based on response characteristics
    confidence = 75  # Base confidence
    
    # Increase confidence for specific, actionable responses
    if any(word in response.lower() for word in ["specific", "exact", "precise", "definite"]):
        confidence += 10
    
    # Decrease confidence for uncertain language
    if any(word in response.lower() for word in ["maybe", "perhaps", "possibly", "might", "could"]):
        confidence -= 15
    
    # Increase confidence for detailed responses
    if len(response.split()) > 50:
        confidence += 5
    
    # Decrease confidence for very short responses
    if len(response.split()) < 10:
        confidence -= 10
    
    return min(max(confidence, 0), 100)

def _extract_entities(response: str) -> Dict[str, Any]:
    """
    Extract entities from the response.
    
    Args:
        response: Raw agent response
        
    Returns:
        Dictionary of extracted entities
    """
    entities = {
        "suppliers": [],
        "amounts": [],
        "dates": [],
        "invoice_numbers": [],
        "items": []
    }
    
    # Extract supplier names (common patterns)
    supplier_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Ltd|Limited|Corp|Corporation|Inc|Company|Co)\b'
    suppliers = re.findall(supplier_pattern, response)
    entities["suppliers"] = list(set(suppliers))
    
    # Extract amounts (£XX.XX or $XX.XX)
    amount_pattern = r'[£$]\d+(?:\.\d{2})?'
    amounts = re.findall(amount_pattern, response)
    entities["amounts"] = amounts
    
    # Extract dates
    date_pattern = r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'
    dates = re.findall(date_pattern, response)
    entities["dates"] = dates
    
    # Extract invoice numbers
    invoice_pattern = r'INV-\d+'
    invoice_numbers = re.findall(invoice_pattern, response)
    entities["invoice_numbers"] = invoice_numbers
    
    # Extract item names (common food items)
    food_items = [
        "tomatoes", "potatoes", "onions", "carrots", "lettuce", "cucumber",
        "beef", "chicken", "pork", "fish", "salmon", "tuna",
        "bread", "milk", "cheese", "eggs", "butter", "oil",
        "rice", "pasta", "sauce", "spices", "herbs"
    ]
    
    found_items = []
    for item in food_items:
        if item in response.lower():
            found_items.append(item)
    
    entities["items"] = found_items
    
    return entities

def _determine_urgency(response: str) -> str:
    """
    Determine urgency level from the response.
    
    Args:
        response: Raw agent response
        
    Returns:
        Urgency level: "low", "medium", "high"
    """
    response_lower = response.lower()
    
    # High urgency indicators
    high_urgency_words = [
        "urgent", "immediate", "critical", "emergency", "asap", "right away",
        "stop payment", "reject", "escalate", "serious", "major"
    ]
    
    # Low urgency indicators
    low_urgency_words = [
        "routine", "normal", "standard", "regular", "usual", "minor",
        "informational", "for reference", "no action needed"
    ]
    
    if any(word in response_lower for word in high_urgency_words):
        return "high"
    elif any(word in response_lower for word in low_urgency_words):
        return "low"
    else:
        return "medium"

def _extract_structured_data(response: str) -> Optional[Dict[str, Any]]:
    """
    Extract structured data if present in the response.
    
    Args:
        response: Raw agent response
        
    Returns:
        Dictionary of structured data or None
    """
    # Look for JSON-like structures
    json_pattern = r'\{[^{}]*\}'
    json_matches = re.findall(json_pattern, response)
    
    for match in json_matches:
        try:
            data = json.loads(match)
            return data
        except json.JSONDecodeError:
            continue
    
    # Look for key-value pairs
    kv_pattern = r'(\w+):\s*([^,\n]+)'
    kv_matches = re.findall(kv_pattern, response)
    
    if kv_matches:
        structured_data = {}
        for key, value in kv_matches:
            structured_data[key.strip()] = value.strip()
        return structured_data
    
    return None

def parse_credit_suggestion(response: str) -> Dict[str, Any]:
    """
    Parse a credit suggestion response.
    
    Args:
        response: Raw agent response
        
    Returns:
        Structured credit suggestion data
    """
    credit_data = {
        "amount": None,
        "reason": "",
        "supplier": "",
        "invoice_number": "",
        "items": []
    }
    
    # Extract credit amount
    amount_pattern = r'[£$](\d+(?:\.\d{2})?)'
    amount_match = re.search(amount_pattern, response)
    if amount_match:
        credit_data["amount"] = float(amount_match.group(1))
    
    # Extract reason
    reason_patterns = [
        r'reason.*?([^.]+)',
        r'because.*?([^.]+)',
        r'due to.*?([^.]+)'
    ]
    
    for pattern in reason_patterns:
        reason_match = re.search(pattern, response, re.IGNORECASE)
        if reason_match:
            credit_data["reason"] = reason_match.group(1).strip()
            break
    
    # Extract supplier name
    supplier_pattern = r'from\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
    supplier_match = re.search(supplier_pattern, response)
    if supplier_match:
        credit_data["supplier"] = supplier_match.group(1)
    
    return credit_data

def parse_email_suggestion(response: str) -> Dict[str, Any]:
    """
    Parse an email generation response.
    
    Args:
        response: Raw agent response
        
    Returns:
        Structured email data
    """
    email_data = {
        "subject": "",
        "recipient": "",
        "content": "",
        "tone": "professional",
        "urgency": "medium"
    }
    
    # Extract subject line
    subject_pattern = r'subject.*?([^\n]+)'
    subject_match = re.search(subject_pattern, response, re.IGNORECASE)
    if subject_match:
        email_data["subject"] = subject_match.group(1).strip()
    
    # Extract recipient
    recipient_pattern = r'to\s+([^\n]+)'
    recipient_match = re.search(recipient_pattern, response, re.IGNORECASE)
    if recipient_match:
        email_data["recipient"] = recipient_match.group(1).strip()
    
    # Determine tone
    if any(word in response.lower() for word in ["urgent", "immediate", "critical"]):
        email_data["tone"] = "urgent"
    elif any(word in response.lower() for word in ["friendly", "courteous", "polite"]):
        email_data["tone"] = "friendly"
    
    return email_data 