"""
Credit Suggestion Engine Module for Owlin Agent

Provides automatic credit value suggestions when an invoice or delivery note
has a mismatch (e.g., short delivery, overcharge, missing item). Shown to
Finance and GM users as helper suggestions but never auto-submits.
"""

import logging
from typing import Dict, List, Any, Optional
from statistics import mean, median
import math

logger = logging.getLogger(__name__)

def suggest_credit(item: dict, pricing_history: list = []) -> dict:
    """
    Suggest credit amount for a mismatched invoice line item.
    
    Args:
        item: Dictionary representing the invoice line item
        pricing_history: Optional list of past unit prices for this item
        
    Returns:
        Dictionary with credit suggestion details
    """
    logger.info(f"💳 Suggesting credit for item: {item.get('item', 'Unknown')}")
    
    try:
        # Extract key values from item
        item_name = item.get('item', 'Unknown')
        quantity_expected = item.get('quantity_expected', 0)
        quantity_received = item.get('quantity_received', 0)
        unit_price_excl_vat = item.get('unit_price_excl_vat', 0.0)
        vat_rate = item.get('vat_rate', 20.0)
        
        # Determine the type of mismatch and calculate credit
        mismatch_type, credit_amount_excl_vat, reason = _analyze_mismatch(
            quantity_expected, quantity_received, unit_price_excl_vat, 
            pricing_history, item_name
        )
        
        # Calculate VAT-inclusive amount
        credit_amount_incl_vat = credit_amount_excl_vat * (1 + (vat_rate / 100))
        
        # Round to 2 decimal places for currency
        credit_amount_excl_vat = round(credit_amount_excl_vat, 2)
        credit_amount_incl_vat = round(credit_amount_incl_vat, 2)
        
        suggestion = {
            "credit_amount_excl_vat": credit_amount_excl_vat,
            "credit_amount_incl_vat": credit_amount_incl_vat,
            "reason": reason,
            "mismatch_type": mismatch_type,
            "item_name": item_name,
            "quantity_expected": quantity_expected,
            "quantity_received": quantity_received,
            "unit_price_excl_vat": unit_price_excl_vat,
            "vat_rate": vat_rate
        }
        
        logger.info(f"✅ Credit suggestion: £{credit_amount_excl_vat:.2f} excl VAT ({reason})")
        return suggestion
        
    except Exception as e:
        logger.error(f"❌ Error suggesting credit: {e}")
        return _get_fallback_suggestion(item)

def _analyze_mismatch(
    quantity_expected: float, 
    quantity_received: float, 
    unit_price_excl_vat: float,
    pricing_history: list,
    item_name: str
) -> tuple:
    """
    Analyze the mismatch and determine credit amount.
    
    Args:
        quantity_expected: Expected quantity
        quantity_received: Actually received quantity
        unit_price_excl_vat: Current unit price
        pricing_history: List of historical prices
        item_name: Name of the item
        
    Returns:
        Tuple of (mismatch_type, credit_amount, reason)
    """
    quantity_difference = quantity_expected - quantity_received
    
    # Case 1: Short delivery (received less than expected)
    if quantity_difference > 0:
        credit_amount = quantity_difference * unit_price_excl_vat
        reason = f"Short delivery of {int(quantity_difference)} units at £{unit_price_excl_vat:.2f} each"
        return "short_delivery", credit_amount, reason
    
    # Case 2: Overdelivery (received more than expected)
    elif quantity_difference < 0:
        # No credit for overdelivery
        reason = f"Supplier overdelivered by {int(abs(quantity_difference))} units - no credit due"
        return "overdelivery", 0.0, reason
    
    # Case 3: Quantities match, check for overcharge
    else:
        return _check_for_overcharge(unit_price_excl_vat, pricing_history, item_name)

