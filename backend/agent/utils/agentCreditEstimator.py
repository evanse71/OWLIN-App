"""
Agent Credit Estimator System

This module provides logic for automatically calculating and suggesting
credit values when items are missing, short-delivered, or mischarged.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)

class PriceHistory:
    """Container for price history data."""
    
    def __init__(
        self,
        item_name: str,
        unit_price: float,
        supplier_id: str,
        supplier_name: str,
        date: datetime,
        quantity: int = 1,
        vat_rate: float = 0.20,
        is_valid: bool = True
    ):
        self.item_name = item_name
        self.unit_price = unit_price
        self.supplier_id = supplier_id
        self.supplier_name = supplier_name
        self.date = date
        self.quantity = quantity
        self.vat_rate = vat_rate
        self.is_valid = is_valid

class LineItem:
    """Container for invoice line item data."""
    
    def __init__(
        self,
        id: str,
        name: str,
        quantity: int,
        unit_price: float,
        total: float,
        status: str = "normal",
        expected_quantity: Optional[int] = None,
        actual_quantity: Optional[int] = None,
        vat_rate: float = 0.20,
        notes: Optional[str] = None
    ):
        self.id = id
        self.name = name
        self.quantity = quantity
        self.unit_price = unit_price
        self.total = total
        self.status = status
        self.expected_quantity = expected_quantity
        self.actual_quantity = actual_quantity
        self.vat_rate = vat_rate
        self.notes = notes

class CreditSuggestion:
    """Container for credit suggestion data."""
    
    def __init__(
        self,
        suggested_credit: float,
        confidence: int,
        reason: str,
        base_price: float,
        quantity_delta: int,
        vat_amount: float,
        price_source: str,
        item_name: str
    ):
        self.suggested_credit = suggested_credit
        self.confidence = confidence
        self.reason = reason
        self.base_price = base_price
        self.quantity_delta = quantity_delta
        self.vat_amount = vat_amount
        self.price_source = price_source
        self.item_name = item_name

def get_price_history(item_name: str, supplier_id: str = None, days_back: int = 90) -> List[PriceHistory]:
    """
    Get price history for an item from the database.
    
    Args:
        item_name: The item name to search for
        supplier_id: Optional supplier ID to filter by
        days_back: Number of days to look back
        
    Returns:
        List of PriceHistory objects
    """
    try:
        # In a real implementation, this would query the database
        # For now, we'll return mock data based on item name
        
        # Mock data generation based on item name
        import hashlib
        hash_obj = hashlib.md5(item_name.encode())
        hash_int = int(hash_obj.hexdigest()[:8], 16)
        
        # Generate realistic mock price history
        base_price = (hash_int % 50) + 10  # £10-60 base price
        price_variation = (hash_int % 20) - 10  # ±£10 variation
        
        history = []
        for i in range(5):  # Last 5 transactions
            date = datetime.now() - timedelta(days=i * 15)  # Every 15 days
            unit_price = base_price + (price_variation * (i % 3 - 1)) / 10  # Varying prices
            vat_rate = 0.20 if hash_int % 3 != 0 else 0.05  # Most items have 20% VAT
            
            history.append(PriceHistory(
                item_name=item_name,
                unit_price=unit_price,
                supplier_id=f"SUP-{hash_int % 1000:03d}",
                supplier_name=f"Supplier {hash_int % 1000}",
                date=date,
                quantity=hash_int % 20 + 1,
                vat_rate=vat_rate,
                is_valid=True
            ))
        
        logger.debug(f"📊 Retrieved price history for {item_name}: {len(history)} records")
        return history
        
    except Exception as e:
        logger.error(f"❌ Error getting price history for {item_name}: {str(e)}")
        return []

def get_average_price_across_suppliers(item_name: str) -> Optional[float]:
    """
    Get average price across all suppliers for an item.
    
    Args:
        item_name: The item name
        
    Returns:
        Average price or None if no data available
    """
    try:
        # In a real implementation, this would query the database
        # For now, we'll return a mock average price
        
        import hashlib
        hash_obj = hashlib.md5(item_name.encode())
        hash_int = int(hash_obj.hexdigest()[:8], 16)
        
        # Generate realistic average price
        base_price = (hash_int % 40) + 15  # £15-55 average price
        average_price = base_price + (hash_int % 10) / 10  # Add some decimal variation
        
        logger.debug(f"📊 Retrieved average price for {item_name}: £{average_price:.2f}")
        return average_price
        
    except Exception as e:
        logger.error(f"❌ Error getting average price for {item_name}: {str(e)}")
        return None

def calculate_quantity_delta(item: LineItem) -> int:
    """
    Calculate the quantity delta for a line item.
    
    Args:
        item: LineItem object
        
    Returns:
        Quantity delta (positive for overcharge, negative for missing)
    """
    if item.status == "missing":
        # Item was not delivered at all
        return -item.quantity
    elif item.status == "mismatched" and item.expected_quantity and item.actual_quantity:
        # Quantity mismatch
        return item.expected_quantity - item.actual_quantity
    elif item.status == "flagged":
        # Price discrepancy - assume 1 unit overcharge for simplicity
        # In a real implementation, this would be more sophisticated
        return 1
    elif item.status == "overcharged":
        # Overcharged item - assume 1 unit overcharge for simplicity
        # In a real implementation, this would calculate based on price difference
        return 1
    else:
        return 0

def suggest_credit_for_line_item(item: LineItem, price_history: List[PriceHistory]) -> Optional[CreditSuggestion]:
    """
    Suggest credit for a line item based on price history.
    
    Args:
        item: LineItem object
        price_history: List of PriceHistory objects
        
    Returns:
        CreditSuggestion object or None if no credit needed
    """
    try:
        # Calculate quantity delta
        quantity_delta = calculate_quantity_delta(item)
        
        if quantity_delta == 0:
            logger.debug(f"No credit needed for {item.name}")
            return None
        
        # Get most recent valid price from history
        recent_price = None
        confidence = 0
        price_source = ""
        
        if price_history:
            # Sort by date, most recent first
            sorted_history = sorted(price_history, key=lambda x: x.date, reverse=True)
            
            # Find most recent valid price
            for price_record in sorted_history:
                if price_record.is_valid and price_record.item_name.lower() == item.name.lower():
                    recent_price = price_record.unit_price
                    confidence = 85  # High confidence with recent price
                    price_source = f"Recent price from {price_record.supplier_name}"
                    break
        
        # Fallback to average price if no recent price found
        if recent_price is None:
            average_price = get_average_price_across_suppliers(item.name)
            if average_price:
                recent_price = average_price
                confidence = 60  # Lower confidence with average price
                price_source = "Average price across suppliers"
            else:
                # Use current unit price as last resort
                recent_price = item.unit_price
                confidence = 40  # Very low confidence
                price_source = "Current invoice price"
        
        # Calculate credit amount
        base_amount = recent_price * abs(quantity_delta)
        vat_amount = base_amount * item.vat_rate
        total_credit = base_amount + vat_amount
        
        # Round to 2 decimal places
        total_credit = round(total_credit, 2)
        vat_amount = round(vat_amount, 2)
        
        # Generate reason
        if quantity_delta < 0:
            reason = f"Based on unit price of £{recent_price:.2f} x {abs(quantity_delta)} missing units"
        else:
            reason = f"Based on unit price of £{recent_price:.2f} x {quantity_delta} overcharged units"
        
        if item.vat_rate > 0:
            reason += f" (incl. VAT)"
        
        suggestion = CreditSuggestion(
            suggested_credit=total_credit,
            confidence=confidence,
            reason=reason,
            base_price=recent_price,
            quantity_delta=quantity_delta,
            vat_amount=vat_amount,
            price_source=price_source,
            item_name=item.name
        )
        
        logger.info(f"💰 Credit suggestion for {item.name}: £{total_credit:.2f} (confidence: {confidence}%)")
        return suggestion
        
    except Exception as e:
        logger.error(f"❌ Error suggesting credit for {item.name}: {str(e)}")
        return None

def suggest_credits_for_invoice(line_items: List[LineItem]) -> List[CreditSuggestion]:
    """
    Suggest credits for all flagged line items in an invoice.
    
    Args:
        line_items: List of LineItem objects
        
    Returns:
        List of CreditSuggestion objects
    """
    suggestions = []
    
    for item in line_items:
        if item.status in ["missing", "mismatched", "flagged"]:
            # Get price history for this item
            price_history = get_price_history(item.name)
            
            # Suggest credit
            suggestion = suggest_credit_for_line_item(item, price_history)
            
            if suggestion:
                suggestions.append(suggestion)
    
    logger.info(f"💰 Generated {len(suggestions)} credit suggestions for invoice")
    return suggestions

def get_confidence_label(confidence: int) -> str:
    """
    Get a human-readable confidence label.
    
    Args:
        confidence: Confidence percentage (0-100)
        
    Returns:
        Confidence label
    """
    if confidence >= 80:
        return "High confidence"
    elif confidence >= 60:
        return "Likely accurate"
    else:
        return "Check manually"

def format_credit_suggestion(suggestion: CreditSuggestion) -> Dict[str, Any]:
    """
    Format a credit suggestion for frontend display.
    
    Args:
        suggestion: CreditSuggestion object
        
    Returns:
        Formatted dictionary for frontend
    """
    return {
        "suggested_credit": suggestion.suggested_credit,
        "confidence": suggestion.confidence,
        "confidence_label": get_confidence_label(suggestion.confidence),
        "reason": suggestion.reason,
        "base_price": suggestion.base_price,
        "quantity_delta": suggestion.quantity_delta,
        "vat_amount": suggestion.vat_amount,
        "price_source": suggestion.price_source,
        "item_name": suggestion.item_name
    }

# Convenience function for testing
def test_credit_estimation():
    """Test the credit estimation logic with sample data."""
    
    # Sample line items
    line_items = [
        LineItem(
            id="1",
            name="Toilet Roll 2ply",
            quantity=10,
            unit_price=1.20,
            total=12.00,
            status="missing",
            expected_quantity=10,
            actual_quantity=6,
            vat_rate=0.20,
            notes="4 units missing"
        ),
        LineItem(
            id="2",
            name="Beef Steaks",
            quantity=5,
            unit_price=8.50,
            total=42.50,
            status="flagged",
            vat_rate=0.20,
            notes="Price 15% higher than usual"
        ),
        LineItem(
            id="3",
            name="Chicken Breast",
            quantity=5,
            unit_price=4.20,
            total=21.00,
            status="mismatched",
            expected_quantity=5,
            actual_quantity=3,
            vat_rate=0.20,
            notes="Only 3 received"
        )
    ]
    
    print("🧪 Testing credit estimation...")
    
    suggestions = suggest_credits_for_invoice(line_items)
    
    for suggestion in suggestions:
        print(f"💰 {suggestion.item_name}: £{suggestion.suggested_credit:.2f}")
        print(f"   Confidence: {suggestion.confidence}% ({get_confidence_label(suggestion.confidence)})")
        print(f"   Reason: {suggestion.reason}")
        print(f"   Price source: {suggestion.price_source}")
        print()
    
    print("✅ Credit estimation test completed")

if __name__ == "__main__":
    test_credit_estimation() 