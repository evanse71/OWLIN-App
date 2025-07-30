"""
Matching Explainer Module for Owlin Agent

Generates human-readable explanations for why a delivery note was (or wasn't)
automatically matched to an invoice. Helps users understand the matching logic
and guides manual override decisions.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

def explain_match_status(
    invoice_data: Dict, 
    delivery_data: Dict, 
    match_score: float, 
    threshold: float
) -> str:
    """
    Generate a human-readable explanation of match status.
    
    Args:
        invoice_data: Invoice metadata dictionary
        delivery_data: Delivery note metadata dictionary
        match_score: Match confidence score (0.0 to 1.0)
        threshold: Threshold required for automatic matching
        
    Returns:
        Human-readable explanation string
    """
    logger.info(f"🔍 Explaining match status (score: {match_score:.2f}, threshold: {threshold:.2f})")
    
    try:
        # Determine if matched or not
        is_matched = match_score >= threshold
        
        if is_matched:
            return _generate_matched_explanation(invoice_data, delivery_data, match_score, threshold)
        else:
            return _generate_unmatched_explanation(invoice_data, delivery_data, match_score, threshold)
            
    except Exception as e:
        logger.error(f"❌ Error generating match explanation: {e}")
        return "Unable to generate match explanation due to an error."

def _generate_matched_explanation(
    invoice_data: Dict, 
    delivery_data: Dict, 
    match_score: float, 
    threshold: float
) -> str:
    """
    Generate explanation for a successful match.
    
    Args:
        invoice_data: Invoice metadata
        delivery_data: Delivery note metadata
        match_score: Match confidence score
        threshold: Matching threshold
        
    Returns:
        Explanation string for successful match
    """
    # Extract key fields
    invoice_number = invoice_data.get('invoice_number', 'Unknown')
    delivery_number = delivery_data.get('delivery_note_number', 'Unknown')
    supplier_name = invoice_data.get('supplier_name', 'Unknown')
    delivery_supplier = delivery_data.get('supplier_name', 'Unknown')
    
    # Format dates
    invoice_date = _format_date(invoice_data.get('invoice_date', ''))
    delivery_date = _format_date(delivery_data.get('delivery_date', ''))
    
    # Get amounts and item counts
    invoice_amount = invoice_data.get('total_amount', 0.0)
    delivery_amount = delivery_data.get('total_amount', 0.0)
    invoice_items = invoice_data.get('total_items', 0)
    delivery_items = delivery_data.get('total_items', 0)
    
    # Build explanation
    explanation_parts = [
        f"✓ This delivery note was automatically matched to invoice {invoice_number} based on:"
    ]
    
    # Add matching criteria
    criteria = []
    
    # Supplier match
    if supplier_name.lower() == delivery_supplier.lower():
        criteria.append(f"• Same supplier ({supplier_name})")
    elif _similar_supplier_names(supplier_name, delivery_supplier):
        criteria.append(f"• Similar supplier names ({supplier_name} vs {delivery_supplier})")
    
    # Date match
    if invoice_date == delivery_date:
        criteria.append(f"• Same date ({invoice_date})")
    elif _dates_close(invoice_data.get('invoice_date', ''), delivery_data.get('delivery_date', '')):
        date_diff = _get_date_difference(invoice_data.get('invoice_date', ''), delivery_data.get('delivery_date', ''))
        criteria.append(f"• Close dates ({invoice_date} vs {delivery_date}, {date_diff} day{'s' if date_diff != 1 else ''} apart)")
    
    # Amount match
    if abs(invoice_amount - delivery_amount) <= 2.0:
        criteria.append(f"• Total values within £2.00 of each other")
    elif abs(invoice_amount - delivery_amount) <= 10.0:
        amount_diff = abs(invoice_amount - delivery_amount)
        criteria.append(f"• Total values within £{amount_diff:.2f} of each other")
    
    # Item count match
    if abs(invoice_items - delivery_items) <= 2:
        criteria.append(f"• Close item count ({invoice_items} vs {delivery_items} items)")
    elif abs(invoice_items - delivery_items) <= 5:
        item_diff = abs(invoice_items - delivery_items)
        criteria.append(f"• Similar item count ({invoice_items} vs {delivery_items} items, {item_diff} difference)")
    
    # Add any additional matching factors
    additional_factors = _get_additional_matching_factors(invoice_data, delivery_data)
    criteria.extend(additional_factors)
    
    explanation_parts.extend(criteria)
    
    # Add match score information
    explanation_parts.append(f"\nMatch score: {match_score:.2f} — above threshold ({threshold:.2f})")
    
    return "\n".join(explanation_parts)

def _generate_unmatched_explanation(
    invoice_data: Dict, 
    delivery_data: Dict, 
    match_score: float, 
    threshold: float
) -> str:
    """
    Generate explanation for an unsuccessful match.
    
    Args:
        invoice_data: Invoice metadata
        delivery_data: Delivery note metadata
        match_score: Match confidence score
        threshold: Matching threshold
        
    Returns:
        Explanation string for unsuccessful match
    """
    # Extract key fields
    invoice_number = invoice_data.get('invoice_number', 'Unknown')
    delivery_number = delivery_data.get('delivery_note_number', 'Unknown')
    supplier_name = invoice_data.get('supplier_name', 'Unknown')
    delivery_supplier = delivery_data.get('supplier_name', 'Unknown')
    
    # Format dates
    invoice_date = _format_date(invoice_data.get('invoice_date', ''))
    delivery_date = _format_date(delivery_data.get('delivery_date', ''))
    
    # Get amounts
    invoice_amount = invoice_data.get('total_amount', 0.0)
    delivery_amount = delivery_data.get('total_amount', 0.0)
    
    # Build explanation
    explanation_parts = [
        f"⚠️ This delivery note could not be automatically matched to any invoice."
    ]
    
    # Add closest match information
    explanation_parts.append(f"\nClosest match: invoice {invoice_number}")
    
    # Add matching factors
    factors = []
    
    # Supplier comparison
    if supplier_name.lower() == delivery_supplier.lower():
        factors.append("• Supplier matches")
    elif _similar_supplier_names(supplier_name, delivery_supplier):
        factors.append("• Supplier names are similar")
    else:
        factors.append(f"• Supplier differs ({supplier_name} vs {delivery_supplier})")
    
    # Date comparison
    if invoice_date == delivery_date:
        factors.append("• Date matches")
    elif _dates_close(invoice_data.get('invoice_date', ''), delivery_data.get('delivery_date', '')):
        date_diff = _get_date_difference(invoice_data.get('invoice_date', ''), delivery_data.get('delivery_date', ''))
        factors.append(f"• Date is similar ({invoice_date} vs {delivery_date}, {date_diff} day{'s' if date_diff != 1 else ''} apart)")
    else:
        factors.append(f"• Date differs ({invoice_date} vs {delivery_date})")
    
    # Amount comparison
    amount_diff = abs(invoice_amount - delivery_amount)
    if amount_diff <= 5.0:
        factors.append(f"• Total amount is close (difference: £{amount_diff:.2f})")
    else:
        factors.append(f"• Total amount differs by £{amount_diff:.2f}")
    
    # Item count comparison
    invoice_items = invoice_data.get('total_items', 0)
    delivery_items = delivery_data.get('total_items', 0)
    if invoice_items > 0 and delivery_items > 0:
        item_diff = abs(invoice_items - delivery_items)
        if item_diff <= 3:
            factors.append(f"• Item count is similar ({invoice_items} vs {delivery_items})")
        else:
            factors.append(f"• Item count differs ({invoice_items} vs {delivery_items})")
    
    explanation_parts.extend(factors)
    
    # Add match score information
    explanation_parts.append(f"\nMatch score: {match_score:.2f} — below threshold ({threshold:.2f})")
    
    # Add guidance
    explanation_parts.append("\nYou can manually confirm the match or leave unpaired.")
    
    return "\n".join(explanation_parts)

def _format_date(date_string: str) -> str:
    """
    Format a date string for display.
    
    Args:
        date_string: Date string in various formats
        
    Returns:
        Formatted date string
    """
    if not date_string:
        return "Unknown"
    
    try:
        # Try common date formats
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S']:
            try:
                date_obj = datetime.strptime(date_string, fmt)
                return date_obj.strftime('%d %B %Y')
            except ValueError:
                continue
        
        # If no format matches, return as is
        return date_string
        
    except Exception:
        return date_string

def _similar_supplier_names(name1: str, name2: str) -> bool:
    """
    Check if two supplier names are similar.
    
    Args:
        name1: First supplier name
        name2: Second supplier name
        
    Returns:
        True if names are similar
    """
    if not name1 or not name2:
        return False
    
    # Normalize names
    name1_clean = re.sub(r'[^\w\s]', '', name1.lower().strip())
    name2_clean = re.sub(r'[^\w\s]', '', name2.lower().strip())
    
    # Exact match after cleaning
    if name1_clean == name2_clean:
        return True
    
    # Check if one contains the other
    if name1_clean in name2_clean or name2_clean in name1_clean:
        return True
    
    # Check for common abbreviations
    abbreviations = {
        'ltd': 'limited',
        'co': 'company',
        'inc': 'incorporated',
        'corp': 'corporation'
    }
    
    name1_expanded = name1_clean
    name2_expanded = name2_clean
    
    for abbr, full in abbreviations.items():
        name1_expanded = name1_expanded.replace(abbr, full)
        name2_expanded = name2_expanded.replace(abbr, full)
    
    if name1_expanded == name2_expanded:
        return True
    
    return False

def _dates_close(date1: str, date2: str) -> bool:
    """
    Check if two dates are close to each other.
    
    Args:
        date1: First date string
        date2: Second date string
        
    Returns:
        True if dates are within 3 days of each other
    """
    if not date1 or not date2:
        return False
    
    try:
        # Try to parse dates
        date1_obj = None
        date2_obj = None
        
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S']:
            try:
                if not date1_obj:
                    date1_obj = datetime.strptime(date1, fmt)
                if not date2_obj:
                    date2_obj = datetime.strptime(date2, fmt)
                if date1_obj and date2_obj:
                    break
            except ValueError:
                continue
        
        if date1_obj and date2_obj:
            date_diff = abs((date1_obj - date2_obj).days)
            return date_diff <= 3
        
        return False
        
    except Exception:
        return False

def _get_date_difference(date1: str, date2: str) -> int:
    """
    Get the difference in days between two dates.
    
    Args:
        date1: First date string
        date2: Second date string
        
    Returns:
        Number of days difference
    """
    if not date1 or not date2:
        return 999
    
    try:
        date1_obj = None
        date2_obj = None
        
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S']:
            try:
                if not date1_obj:
                    date1_obj = datetime.strptime(date1, fmt)
                if not date2_obj:
                    date2_obj = datetime.strptime(date2, fmt)
                if date1_obj and date2_obj:
                    break
            except ValueError:
                continue
        
        if date1_obj and date2_obj:
            return abs((date1_obj - date2_obj).days)
        
        return 999
        
    except Exception:
        return 999

def _get_additional_matching_factors(invoice_data: Dict, delivery_data: Dict) -> List[str]:
    """
    Get additional matching factors that might have contributed to the match.
    
    Args:
        invoice_data: Invoice metadata
        delivery_data: Delivery note metadata
        
    Returns:
        List of additional matching factors
    """
    factors = []
    
    # Check for special patterns
    invoice_number = invoice_data.get('invoice_number', '')
    delivery_number = delivery_data.get('delivery_note_number', '')
    
    # Check for sequential numbering
    if _are_sequential_numbers(invoice_number, delivery_number):
        factors.append("• Sequential document numbering")
    
    # Check for delivery note reference in invoice
    if delivery_number and delivery_number.lower() in str(invoice_data).lower():
        factors.append("• Delivery note number referenced in invoice")
    
    # Check for invoice number in delivery note
    if invoice_number and invoice_number.lower() in str(delivery_data).lower():
        factors.append("• Invoice number referenced in delivery note")
    
    # Check for similar document patterns
    if _similar_document_patterns(invoice_data, delivery_data):
        factors.append("• Similar document structure and patterns")
    
    return factors

def _are_sequential_numbers(num1: str, num2: str) -> bool:
    """
    Check if two document numbers are sequential.
    
    Args:
        num1: First document number
        num2: Second document number
        
    Returns:
        True if numbers are sequential
    """
    if not num1 or not num2:
        return False
    
    # Extract numeric parts
    num1_digits = re.findall(r'\d+', num1)
    num2_digits = re.findall(r'\d+', num2)
    
    if num1_digits and num2_digits:
        try:
            num1_val = int(num1_digits[-1])
            num2_val = int(num2_digits[-1])
            return abs(num1_val - num2_val) <= 5  # Within 5 numbers
        except ValueError:
            pass
    
    return False

def _similar_document_patterns(invoice_data: Dict, delivery_data: Dict) -> bool:
    """
    Check if invoice and delivery note have similar document patterns.
    
    Args:
        invoice_data: Invoice metadata
        delivery_data: Delivery note metadata
        
    Returns:
        True if documents have similar patterns
    """
    # Check for similar field structures
    invoice_fields = set(invoice_data.keys())
    delivery_fields = set(delivery_data.keys())
    
    # Check for common fields
    common_fields = invoice_fields.intersection(delivery_fields)
    if len(common_fields) >= 3:
        return True
    
    # Check for similar data types
    invoice_has_amount = 'total_amount' in invoice_data
    delivery_has_amount = 'total_amount' in delivery_data
    
    invoice_has_date = 'invoice_date' in invoice_data
    delivery_has_date = 'delivery_date' in delivery_data
    
    if invoice_has_amount == delivery_has_amount and invoice_has_date == delivery_has_date:
        return True
    
    return False

def get_match_confidence_level(match_score: float) -> str:
    """
    Get a human-readable confidence level for a match score.
    
    Args:
        match_score: Match confidence score (0.0 to 1.0)
        
    Returns:
        Confidence level string
    """
    if match_score >= 0.95:
        return "Very High"
    elif match_score >= 0.85:
        return "High"
    elif match_score >= 0.70:
        return "Medium"
    elif match_score >= 0.50:
        return "Low"
    else:
        return "Very Low"

def format_match_summary(invoice_data: Dict, delivery_data: Dict, match_score: float) -> str:
    """
    Generate a brief match summary for display.
    
    Args:
        invoice_data: Invoice metadata
        delivery_data: Delivery note metadata
        match_score: Match confidence score
        
    Returns:
        Brief summary string
    """
    confidence_level = get_match_confidence_level(match_score)
    
    invoice_number = invoice_data.get('invoice_number', 'Unknown')
    delivery_number = delivery_data.get('delivery_note_number', 'Unknown')
    
    return f"{confidence_level} confidence match: {delivery_number} → {invoice_number} ({match_score:.1%})"


if __name__ == "__main__":
    # Test the matching explainer
    logging.basicConfig(level=logging.INFO)
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "Successful Match",
            "invoice_data": {
                "invoice_number": "INV-02341",
                "supplier_name": "Bidfood",
                "invoice_date": "2025-07-20",
                "total_amount": 146.75,
                "total_items": 12
            },
            "delivery_data": {
                "delivery_note_number": "DN-9871",
                "supplier_name": "Bidfood",
                "delivery_date": "2025-07-20",
                "total_amount": 145.50,
                "total_items": 13
            },
            "match_score": 0.92,
            "threshold": 0.85
        },
        {
            "name": "Unsuccessful Match",
            "invoice_data": {
                "invoice_number": "INV-02341",
                "supplier_name": "Bidfood",
                "invoice_date": "2025-07-20",
                "total_amount": 146.75,
                "total_items": 12
            },
            "delivery_data": {
                "delivery_note_number": "DN-9871",
                "supplier_name": "Bidfood",
                "delivery_date": "2025-07-19",
                "total_amount": 138.75,
                "total_items": 10
            },
            "match_score": 0.68,
            "threshold": 0.85
        },
        {
            "name": "Similar Supplier Names",
            "invoice_data": {
                "invoice_number": "INV-02342",
                "supplier_name": "Quality Foods Ltd",
                "invoice_date": "2025-07-21",
                "total_amount": 200.00,
                "total_items": 8
            },
            "delivery_data": {
                "delivery_note_number": "DN-9872",
                "supplier_name": "Quality Foods Limited",
                "delivery_date": "2025-07-21",
                "total_amount": 200.00,
                "total_items": 8
            },
            "match_score": 0.88,
            "threshold": 0.85
        }
    ]
    
    print("🔍 Matching Explainer Test Results:")
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print(f"   Match Score: {scenario['match_score']:.2f}")
        print(f"   Threshold: {scenario['threshold']:.2f}")
        
        explanation = explain_match_status(
            scenario['invoice_data'],
            scenario['delivery_data'],
            scenario['match_score'],
            scenario['threshold']
        )
        
        print(f"   Explanation:")
        for line in explanation.split('\n'):
            print(f"   {line}")
        
        # Test confidence level
        confidence_level = get_match_confidence_level(scenario['match_score'])
        print(f"   Confidence Level: {confidence_level}")
        
        # Test summary
        summary = format_match_summary(
            scenario['invoice_data'],
            scenario['delivery_data'],
            scenario['match_score']
        )
        print(f"   Summary: {summary}")
    
    print("\n✅ Test completed successfully") 