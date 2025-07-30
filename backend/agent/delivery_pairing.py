"""
Delivery Pairing Module for Owlin Agent

Analyzes delivery note pairing with invoices and flags issues such as
missing delivery notes, quantity mismatches, and delivery date anomalies.
"""

import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def check_delivery_pairing(
    delivery_note_attached: bool,
    line_items: List[Dict[str, Any]],
    metadata: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Check delivery note pairing and flag potential issues.
    
    Analyzes whether delivery notes are properly matched with invoices
    and flags issues that may indicate delivery problems or missing documentation.
    
    Args:
        delivery_note_attached: Boolean indicating if delivery note was matched
        line_items: List of line item dictionaries
        metadata: Invoice metadata dictionary
        
    Returns:
        List of delivery-related flags
    """
    logger.debug("🔍 Starting delivery pairing analysis")
    
    flags = []
    
    # Check if delivery note is missing when expected
    if not delivery_note_attached:
        flags.extend(_check_missing_delivery_note(line_items, metadata))
    
    # Check for delivery-related issues even if note is attached
    if delivery_note_attached:
        flags.extend(_check_delivery_note_quality(line_items, metadata))
    
    # Check for delivery date anomalies
    flags.extend(_check_delivery_date_anomalies(metadata))
    
    # Check for quantity patterns that might indicate delivery issues
    flags.extend(_check_quantity_patterns(line_items))
    
    logger.debug(f"✅ Delivery pairing analysis completed. Found {len(flags)} flags")
    return flags

def _check_missing_delivery_note(
    line_items: List[Dict[str, Any]],
    metadata: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Check for missing delivery note and create appropriate flags.
    
    Args:
        line_items: List of line items
        metadata: Invoice metadata
        
    Returns:
        List of missing delivery note flags
    """
    flags = []
    
    # Determine if delivery note should be expected based on invoice characteristics
    should_have_delivery = _should_expect_delivery_note(line_items, metadata)
    
    if should_have_delivery:
        flags.append({
            "type": "missing_delivery_note",
            "severity": "warning",
            "field": "delivery_note",
            "message": "No delivery note found for this invoice",
            "suggested_action": "Request delivery note from supplier or check if it was received separately"
        })
        
        # Additional flag for high-value invoices
        total_amount = metadata.get('total_amount', 0.0)
        if total_amount > 500.0:
            flags.append({
                "type": "high_value_no_delivery",
                "severity": "critical",
                "field": "delivery_note",
                "message": f"High-value invoice (£{total_amount:.2f}) missing delivery note",
                "suggested_action": "Critical: Request delivery note immediately - high-value deliveries require documentation"
            })
    
    return flags

def _should_expect_delivery_note(
    line_items: List[Dict[str, Any]],
    metadata: Dict[str, Any]
) -> bool:
    """
    Determine if a delivery note should be expected for this invoice.
    
    Args:
        line_items: List of line items
        metadata: Invoice metadata
        
    Returns:
        True if delivery note should be expected
    """
    # Check invoice total - high-value invoices typically need delivery notes
    total_amount = metadata.get('total_amount', 0.0)
    if total_amount > 200.0:
        return True
    
    # Check for perishable goods that typically require delivery notes
    perishable_keywords = [
        'beef', 'chicken', 'pork', 'lamb', 'fish', 'salmon', 'tuna', 'cod',
        'vegetables', 'tomatoes', 'lettuce', 'onions', 'potatoes', 'carrots',
        'dairy', 'milk', 'cheese', 'yogurt', 'cream', 'butter',
        'bread', 'pastries', 'cakes', 'desserts',
        'fruits', 'apples', 'bananas', 'oranges', 'berries'
    ]
    
    for item in line_items:
        item_name = (item.get('item', '') or item.get('description', '')).lower()
        if any(keyword in item_name for keyword in perishable_keywords):
            return True
    
    # Check for large quantities that suggest delivery
    total_quantity = sum(item.get('quantity', 0.0) for item in line_items)
    if total_quantity > 10.0:
        return True
    
    return False

def _check_delivery_note_quality(
    line_items: List[Dict[str, Any]],
    metadata: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Check the quality of delivery note matching.
    
    Args:
        line_items: List of line items
        metadata: Invoice metadata
        
    Returns:
        List of delivery note quality flags
    """
    flags = []
    
    # Check for potential quantity mismatches
    for i, item in enumerate(line_items):
        quantity = item.get('quantity', 0.0)
        
        # Flag unusually large quantities that might indicate delivery issues
        if quantity > 50.0:
            flags.append({
                "type": "large_quantity",
                "severity": "warning",
                "field": f"line_items[{i}].quantity",
                "message": f"Large quantity ({quantity}) for {item.get('item', 'Unknown item')}",
                "suggested_action": "Verify quantity matches delivery note and check for potential errors"
            })
        
        # Flag zero quantities (shouldn't be on invoice)
        if quantity <= 0.0:
            flags.append({
                "type": "zero_quantity",
                "severity": "critical",
                "field": f"line_items[{i}].quantity",
                "message": f"Zero quantity for {item.get('item', 'Unknown item')}",
                "suggested_action": "Remove item from invoice or verify quantity"
            })
    
    return flags

def _check_delivery_date_anomalies(metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Check for delivery date anomalies.
    
    Args:
        metadata: Invoice metadata
        
    Returns:
        List of delivery date anomaly flags
    """
    flags = []
    
    invoice_date = metadata.get('invoice_date', '')
    if not invoice_date:
        return flags
    
    try:
        # Parse invoice date
        invoice_date_obj = datetime.strptime(invoice_date, "%Y-%m-%d")
        today = datetime.now()
        
        # Check for future delivery dates
        if invoice_date_obj > today:
            flags.append({
                "type": "future_delivery_date",
                "severity": "warning",
                "field": "invoice_date",
                "message": f"Invoice date ({invoice_date}) is in the future",
                "suggested_action": "Verify delivery date is correct - future dates may indicate errors"
            })
        
        # Check for very old deliveries
        days_old = (today - invoice_date_obj).days
        if days_old > 30:
            flags.append({
                "type": "old_delivery",
                "severity": "info",
                "field": "invoice_date",
                "message": f"Delivery is {days_old} days old ({invoice_date})",
                "suggested_action": "Consider if this delivery is still relevant for current operations"
            })
        
        # Check for weekend deliveries (unusual for business deliveries)
        if invoice_date_obj.weekday() >= 5:  # Saturday = 5, Sunday = 6
            flags.append({
                "type": "weekend_delivery",
                "severity": "info",
                "field": "invoice_date",
                "message": f"Weekend delivery on {invoice_date}",
                "suggested_action": "Verify if weekend delivery was expected and properly received"
            })
            
    except ValueError:
        flags.append({
            "type": "invalid_delivery_date",
            "severity": "warning",
            "field": "invoice_date",
            "message": f"Invalid delivery date format: {invoice_date}",
            "suggested_action": "Verify date format and correct if needed"
        })
    
    return flags

def _check_quantity_patterns(line_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Check for quantity patterns that might indicate delivery issues.
    
    Args:
        line_items: List of line items
        
    Returns:
        List of quantity pattern flags
    """
    flags = []
    
    if not line_items:
        return flags
    
    # Check for mixed delivery patterns
    quantities = [item.get('quantity', 0.0) for item in line_items]
    non_zero_quantities = [q for q in quantities if q > 0]
    
    if non_zero_quantities:
        # Check for unusual quantity patterns
        avg_quantity = sum(non_zero_quantities) / len(non_zero_quantities)
        
        # Flag items with quantities much higher than average
        for i, item in enumerate(line_items):
            quantity = item.get('quantity', 0.0)
            if quantity > avg_quantity * 3:  # 3x average
                flags.append({
                    "type": "unusual_quantity",
                    "severity": "warning",
                    "field": f"line_items[{i}].quantity",
                    "message": f"Unusually high quantity ({quantity}) for {item.get('item', 'Unknown item')}",
                    "suggested_action": "Verify quantity matches delivery note and check for potential errors"
                })
        
        # Check for very small quantities that might be delivery errors
        for i, item in enumerate(line_items):
            quantity = item.get('quantity', 0.0)
            if 0 < quantity < 0.5:  # Very small quantities
                flags.append({
                    "type": "very_small_quantity",
                    "severity": "info",
                    "field": f"line_items[{i}].quantity",
                    "message": f"Very small quantity ({quantity}) for {item.get('item', 'Unknown item')}",
                    "suggested_action": "Verify if this small quantity is correct or a delivery error"
                })
    
    return flags

def get_delivery_summary(
    delivery_note_attached: bool,
    line_items: List[Dict[str, Any]],
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate a summary of delivery analysis.
    
    Args:
        delivery_note_attached: Whether delivery note was matched
        line_items: List of line items
        metadata: Invoice metadata
        
    Returns:
        Dictionary with delivery analysis summary
    """
    total_items = len(line_items)
    total_quantity = sum(item.get('quantity', 0.0) for item in line_items)
    total_value = metadata.get('total_amount', 0.0)
    
    should_have_delivery = _should_expect_delivery_note(line_items, metadata)
    
    return {
        "delivery_note_attached": delivery_note_attached,
        "should_have_delivery": should_have_delivery,
        "delivery_missing": should_have_delivery and not delivery_note_attached,
        "total_items": total_items,
        "total_quantity": total_quantity,
        "total_value": total_value,
        "high_value": total_value > 500.0,
        "large_quantity": total_quantity > 50.0
    }


if __name__ == "__main__":
    # Test delivery pairing
    logging.basicConfig(level=logging.INFO)
    
    # Test case 1: Missing delivery note for perishable goods
    line_items = [
        {
            "item": "Beef Sirloin",
            "quantity": 5.0,
            "unit_price_excl_vat": 20.00,
            "line_total_excl_vat": 100.00
        },
        {
            "item": "Fresh Vegetables",
            "quantity": 10.0,
            "unit_price_excl_vat": 2.50,
            "line_total_excl_vat": 25.00
        }
    ]
    
    metadata = {
        "supplier_name": "Quality Foods Ltd",
        "invoice_date": "2024-12-01",
        "total_amount": 150.00
    }
    
    flags = check_delivery_pairing(False, line_items, metadata)
    
    print("🔍 Delivery Pairing Analysis:")
    print(f"Flags found: {len(flags)}")
    for flag in flags:
        print(f"  - {flag['message']}")
        print(f"    Action: {flag['suggested_action']}")
    
    # Test case 2: Delivery note attached
    flags = check_delivery_pairing(True, line_items, metadata)
    
    print(f"\n✅ Delivery Note Attached:")
    print(f"Flags found: {len(flags)}")
    for flag in flags:
        print(f"  - {flag['message']}")
        print(f"    Action: {flag['suggested_action']}")
    
    # Test delivery summary
    summary = get_delivery_summary(False, line_items, metadata)
    print(f"\n📊 Delivery Summary:")
    print(f"  Delivery note attached: {summary['delivery_note_attached']}")
    print(f"  Should have delivery: {summary['should_have_delivery']}")
    print(f"  Delivery missing: {summary['delivery_missing']}")
    print(f"  Total items: {summary['total_items']}")
    print(f"  Total quantity: {summary['total_quantity']}")
    print(f"  Total value: £{summary['total_value']:.2f}")
    print(f"  High value: {summary['high_value']}")
    print(f"  Large quantity: {summary['large_quantity']}") 