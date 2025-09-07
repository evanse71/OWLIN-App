#!/usr/bin/env python3
"""
Test script for agent escalation logic.
"""

import sys
import os
# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.agent.utils.agentSuggestEscalation import (
    check_supplier_escalation,
    should_escalate_supplier,
    get_supplier_metrics,
    SupplierMetrics
)

def test_escalation_thresholds():
    """Test the escalation threshold logic."""
    print("🧪 Testing escalation thresholds...")
    
    # Test case 1: High mismatch rate
    metrics1 = SupplierMetrics(
        supplier_id="SUP-001",
        supplier_name="Problem Supplier",
        mismatch_rate=35.0,
        avg_confidence=70.0,
        late_delivery_rate=20.0,
        flagged_issue_count=3,
        total_invoices=5,
        recent_issues=["Delivery mismatch", "Missing items"]
    )
    
    should_escalate, reason = should_escalate_supplier(metrics1)
    print(f"Case 1 - High mismatch rate: {should_escalate} - {reason}")
    
    # Test case 2: Low confidence
    metrics2 = SupplierMetrics(
        supplier_id="SUP-002",
        supplier_name="Low Confidence Supplier",
        mismatch_rate=15.0,
        avg_confidence=55.0,
        late_delivery_rate=25.0,
        flagged_issue_count=2,
        total_invoices=4,
        recent_issues=["Low confidence processing"]
    )
    
    should_escalate, reason = should_escalate_supplier(metrics2)
    print(f"Case 2 - Low confidence: {should_escalate} - {reason}")
    
    # Test case 3: High late delivery rate
    metrics3 = SupplierMetrics(
        supplier_id="SUP-003",
        supplier_name="Late Delivery Supplier",
        mismatch_rate=10.0,
        avg_confidence=80.0,
        late_delivery_rate=50.0,
        flagged_issue_count=1,
        total_invoices=3,
        recent_issues=["Late deliveries"]
    )
    
    should_escalate, reason = should_escalate_supplier(metrics3)
    print(f"Case 3 - High late delivery rate: {should_escalate} - {reason}")
    
    # Test case 4: Multiple flagged issues
    metrics4 = SupplierMetrics(
        supplier_id="SUP-004",
        supplier_name="Flagged Issues Supplier",
        mismatch_rate=20.0,
        avg_confidence=75.0,
        late_delivery_rate=15.0,
        flagged_issue_count=7,
        total_invoices=6,
        recent_issues=["Multiple price discrepancies", "Quality issues"]
    )
    
    should_escalate, reason = should_escalate_supplier(metrics4)
    print(f"Case 4 - Multiple flagged issues: {should_escalate} - {reason}")
    
    # Test case 5: Good supplier (no escalation)
    metrics5 = SupplierMetrics(
        supplier_id="SUP-005",
        supplier_name="Good Supplier",
        mismatch_rate=10.0,
        avg_confidence=85.0,
        late_delivery_rate=15.0,
        flagged_issue_count=2,
        total_invoices=8,
        recent_issues=[]
    )
    
    should_escalate, reason = should_escalate_supplier(metrics5)
    print(f"Case 5 - Good supplier: {should_escalate} - {reason}")

def test_supplier_escalation_check():
    """Test the full escalation check function."""
    print("\n🧪 Testing supplier escalation check...")
    
    test_suppliers = [
        ("SUP-001", "Tom's Meats"),
        ("SUP-002", "Fresh Produce Co"),
        ("SUP-003", "Quality Beverages"),
        ("SUP-004", "Reliable Suppliers Ltd"),
        ("SUP-005", "Problematic Foods Inc")
    ]
    
    for supplier_id, supplier_name in test_suppliers:
        escalation_data = check_supplier_escalation(supplier_id, supplier_name)
        
        if escalation_data:
            print(f"🚨 {supplier_name}: {escalation_data['reason']}")
            print(f"   Metrics: {escalation_data['metrics']}")
        else:
            print(f"✅ {supplier_name}: No escalation needed")

def test_edge_cases():
    """Test edge cases and boundary conditions."""
    print("\n🧪 Testing edge cases...")
    
    # Edge case 1: Just below threshold
    metrics1 = SupplierMetrics(
        supplier_id="SUP-EDGE-1",
        supplier_name="Edge Case Supplier 1",
        mismatch_rate=24.9,  # Just below 25%
        avg_confidence=60.1,  # Just above 60%
        late_delivery_rate=39.9,  # Just below 40%
        flagged_issue_count=4,  # Just below 5
        total_invoices=3,
        recent_issues=[]
    )
    
    should_escalate, reason = should_escalate_supplier(metrics1)
    print(f"Edge Case 1 - Just below thresholds: {should_escalate} - {reason}")
    
    # Edge case 2: Just above threshold
    metrics2 = SupplierMetrics(
        supplier_id="SUP-EDGE-2",
        supplier_name="Edge Case Supplier 2",
        mismatch_rate=25.1,  # Just above 25%
        avg_confidence=59.9,  # Just below 60%
        late_delivery_rate=40.1,  # Just above 40%
        flagged_issue_count=5,  # Just at 5
        total_invoices=3,
        recent_issues=["Issue detected"]
    )
    
    should_escalate, reason = should_escalate_supplier(metrics2)
    print(f"Edge Case 2 - Just above thresholds: {should_escalate} - {reason}")
    
    # Edge case 3: Insufficient invoices for mismatch check
    metrics3 = SupplierMetrics(
        supplier_id="SUP-EDGE-3",
        supplier_name="Edge Case Supplier 3",
        mismatch_rate=50.0,  # High mismatch rate
        avg_confidence=70.0,
        late_delivery_rate=20.0,
        flagged_issue_count=2,
        total_invoices=2,  # Less than 3 invoices
        recent_issues=[]
    )
    
    should_escalate, reason = should_escalate_supplier(metrics3)
    print(f"Edge Case 3 - Insufficient invoices: {should_escalate} - {reason}")

def main():
    """Run all escalation tests."""
    print("🚀 Starting escalation logic tests...\n")
    
    try:
        test_escalation_thresholds()
        test_supplier_escalation_check()
        test_edge_cases()
        
        print("\n✅ All escalation tests completed successfully!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main()) 