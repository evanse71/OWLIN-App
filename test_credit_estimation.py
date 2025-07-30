#!/usr/bin/env python3
"""
Test script for agent credit estimation logic.
"""

import sys
import os
# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.agent.utils.agentCreditEstimator import (
    suggest_credit_for_line_item,
    suggest_credits_for_invoice,
    get_price_history,
    get_average_price_across_suppliers,
    calculate_quantity_delta,
    get_confidence_label,
    format_credit_suggestion,
    LineItem,
    PriceHistory
)

def test_quantity_delta_calculation():
    """Test the quantity delta calculation logic."""
    print("🧪 Testing quantity delta calculation...")
    
    # Test case 1: Missing item
    item1 = LineItem(
        id="1",
        name="Toilet Roll 2ply",
        quantity=10,
        unit_price=1.20,
        total=12.00,
        status="missing",
        vat_rate=0.20
    )
    delta1 = calculate_quantity_delta(item1)
    print(f"Case 1 - Missing item: {delta1} (expected: -10)")
    assert delta1 == -10, f"Expected -10 for missing item, got {delta1}"
    
    # Test case 2: Quantity mismatch
    item2 = LineItem(
        id="2",
        name="Chicken Breast",
        quantity=5,
        unit_price=4.20,
        total=21.00,
        status="mismatched",
        expected_quantity=5,
        actual_quantity=3,
        vat_rate=0.20
    )
    delta2 = calculate_quantity_delta(item2)
    print(f"Case 2 - Quantity mismatch: {delta2} (expected: 2)")
    assert delta2 == 2, f"Expected 2 for quantity mismatch, got {delta2}"
    
    # Test case 3: Flagged item (price discrepancy)
    item3 = LineItem(
        id="3",
        name="Beef Steaks",
        quantity=5,
        unit_price=8.50,
        total=42.50,
        status="flagged",
        vat_rate=0.20
    )
    delta3 = calculate_quantity_delta(item3)
    print(f"Case 3 - Flagged item: {delta3} (expected: 1)")
    assert delta3 == 1, f"Expected 1 for flagged item, got {delta3}"
    
    # Test case 4: Normal item
    item4 = LineItem(
        id="4",
        name="Onions",
        quantity=5,
        unit_price=1.20,
        total=6.00,
        status="normal",
        vat_rate=0.20
    )
    delta4 = calculate_quantity_delta(item4)
    print(f"Case 4 - Normal item: {delta4} (expected: 0)")
    assert delta4 == 0, f"Expected 0 for normal item, got {delta4}"
    
    # Test case 5: Overcharged item
    item5 = LineItem(
        id="5",
        name="Olive Oil",
        quantity=3,
        unit_price=7.00,
        total=21.00,
        status="overcharged",
        vat_rate=0.20
    )
    delta5 = calculate_quantity_delta(item5)
    print(f"Case 5 - Overcharged item: {delta5} (expected: 1)")
    assert delta5 == 1, f"Expected 1 for overcharged item, got {delta5}"

def test_price_history_retrieval():
    """Test price history retrieval."""
    print("\n🧪 Testing price history retrieval...")
    
    test_items = [
        "Toilet Roll 2ply",
        "Beef Steaks",
        "Chicken Breast",
        "Olive Oil"
    ]
    
    for item_name in test_items:
        history = get_price_history(item_name)
        print(f"📊 {item_name}: {len(history)} price records")
        
        if history:
            latest_price = history[0].unit_price
            print(f"   Latest price: £{latest_price:.2f}")
            print(f"   Supplier: {history[0].supplier_name}")
            
            # Verify price history structure
            assert hasattr(history[0], 'item_name'), "Price history should have item_name"
            assert hasattr(history[0], 'unit_price'), "Price history should have unit_price"
            assert hasattr(history[0], 'supplier_name'), "Price history should have supplier_name"
            assert hasattr(history[0], 'date'), "Price history should have date"
        else:
            print(f"   ⚠️ No price history found for {item_name}")