def _check_for_overcharge(
    current_price: float, 
    pricing_history: list, 
    item_name: str
) -> tuple:
    """
    Check if current price is an overcharge compared to historical prices.
    
    Args:
        current_price: Current unit price
        pricing_history: List of historical prices
        item_name: Name of the item
        
    Returns:
        Tuple of (mismatch_type, credit_amount, reason)
    """
    if not pricing_history or len(pricing_history) < 2:
        # No historical data available
        reason = "No pricing history available for overcharge analysis"
        return "no_history", 0.0, reason
    
    # Calculate average and median of historical prices
    avg_price = mean(pricing_history)
    median_price = median(pricing_history)
    
    # Use the lower of average or median to be conservative
    reference_price = min(avg_price, median_price)
    
    # Calculate price difference percentage
    price_difference = current_price - reference_price
    price_difference_percentage = (price_difference / reference_price) * 100
    
    # Check if this constitutes an overcharge (>5% increase)
    if price_difference_percentage > 5.0:
        # Calculate overcharge amount per unit
        overcharge_per_unit = price_difference
        
        # For overcharge, we need to know the quantity to calculate total credit
        # Since we don't have quantity in this context, we'll return per-unit overcharge
        reason = f"Overcharge of £{overcharge_per_unit:.2f} per unit ({price_difference_percentage:.1f}% above average)"
        return "overcharge", overcharge_per_unit, reason
    else:
        reason = f"No significant overcharge detected (price within {price_difference_percentage:.1f}% of average)"
        return "no_overcharge", 0.0, reason

def suggest_credit_for_quantity_mismatch(
    item: dict, 
    quantity_expected: float, 
    quantity_received: float
) -> dict:
    """
    Suggest credit specifically for quantity mismatches.
    
    Args:
        item: Dictionary representing the invoice line item
        quantity_expected: Expected quantity
        quantity_received: Actually received quantity
        
    Returns:
        Dictionary with credit suggestion details
    """
    logger.info(f"📦 Suggesting credit for quantity mismatch: {item.get('item', 'Unknown')}")
    
    # Create a modified item with the specific quantities
    modified_item = item.copy()
    modified_item['quantity_expected'] = quantity_expected
    modified_item['quantity_received'] = quantity_received
    
    return suggest_credit(modified_item)

def suggest_credit_for_overcharge(
    item: dict, 
    pricing_history: list
) -> dict:
    """
    Suggest credit specifically for overcharge scenarios.
    
    Args:
        item: Dictionary representing the invoice line item
        pricing_history: List of historical prices
        
    Returns:
        Dictionary with credit suggestion details
    """
    logger.info(f"💰 Suggesting credit for overcharge: {item.get('item', 'Unknown')}")
    
    # Create a modified item with matching quantities (no quantity mismatch)
    modified_item = item.copy()
    modified_item['quantity_expected'] = item.get('quantity_received', 0)
    modified_item['quantity_received'] = item.get('quantity_received', 0)
    
    return suggest_credit(modified_item, pricing_history)

def suggest_credit_for_missing_item(item: dict) -> dict:
    """
    Suggest credit for completely missing items.
    
    Args:
        item: Dictionary representing the invoice line item
        
    Returns:
        Dictionary with credit suggestion details
    """
    logger.info(f"❌ Suggesting credit for missing item: {item.get('item', 'Unknown')}")
    
    # Create a modified item with zero received quantity
    modified_item = item.copy()
    modified_item['quantity_expected'] = item.get('quantity_expected', 0)
    modified_item['quantity_received'] = 0
    
    return suggest_credit(modified_item)

