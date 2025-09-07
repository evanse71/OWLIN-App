"""
Credit Suggestion Module for Owlin Agent

Analyzes invoice mismatches and provides intelligent credit recommendations
for suppliers based on overcharges, missing items, and other discrepancies.
"""

import logging
import sqlite3
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

def suggest_credits_for_invoice(invoice_id: str, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """
    Suggest credit amounts for an invoice based on detected mismatches.
    
    Analyzes the invoice_mismatches table for overcharges and missing items,
    then calculates appropriate credit amounts for each issue.
    
    Args:
        invoice_id: The ID of the invoice to analyze
        conn: SQLite database connection
        
    Returns:
        List of credit suggestions with details:
        [
            {
                "item": str,                    # Item name
                "reason": str,                   # Reason for credit (e.g., "Overcharged", "Missing Item")
                "suggested_credit": float,       # Credit amount in GBP
                "quantity": float,               # Quantity involved
                "unit_price": float,            # Current unit price
                "avg_price": float,             # Average historical price (for overcharges)
                "mismatch_type": str,           # Type of mismatch detected
                "confidence": float,            # Confidence in the suggestion (0-100)
                "evidence": str                 # Supporting evidence for the credit
            }
        ]
    """
    logger.info(f"🔍 Analyzing credit suggestions for invoice: {invoice_id}")
    
    try:
        # Query mismatches for this invoice
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                item_name,
                mismatch_type,
                current_quantity,
                current_unit_price,
                current_line_total,
                historical_avg_price,
                historical_median_price,
                price_difference,
                quantity_difference,
                confidence_score,
                detection_timestamp,
                notes
            FROM invoice_mismatches 
            WHERE invoice_id = ? 
            AND mismatch_type IN ('overcharge', 'missing_item', 'price_increase', 'quantity_mismatch')
            ORDER BY confidence_score DESC
        """, (invoice_id,))
        
        mismatches = cursor.fetchall()
        logger.info(f"📊 Found {len(mismatches)} mismatches to analyze")
        
        credit_suggestions = []
        
        for mismatch in mismatches:
            suggestion = _analyze_mismatch_for_credit(mismatch, invoice_id)
            if suggestion:
                credit_suggestions.append(suggestion)
        
        logger.info(f"✅ Generated {len(credit_suggestions)} credit suggestions")
        return credit_suggestions
        
    except Exception as e:
        logger.error(f"❌ Error analyzing credit suggestions: {e}")
        return []

def _analyze_mismatch_for_credit(mismatch: tuple, invoice_id: str) -> Optional[Dict[str, Any]]:
    """
    Analyze a single mismatch and generate credit suggestion.
    
    Args:
        mismatch: Tuple from database query
        invoice_id: Invoice ID for context
        
    Returns:
        Credit suggestion dictionary or None if no credit warranted
    """
    try:
        # Unpack mismatch data
        (item_name, mismatch_type, current_quantity, current_unit_price, 
         current_line_total, historical_avg_price, historical_median_price,
         price_difference, quantity_difference, confidence_score,
         detection_timestamp, notes) = mismatch
        
        # Skip if confidence is too low
        if confidence_score < 50.0:
            logger.debug(f"⚠️ Skipping {item_name} - confidence too low ({confidence_score:.1f}%)")
            return None
        
        suggestion = {
            "item": item_name,
            "mismatch_type": mismatch_type,
            "quantity": current_quantity or 0.0,
            "unit_price": current_unit_price or 0.0,
            "avg_price": historical_avg_price or 0.0,
            "confidence": confidence_score,
            "evidence": notes or "",
            "detection_timestamp": detection_timestamp
        }
        
        # Calculate credit based on mismatch type
        if mismatch_type == "overcharge":
            return _calculate_overcharge_credit(suggestion)
        elif mismatch_type == "missing_item":
            return _calculate_missing_item_credit(suggestion)
        elif mismatch_type == "price_increase":
            return _calculate_price_increase_credit(suggestion)
        elif mismatch_type == "quantity_mismatch":
            return _calculate_quantity_mismatch_credit(suggestion)
        else:
            logger.debug(f"⚠️ Unknown mismatch type: {mismatch_type}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error analyzing mismatch: {e}")
        return None

def _calculate_overcharge_credit(suggestion: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate credit for overcharge mismatch.
    
    Credit = (current_unit_price - avg_price) * quantity
    """
    current_price = suggestion["unit_price"]
    avg_price = suggestion["avg_price"]
    quantity = suggestion["quantity"]
    
    if current_price > avg_price and quantity > 0:
        credit_amount = (current_price - avg_price) * quantity
        suggestion.update({
            "reason": "Overcharged",
            "suggested_credit": round(credit_amount, 2),
            "price_difference": round(current_price - avg_price, 2),
            "evidence": f"Charged £{current_price:.2f} vs average £{avg_price:.2f} for {quantity} units"
        })
        return suggestion
    else:
        return None

def _calculate_missing_item_credit(suggestion: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate credit for missing item mismatch.
    
    Credit = full line total (since item was charged but not delivered)
    """
    line_total = suggestion.get("unit_price", 0) * suggestion.get("quantity", 0)
    
    if line_total > 0:
        suggestion.update({
            "reason": "Missing Item",
            "suggested_credit": round(line_total, 2),
            "evidence": f"Charged for {suggestion['quantity']} units but item not delivered"
        })
        return suggestion
    else:
        return None

def _calculate_price_increase_credit(suggestion: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Calculate credit for significant price increase.
    
    Only suggest credit if increase is >20% above historical average.
    """
    current_price = suggestion["unit_price"]
    avg_price = suggestion["avg_price"]
    quantity = suggestion["quantity"]
    
    if avg_price > 0:
        increase_percentage = ((current_price - avg_price) / avg_price) * 100
        
        # Only suggest credit for significant increases (>20%)
        if increase_percentage > 20.0 and quantity > 0:
            # Suggest partial credit (50% of the increase)
            credit_amount = (current_price - avg_price) * quantity * 0.5
            suggestion.update({
                "reason": "Significant Price Increase",
                "suggested_credit": round(credit_amount, 2),
                "price_difference": round(current_price - avg_price, 2),
                "increase_percentage": round(increase_percentage, 1),
                "evidence": f"Price increased {increase_percentage:.1f}% above average (£{avg_price:.2f} → £{current_price:.2f})"
            })
            return suggestion
    
    return None

def _calculate_quantity_mismatch_credit(suggestion: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Calculate credit for quantity mismatch.
    
    Credit = unit_price * quantity_difference
    """
    unit_price = suggestion["unit_price"]
    quantity_diff = abs(suggestion.get("quantity_difference", 0))
    
    if quantity_diff > 0 and unit_price > 0:
        credit_amount = unit_price * quantity_diff
        suggestion.update({
            "reason": "Quantity Mismatch",
            "suggested_credit": round(credit_amount, 2),
            "quantity_difference": quantity_diff,
            "evidence": f"Quantity discrepancy of {quantity_diff} units at £{unit_price:.2f} each"
        })
        return suggestion
    
    return None

def get_credit_summary(credit_suggestions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a summary of credit suggestions.
    
    Args:
        credit_suggestions: List of credit suggestions
        
    Returns:
        Summary dictionary with totals and breakdowns
    """
    if not credit_suggestions:
        return {
            "total_suggested_credit": 0.0,
            "suggestion_count": 0,
            "high_confidence_count": 0,
            "medium_confidence_count": 0,
            "low_confidence_count": 0,
            "breakdown_by_reason": {},
            "breakdown_by_type": {}
        }
    
    total_credit = sum(s.get("suggested_credit", 0) for s in credit_suggestions)
    
    # Count by confidence level
    high_confidence = len([s for s in credit_suggestions if s.get("confidence", 0) >= 80])
    medium_confidence = len([s for s in credit_suggestions if 60 <= s.get("confidence", 0) < 80])
    low_confidence = len([s for s in credit_suggestions if s.get("confidence", 0) < 60])
    
    # Breakdown by reason
    reasons = {}
    for suggestion in credit_suggestions:
        reason = suggestion.get("reason", "Unknown")
        reasons[reason] = reasons.get(reason, 0) + 1
    
    # Breakdown by mismatch type
    types = {}
    for suggestion in credit_suggestions:
        mismatch_type = suggestion.get("mismatch_type", "Unknown")
        types[mismatch_type] = types.get(mismatch_type, 0) + 1
    
    return {
        "total_suggested_credit": round(total_credit, 2),
        "suggestion_count": len(credit_suggestions),
        "high_confidence_count": high_confidence,
        "medium_confidence_count": medium_confidence,
        "low_confidence_count": low_confidence,
        "breakdown_by_reason": reasons,
        "breakdown_by_type": types,
        "average_confidence": round(sum(s.get("confidence", 0) for s in credit_suggestions) / len(credit_suggestions), 1)
    }

def generate_credit_email_template(credit_suggestions: List[Dict[str, Any]], invoice_id: str) -> str:
    """
    Generate an email template for credit requests.
    
    Args:
        credit_suggestions: List of credit suggestions
        invoice_id: Invoice ID
        
    Returns:
        Formatted email template
    """
    if not credit_suggestions:
        return ""
    
    summary = get_credit_summary(credit_suggestions)
    
    email_template = f"""
Dear Supplier,

We have identified several discrepancies in invoice {invoice_id} that require your attention.

**Total Suggested Credit: £{summary['total_suggested_credit']:.2f}**

**Discrepancies Found:**

"""
    
    for i, suggestion in enumerate(credit_suggestions, 1):
        email_template += f"""
{i}. **{suggestion['item']}** - {suggestion['reason']}
   - Suggested Credit: £{suggestion['suggested_credit']:.2f}
   - Evidence: {suggestion['evidence']}
   - Confidence: {suggestion['confidence']:.1f}%

"""
    
    email_template += f"""
**Summary:**
- Total suggested credit: £{summary['total_suggested_credit']:.2f}
- Number of discrepancies: {summary['suggestion_count']}
- High confidence issues: {summary['high_confidence_count']}
- Medium confidence issues: {summary['medium_confidence_count']}

Please review these discrepancies and let us know if you agree with the suggested credits or if you need additional information.

Best regards,
Finance Team
"""
    
    return email_template

def validate_credit_suggestion(suggestion: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a credit suggestion and add validation flags.
    
    Args:
        suggestion: Credit suggestion dictionary
        
    Returns:
        Validated suggestion with additional flags
    """
    validation_result = {
        "is_valid": True,
        "warnings": [],
        "errors": []
    }
    
    # Check for required fields
    required_fields = ["item", "reason", "suggested_credit", "confidence"]
    for field in required_fields:
        if field not in suggestion:
            validation_result["errors"].append(f"Missing required field: {field}")
            validation_result["is_valid"] = False
    
    # Validate credit amount
    credit_amount = suggestion.get("suggested_credit", 0)
    if credit_amount <= 0:
        validation_result["warnings"].append("Credit amount is zero or negative")
    elif credit_amount > 1000:
        validation_result["warnings"].append("Credit amount is unusually high")
    
    # Validate confidence
    confidence = suggestion.get("confidence", 0)
    if confidence < 30:
        validation_result["warnings"].append("Low confidence in suggestion")
    elif confidence > 100:
        validation_result["errors"].append("Invalid confidence score")
        validation_result["is_valid"] = False
    
    # Validate quantity
    quantity = suggestion.get("quantity", 0)
    if quantity < 0:
        validation_result["errors"].append("Negative quantity")
        validation_result["is_valid"] = False
    
    return validation_result

def suggest_credit_for_invoice(invoice_id: str, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """
    Suggest credit amounts for an invoice based on detected mismatches.
    
    This is an alias for suggest_credits_for_invoice() to maintain API compatibility.
    
    Args:
        invoice_id: The ID of the invoice to analyze
        conn: SQLite database connection
        
    Returns:
        List of credit suggestions with details:
        [
            {
                "item": str,                    # Item name
                "issue": str,                   # Issue type (e.g., "Short Delivery", "Overcharge")
                "suggested_credit": float,      # Credit amount in GBP
                "reason": str,                  # Detailed reason for the credit
                "quantity": float,              # Quantity involved
                "unit_price": float,           # Current unit price
                "expected_price": float,       # Expected price (for overcharges)
                "expected_quantity": float,    # Expected quantity (for short deliveries)
                "received_quantity": float,    # Received quantity (for short deliveries)
                "confidence": float,           # Confidence in the suggestion (0-100)
                "evidence": str                # Supporting evidence for the credit
            }
        ]
    """
    # Get the base suggestions
    suggestions = suggest_credits_for_invoice(invoice_id, conn)
    
    # Transform to match the requested format
    transformed_suggestions = []
    
    for suggestion in suggestions:
        # Map the existing fields to the requested format
        transformed_suggestion = {
            "item": suggestion.get("item", ""),
            "issue": _map_issue_type(suggestion.get("reason", "")),
            "suggested_credit": suggestion.get("suggested_credit", 0.0),
            "reason": suggestion.get("evidence", ""),
            "quantity": suggestion.get("quantity", 0.0),
            "unit_price": suggestion.get("unit_price", 0.0),
            "expected_price": suggestion.get("avg_price", 0.0),
            "expected_quantity": _get_expected_quantity(suggestion),
            "received_quantity": suggestion.get("quantity", 0.0),
            "confidence": suggestion.get("confidence", 0.0),
            "evidence": suggestion.get("evidence", "")
        }
        
        transformed_suggestions.append(transformed_suggestion)
    
    return transformed_suggestions

def _map_issue_type(reason: str) -> str:
    """
    Map the internal reason to the requested issue type format.
    
    Args:
        reason: Internal reason string
        
    Returns:
        Mapped issue type string
    """
    mapping = {
        "Overcharged": "Overcharge",
        "Missing Item": "Short Delivery",
        "Significant Price Increase": "Overcharge",
        "Quantity Mismatch": "Short Delivery"
    }
    
    return mapping.get(reason, reason)

def _get_expected_quantity(suggestion: Dict[str, Any]) -> float:
    """
    Calculate expected quantity based on the suggestion type.
    
    Args:
        suggestion: Credit suggestion dictionary
        
    Returns:
        Expected quantity
    """
    mismatch_type = suggestion.get("mismatch_type", "")
    
    if mismatch_type == "missing_item":
        # For missing items, expected quantity is the charged quantity
        return suggestion.get("quantity", 0.0)
    elif mismatch_type == "quantity_mismatch":
        # For quantity mismatches, add the difference to received quantity
        received = suggestion.get("quantity", 0.0)
        difference = abs(suggestion.get("quantity_difference", 0.0))
        return received + difference
    else:
        # For other cases, use the charged quantity as expected
        return suggestion.get("quantity", 0.0)


if __name__ == "__main__":
    # Test the credit suggestion engine
    logging.basicConfig(level=logging.INFO)
    
    # Create test database connection
    import tempfile
    import os
    
    # Create temporary database for testing
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    
    try:
        conn = sqlite3.connect(temp_db.name)
        
        # Create test table
        conn.execute("""
            CREATE TABLE invoice_mismatches (
                id INTEGER PRIMARY KEY,
                invoice_id TEXT,
                item_name TEXT,
                mismatch_type TEXT,
                current_quantity REAL,
                current_unit_price REAL,
                current_line_total REAL,
                historical_avg_price REAL,
                historical_median_price REAL,
                price_difference REAL,
                quantity_difference REAL,
                confidence_score REAL,
                detection_timestamp TEXT,
                notes TEXT
            )
        """)
        
        # Insert test data
        test_mismatches = [
            ("INV-001", "Whole Milk", "overcharge", 20.0, 1.20, 24.00, 1.00, 1.00, 0.20, 0.0, 85.0, "2024-12-01", "Price 20% above average"),
            ("INV-001", "Beef Sirloin", "missing_item", 5.0, 25.00, 125.00, 22.00, 22.00, 0.0, 0.0, 90.0, "2024-12-01", "Item not delivered"),
            ("INV-001", "Chicken Breast", "price_increase", 10.0, 12.00, 120.00, 9.50, 9.50, 2.50, 0.0, 75.0, "2024-12-01", "Price increased 26%"),
        ]
        
        for mismatch in test_mismatches:
            conn.execute("""
                INSERT INTO invoice_mismatches (
                    invoice_id, item_name, mismatch_type, current_quantity,
                    current_unit_price, current_line_total, historical_avg_price,
                    historical_median_price, price_difference, quantity_difference,
                    confidence_score, detection_timestamp, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, mismatch)
        
        conn.commit()
        
        # Test credit suggestions
        suggestions = suggest_credits_for_invoice("INV-001", conn)
        
        print("🔍 Credit Suggestion Test Results:")
        print(f"Found {len(suggestions)} credit suggestions")
        
        for i, suggestion in enumerate(suggestions, 1):
            print(f"\n{i}. {suggestion['item']}")
            print(f"   Reason: {suggestion['reason']}")
            print(f"   Credit: £{suggestion['suggested_credit']:.2f}")
            print(f"   Confidence: {suggestion['confidence']:.1f}%")
            print(f"   Evidence: {suggestion['evidence']}")
        
        # Test the new function format
        new_suggestions = suggest_credit_for_invoice("INV-001", conn)
        print(f"\n🆕 New Format Test Results:")
        print(f"Found {len(new_suggestions)} credit suggestions")
        
        for i, suggestion in enumerate(new_suggestions, 1):
            print(f"\n{i}. {suggestion['item']}")
            print(f"   Issue: {suggestion['issue']}")
            print(f"   Credit: £{suggestion['suggested_credit']:.2f}")
            print(f"   Reason: {suggestion['reason']}")
            print(f"   Expected: {suggestion['expected_quantity']} units")
            print(f"   Received: {suggestion['received_quantity']} units")
            print(f"   Unit Price: £{suggestion['unit_price']:.2f}")
            print(f"   Expected Price: £{suggestion['expected_price']:.2f}")
        
        # Test summary
        summary = get_credit_summary(suggestions)
        print(f"\n📊 Summary:")
        print(f"   Total Credit: £{summary['total_suggested_credit']:.2f}")
        print(f"   Suggestions: {summary['suggestion_count']}")
        print(f"   High Confidence: {summary['high_confidence_count']}")
        
        # Test email template
        email = generate_credit_email_template(suggestions, "INV-001")
        print(f"\n📧 Email Template:")
        print(email)
        
        conn.close()
        
    finally:
        # Clean up
        os.unlink(temp_db.name)
        print("\n✅ Test completed successfully") 