def test_average_price_retrieval():
    """Test average price retrieval."""
    print("\n🧪 Testing average price retrieval...")
    
    test_items = [
        "Toilet Roll 2ply",
        "Beef Steaks",
        "Chicken Breast",
        "Olive Oil"
    ]
    
    for item_name in test_items:
        avg_price = get_average_price_across_suppliers(item_name)
        if avg_price:
            print(f"📊 {item_name}: £{avg_price:.2f} (average across suppliers)")
            assert avg_price > 0, f"Average price should be positive, got {avg_price}"
        else:
            print(f"   ⚠️ No average price found for {item_name}")

def test_credit_suggestion_logic():
    """Test the credit suggestion logic."""
    print("\n🧪 Testing credit suggestion logic...")
    
    # Sample line items with issues
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
        ),
        LineItem(
            id="4",
            name="Olive Oil",
            quantity=3,
            unit_price=7.00,
            total=21.00,
            status="normal",
            vat_rate=0.20,
            notes="No issues"
        )
    ]
    
    suggestions = suggest_credits_for_invoice(line_items)
    
    print(f"💰 Generated {len(suggestions)} credit suggestions:")
    
    # Verify we got suggestions for flagged items only
    expected_suggestions = 3  # missing, flagged, mismatched
    assert len(suggestions) == expected_suggestions, f"Expected {expected_suggestions} suggestions, got {len(suggestions)}"
    
    for suggestion in suggestions:
        print(f"\n📦 {suggestion.item_name}")
        print(f"   Credit: £{suggestion.suggested_credit:.2f}")
        print(f"   Confidence: {suggestion.confidence}% ({get_confidence_label(suggestion.confidence)})")
        print(f"   Reason: {suggestion.reason}")
        print(f"   Price source: {suggestion.price_source}")
        print(f"   Base price: £{suggestion.base_price:.2f}")
        print(f"   Quantity delta: {suggestion.quantity_delta}")
        print(f"   VAT amount: £{suggestion.vat_amount:.2f}")
        
        # Verify suggestion structure
        assert suggestion.suggested_credit > 0, f"Credit should be positive, got {suggestion.suggested_credit}"
        assert 0 <= suggestion.confidence <= 100, f"Confidence should be 0-100, got {suggestion.confidence}"
        assert suggestion.base_price > 0, f"Base price should be positive, got {suggestion.base_price}"
        assert suggestion.vat_amount >= 0, f"VAT amount should be non-negative, got {suggestion.vat_amount}"

def test_confidence_labels():
    """Test confidence label generation."""
    print("\n🧪 Testing confidence labels...")
    
    test_confidences = [95, 75, 55, 30]
    expected_labels = ["High confidence", "Likely accurate", "Check manually", "Check manually"]
    
    for confidence, expected_label in zip(test_confidences, expected_labels):
        label = get_confidence_label(confidence)
        print(f"Confidence {confidence}%: {label}")
        assert label == expected_label, f"Expected '{expected_label}', got '{label}' for confidence {confidence}%"

def test_formatting():
    """Test credit suggestion formatting."""
    print("\n🧪 Testing credit suggestion formatting...")
    
    # Create a sample suggestion
    from backend.agent.utils.agentCreditEstimator import CreditSuggestion
    
    suggestion = CreditSuggestion(
        suggested_credit=4.80,
        confidence=85,
        reason="Based on unit price of £1.20 x 4 missing units (incl. VAT)",
        base_price=1.20,
        quantity_delta=-4,
        vat_amount=0.80,
        price_source="Recent price from Supplier 123",
        item_name="Toilet Roll 2ply"
    )
    
    formatted = format_credit_suggestion(suggestion)
    print("Formatted credit suggestion:")
    for key, value in formatted.items():
        print(f"  {key}: {value}")
    
    # Verify all required fields are present
    required_fields = [
        'suggested_credit', 'confidence', 'confidence_label', 'reason',
        'base_price', 'quantity_delta', 'vat_amount', 'price_source', 'item_name'
    ]
    
    for field in required_fields:
        assert field in formatted, f"Missing required field: {field}"
        assert formatted[field] is not None, f"Field {field} should not be None"