def validate_credit_suggestion(suggestion: dict) -> dict:
    """
    Validate a credit suggestion for reasonableness.
    
    Args:
        suggestion: Credit suggestion dictionary
        
    Returns:
        Dictionary with validation results
    """
    logger.info(f"🔍 Validating credit suggestion for: {suggestion.get('item_name', 'Unknown')}")
    
    validation_result = {
        "is_valid": True,
        "warnings": [],
        "errors": []
    }
    
    # Check for reasonable credit amounts
    credit_amount = suggestion.get('credit_amount_excl_vat', 0)
    
    if credit_amount < 0:
        validation_result["is_valid"] = False
        validation_result["errors"].append("Credit amount cannot be negative")
    
    if credit_amount > 10000:  # £10,000 limit
        validation_result["warnings"].append("Credit amount exceeds £10,000 - verify manually")
    
    # Check for reasonable unit prices
    unit_price = suggestion.get('unit_price_excl_vat', 0)
    if unit_price > 1000:  # £1,000 per unit limit
        validation_result["warnings"].append("Unit price exceeds £1,000 - verify manually")
    
    # Check for reasonable quantities
    quantity_expected = suggestion.get('quantity_expected', 0)
    quantity_received = suggestion.get('quantity_received', 0)
    
    if quantity_expected > 10000:  # 10,000 unit limit
        validation_result["warnings"].append("Expected quantity exceeds 10,000 - verify manually")
    
    if quantity_received < 0:
        validation_result["is_valid"] = False
        validation_result["errors"].append("Received quantity cannot be negative")
    
    # Check mismatch type logic
    mismatch_type = suggestion.get('mismatch_type', '')
    if mismatch_type == 'short_delivery' and credit_amount <= 0:
        validation_result["warnings"].append("Short delivery detected but no credit calculated")
    
    if mismatch_type == 'overdelivery' and credit_amount > 0:
        validation_result["warnings"].append("Overdelivery detected but credit calculated")
    
    logger.info(f"✅ Validation result: {validation_result['is_valid']} ({len(validation_result['warnings'])} warnings)")
    return validation_result

def format_credit_suggestion_for_ui(suggestion: dict) -> dict:
    """
    Format credit suggestion for UI display.
    
    Args:
        suggestion: Credit suggestion dictionary
        
    Returns:
        Formatted dictionary for UI
    """
    validation = validate_credit_suggestion(suggestion)
    
    # Determine display color based on validation
    if not validation['is_valid']:
        display_color = "red"
        display_status = "error"
    elif validation['warnings']:
        display_color = "orange"
        display_status = "warning"
    else:
        display_color = "green"
        display_status = "valid"
    
    # Format currency amounts
    credit_excl_vat = suggestion.get('credit_amount_excl_vat', 0)
    credit_incl_vat = suggestion.get('credit_amount_incl_vat', 0)
    
    formatted = {
        "id": f"credit_{suggestion.get('item_name', 'unknown').replace(' ', '_').lower()}",
        "item_name": suggestion.get('item_name', 'Unknown'),
        "credit_amount_excl_vat": credit_excl_vat,
        "credit_amount_incl_vat": credit_incl_vat,
        "credit_amount_excl_vat_formatted": f"£{credit_excl_vat:.2f}",
        "credit_amount_incl_vat_formatted": f"£{credit_incl_vat:.2f}",
        "reason": suggestion.get('reason', ''),
        "mismatch_type": suggestion.get('mismatch_type', ''),
        "display_color": display_color,
        "display_status": display_status,
        "validation": validation,
        "can_copy": credit_excl_vat > 0,
        "copy_text": f"£{credit_excl_vat:.2f} excl VAT" if credit_excl_vat > 0 else "No credit due"
    }
    
    return formatted

def get_credit_summary(suggestions: list) -> dict:
    """
    Generate a summary of multiple credit suggestions.
    
    Args:
        suggestions: List of credit suggestion dictionaries
        
    Returns:
        Dictionary with summary information
    """
    logger.info(f"📊 Generating credit summary for {len(suggestions)} suggestions")
    
    total_credit_excl_vat = sum(s.get('credit_amount_excl_vat', 0) for s in suggestions)
    total_credit_incl_vat = sum(s.get('credit_amount_incl_vat', 0) for s in suggestions)
    
    # Count by mismatch type
    mismatch_counts = {}
    for suggestion in suggestions:
        mismatch_type = suggestion.get('mismatch_type', 'unknown')
        mismatch_counts[mismatch_type] = mismatch_counts.get(mismatch_type, 0) + 1
    
    # Count validation issues
    total_warnings = 0
    total_errors = 0
    for suggestion in suggestions:
        validation = validate_credit_suggestion(suggestion)
        total_warnings += len(validation.get('warnings', []))
        total_errors += len(validation.get('errors', []))
    
    summary = {
        "total_suggestions": len(suggestions),
        "total_credit_excl_vat": round(total_credit_excl_vat, 2),
        "total_credit_incl_vat": round(total_credit_incl_vat, 2),
        "total_credit_excl_vat_formatted": f"£{total_credit_excl_vat:.2f}",
        "total_credit_incl_vat_formatted": f"£{total_credit_incl_vat:.2f}",
        "mismatch_type_counts": mismatch_counts,
        "total_warnings": total_warnings,
        "total_errors": total_errors,
        "has_issues": total_errors > 0,
        "has_warnings": total_warnings > 0
    }
    
    logger.info(f"✅ Credit summary: £{total_credit_excl_vat:.2f} total credit")
    return summary

def _get_fallback_suggestion(item: dict) -> dict:
    """
    Generate a fallback suggestion when analysis fails.
    
    Args:
        item: Original item dictionary
        
    Returns:
        Fallback suggestion dictionary
    """
    return {
        "credit_amount_excl_vat": 0.0,
        "credit_amount_incl_vat": 0.0,
        "reason": "Unable to calculate credit - manual review required",
        "mismatch_type": "calculation_error",
        "item_name": item.get('item', 'Unknown'),
        "quantity_expected": item.get('quantity_expected', 0),
        "quantity_received": item.get('quantity_received', 0),
        "unit_price_excl_vat": item.get('unit_price_excl_vat', 0.0),
        "vat_rate": item.get('vat_rate', 20.0)
    }


if __name__ == "__main__":
    # Test the credit suggestion engine
    logging.basicConfig(level=logging.INFO)
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "Short Delivery",
            "item": {
                "item": "Coca-Cola 330ml",
                "quantity_expected": 24,
                "quantity_received": 20,
                "unit_price_excl_vat": 0.75,
                "vat_rate": 20.0
            },
            "pricing_history": [0.70, 0.72, 0.74, 0.75]
        },
        {
            "name": "Overcharge",
            "item": {
                "item": "Beef Sirloin",
                "quantity_expected": 5,
                "quantity_received": 5,
                "unit_price_excl_vat": 25.00,
                "vat_rate": 20.0
            },
            "pricing_history": [18.50, 19.00, 20.50, 21.00, 20.00]
        },
        {
            "name": "Missing Item",
            "item": {
                "item": "Chicken Breast",
                "quantity_expected": 10,
                "quantity_received": 0,
                "unit_price_excl_vat": 12.00,
                "vat_rate": 20.0
            },
            "pricing_history": [11.50, 12.00, 12.50]
        },
        {
            "name": "Overdelivery",
            "item": {
                "item": "Fresh Vegetables",
                "quantity_expected": 5,
                "quantity_received": 7,
                "unit_price_excl_vat": 2.50,
                "vat_rate": 20.0
            },
            "pricing_history": [2.40, 2.50, 2.60]
        }
    ]
    
    print("💳 Credit Suggestion Engine Test Results:")
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        
        # Test basic credit suggestion
        suggestion = suggest_credit(scenario['item'], scenario['pricing_history'])
        print(f"   Credit: £{suggestion['credit_amount_excl_vat']:.2f} excl VAT")
        print(f"   Reason: {suggestion['reason']}")
        print(f"   Type: {suggestion['mismatch_type']}")
        
        # Test validation
        validation = validate_credit_suggestion(suggestion)
        print(f"   Valid: {validation['is_valid']}")
        if validation['warnings']:
            print(f"   Warnings: {validation['warnings']}")
        
        # Test UI formatting
        formatted = format_credit_suggestion_for_ui(suggestion)
        print(f"   Display: {formatted['display_status']} ({formatted['display_color']})")
        print(f"   Copy Text: {formatted['copy_text']}")
    
    # Test summary
    all_suggestions = [
        suggest_credit(scenario['item'], scenario['pricing_history'])
        for scenario in test_scenarios
    ]
    
    summary = get_credit_summary(all_suggestions)
    print(f"\n📊 Summary:")
    print(f"   Total Credit: {summary['total_credit_excl_vat_formatted']}")
    print(f"   Suggestions: {summary['total_suggestions']}")
    print(f"   Mismatch Types: {summary['mismatch_type_counts']}")
    
    print("\n✅ Test completed successfully") 