def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n🧪 Testing edge cases...")
    
    # Test 1: Line item with no issues
    normal_item = LineItem(
        id="normal",
        name="Normal Item",
        quantity=5,
        unit_price=2.00,
        total=10.00,
        status="normal",
        vat_rate=0.20
    )
    
    suggestion = suggest_credit_for_line_item(normal_item, [])
    print(f"Case 1 - Normal item: {suggestion}")
    assert suggestion is None, f"Expected None for normal item, got {suggestion}"
    
    # Test 2: Line item with zero quantity
    zero_item = LineItem(
        id="zero",
        name="Zero Item",
        quantity=0,
        unit_price=5.00,
        total=0.00,
        status="missing",
        vat_rate=0.20
    )
    
    suggestion = suggest_credit_for_line_item(zero_item, [])
    print(f"Case 2 - Zero quantity: {suggestion}")
    # Should still generate a suggestion for missing item
    
    # Test 3: Line item with negative price
    negative_item = LineItem(
        id="negative",
        name="Negative Price",
        quantity=3,
        unit_price=-1.00,
        total=-3.00,
        status="flagged",
        vat_rate=0.20
    )
    
    suggestion = suggest_credit_for_line_item(negative_item, [])
    print(f"Case 3 - Negative price: {suggestion}")
    # Should handle gracefully

def test_realistic_scenarios():
    """Test realistic credit estimation scenarios."""
    print("\n🧪 Testing realistic scenarios...")
    
    # Scenario 1: Restaurant missing ingredients
    restaurant_items = [
        LineItem(
            id="tomatoes",
            name="Fresh Tomatoes",
            quantity=20,
            unit_price=0.80,
            total=16.00,
            status="missing",
            expected_quantity=20,
            actual_quantity=0,
            vat_rate=0.20,
            notes="No tomatoes delivered"
        ),
        LineItem(
            id="beef",
            name="Beef Steaks",
            quantity=10,
            unit_price=12.50,
            total=125.00,
            status="mismatched",
            expected_quantity=10,
            actual_quantity=8,
            vat_rate=0.20,
            notes="Only 8 steaks received"
        )
    ]
    
    suggestions = suggest_credits_for_invoice(restaurant_items)
    print(f"\n🍽️ Restaurant scenario: {len(suggestions)} credit suggestions")
    
    total_credit = sum(s.suggested_credit for s in suggestions)
    print(f"   Total estimated credit: £{total_credit:.2f}")
    
    # Scenario 2: Office supplies overcharge
    office_items = [
        LineItem(
            id="paper",
            name="A4 Paper",
            quantity=50,
            unit_price=5.00,
            total=250.00,
            status="flagged",
            vat_rate=0.20,
            notes="Price 25% higher than usual"
        )
    ]
    
    suggestions = suggest_credits_for_invoice(office_items)
    print(f"\n📄 Office supplies scenario: {len(suggestions)} credit suggestions")
    
    for suggestion in suggestions:
        print(f"   {suggestion.item_name}: £{suggestion.suggested_credit:.2f}")

def main():
    """Run all credit estimation tests."""
    print("🚀 Starting credit estimation tests...\n")
    
    try:
        test_quantity_delta_calculation()
        test_price_history_retrieval()
        test_average_price_retrieval()
        test_credit_suggestion_logic()
        test_confidence_labels()
        test_formatting()
        test_edge_cases()
        test_realistic_scenarios()
        
        print("\n✅ All credit estimation tests completed successfully!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main()) 