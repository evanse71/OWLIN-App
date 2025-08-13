#!/usr/bin/env python3
"""
Test script for supplier summary generation logic.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.agent.utils.supplierSummaryGenerator import (
    generate_supplier_summary,
    get_supplier_invoices,
    get_flagged_items,
    analyze_common_issues,
    get_top_flagged_items,
    generate_summary_message,
    format_supplier_summary,
    SupplierSummary,
    InvoiceData,
    FlaggedItem
)

def test_supplier_invoice_retrieval():
    """Test supplier invoice retrieval."""
    print("🧪 Testing supplier invoice retrieval...")
    
    supplier_id = "SUP-001"
    date_range = {
        'from': '2025-07-01',
        'to': '2025-07-20'
    }
    
    invoices = get_supplier_invoices(supplier_id, date_range)
    
    print(f"📊 Retrieved {len(invoices)} invoices for supplier {supplier_id}")
    
    if invoices:
        print(f"   First invoice: {invoices[0].invoice_number}")
        print(f"   Date range: {invoices[0].invoice_date} to {invoices[-1].invoice_date}")
        print(f"   Total amount range: £{min(inv.total_amount for inv in invoices):.2f} - £{max(inv.total_amount for inv in invoices):.2f}")

def test_flagged_items_retrieval():
    """Test flagged items retrieval."""
    print("\n🧪 Testing flagged items retrieval...")
    
    supplier_id = "SUP-001"
    date_range = {
        'from': '2025-07-01',
        'to': '2025-07-20'
    }
    
    flagged_items = get_flagged_items(supplier_id, date_range)
    
    print(f"📊 Retrieved {len(flagged_items)} flagged items for supplier {supplier_id}")
    
    if flagged_items:
        print(f"   Date range: {flagged_items[0].invoice_date} to {flagged_items[-1].invoice_date}")
        
        # Count issue types
        issue_types = {}
        for item in flagged_items:
            issue_types[item.issue_type] = issue_types.get(item.issue_type, 0) + 1
        
        print(f"   Issue types: {issue_types}")
        
        # Show sample items
        print(f"   Sample items:")
        for item in flagged_items[:3]:
            print(f"     - {item.item_name}: {item.issue_type} (£{item.suggested_credit:.2f})")

def test_common_issues_analysis():
    """Test common issues analysis."""
    print("\n🧪 Testing common issues analysis...")
    
    # Create sample flagged items
    flagged_items = [
        FlaggedItem("1", "Toilet Roll 2ply", "INV-001", "2025-07-03", "missing", 5, 1.20, 6.00, "Missing items", 4.80),
        FlaggedItem("2", "House Red 12x750ml", "INV-002", "2025-07-05", "flagged", 2, 8.50, 17.00, "Price discrepancy", 3.40),
        FlaggedItem("3", "Beef Steaks", "INV-003", "2025-07-07", "mismatched", 3, 12.00, 36.00, "Quantity mismatch", 9.60),
        FlaggedItem("4", "Toilet Roll 2ply", "INV-004", "2025-07-10", "missing", 4, 1.20, 4.80, "Missing items", 3.84),
        FlaggedItem("5", "Chicken Breast", "INV-005", "2025-07-12", "flagged", 1, 6.50, 6.50, "Price discrepancy", 1.30)
    ]
    
    common_issues = analyze_common_issues(flagged_items)
    
    print(f"🛠 Common issues identified: {common_issues}")

def test_top_flagged_items():
    """Test top flagged items retrieval."""
    print("\n🧪 Testing top flagged items retrieval...")
    
    # Create sample flagged items
    flagged_items = [
        FlaggedItem("1", "Toilet Roll 2ply", "INV-001", "2025-07-03", "missing", 5, 1.20, 6.00, "Missing items", 4.80),
        FlaggedItem("2", "House Red 12x750ml", "INV-002", "2025-07-05", "flagged", 2, 8.50, 17.00, "Price discrepancy", 3.40),
        FlaggedItem("3", "Beef Steaks", "INV-003", "2025-07-07", "mismatched", 3, 12.00, 36.00, "Quantity mismatch", 9.60),
        FlaggedItem("4", "Toilet Roll 2ply", "INV-004", "2025-07-10", "missing", 4, 1.20, 4.80, "Missing items", 3.84),
        FlaggedItem("5", "Chicken Breast", "INV-005", "2025-07-12", "flagged", 1, 6.50, 6.50, "Price discrepancy", 1.30),
        FlaggedItem("6", "House Red 12x750ml", "INV-006", "2025-07-15", "flagged", 1, 8.50, 8.50, "Price discrepancy", 1.70)
    ]
    
    top_items = get_top_flagged_items(flagged_items, limit=3)
    
    print(f"🔥 Top flagged items: {top_items}")

def test_summary_message_generation():
    """Test summary message generation."""
    print("\n🧪 Testing summary message generation...")
    
    supplier_name = "Thomas Ridley"
    total_invoices = 28
    total_flagged_items = 13
    estimated_credit = 87.40
    date_range = {
        'from': '2025-07-01',
        'to': '2025-07-20'
    }
    common_issues = ['Missing items', 'Price discrepancies', 'Quantity mismatches']
    
    message = generate_summary_message(
        supplier_name,
        total_invoices,
        total_flagged_items,
        estimated_credit,
        date_range,
        common_issues
    )
    
    print(f"✏️ Generated summary message:")
    print(f"   {message}")

def test_full_supplier_summary():
    """Test full supplier summary generation."""
    print("\n🧪 Testing full supplier summary generation...")
    
    # Test data
    supplier_id = "SUP-001"
    supplier_name = "Thomas Ridley"
    date_range = {
        'from': '2025-07-01',
        'to': '2025-07-20'
    }
    
    summary = generate_supplier_summary(supplier_id, supplier_name, date_range)
    
    if summary:
        print(f"📦 Supplier: {summary.supplier_name}")
        print(f"🧾 Total Invoices: {summary.total_invoices}")
        print(f"⚠️ Flagged Issues: {summary.total_flagged_items} items")
        print(f"💸 Estimated Credit Due: £{summary.estimated_credit:.2f}")
        print(f"📅 Dates Affected: {len(summary.flagged_dates)} dates")
        
        print(f"\n🛠 Common Problems:")
        for issue in summary.common_issues:
            print(f"   - {issue}")
        
        print(f"\n🔥 Top Affected Items:")
        for item in summary.top_flagged_items:
            print(f"   - {item}")
        
        print(f"\n✏️ Summary Message:")
        print(f"   {summary.summary_message}")
        
        print(f"\n💰 Credit Breakdown (first 3):")
        for credit in summary.credit_breakdown[:3]:
            print(f"   - {credit['item_name']}: £{credit['suggested_credit']:.2f}")
        
        # Test formatting
        formatted = format_supplier_summary(summary)
        print(f"\n📋 Formatted for frontend:")
        print(f"   Keys: {list(formatted.keys())}")
    else:
        print("❌ No summary generated")

def test_multiple_suppliers():
    """Test summary generation for multiple suppliers."""
    print("\n🧪 Testing multiple suppliers...")
    
    suppliers = [
        ("SUP-001", "Thomas Ridley"),
        ("SUP-002", "Fresh Produce Co"),
        ("SUP-003", "Quality Beverages"),
        ("SUP-004", "Reliable Suppliers Ltd")
    ]
    
    date_range = {
        'from': '2025-07-01',
        'to': '2025-07-20'
    }
    
    for supplier_id, supplier_name in suppliers:
        print(f"\n📊 Testing {supplier_name} ({supplier_id})...")
        summary = generate_supplier_summary(supplier_id, supplier_name, date_range)
        
        if summary:
            print(f"   ✅ Generated summary: {summary.total_flagged_items} flagged items, £{summary.estimated_credit:.2f} credit")
        else:
            print(f"   ❌ No summary generated")

def test_edge_cases():
    """Test edge cases."""
    print("\n🧪 Testing edge cases...")
    
    # Test with no data
    print("Testing with no data...")
    summary = generate_supplier_summary("SUP-EMPTY", "Empty Supplier", {
        'from': '2025-07-01',
        'to': '2025-07-20'
    })
    
    if summary is None:
        print("   ✅ Correctly handled no data case")
    else:
        print("   ❌ Should have returned None for no data")
    
    # Test with single invoice
    print("Testing with single invoice...")
    summary = generate_supplier_summary("SUP-SINGLE", "Single Invoice Supplier", {
        'from': '2025-07-01',
        'to': '2025-07-20'
    })
    
    if summary:
        print(f"   ✅ Generated summary with {summary.total_invoices} invoice(s)")

def main():
    """Run all supplier summary tests."""
    print("🚀 Starting supplier summary tests...\n")
    
    try:
        test_supplier_invoice_retrieval()
        test_flagged_items_retrieval()
        test_common_issues_analysis()
        test_top_flagged_items()
        test_summary_message_generation()
        test_full_supplier_summary()
        test_multiple_suppliers()
        test_edge_cases()
        
        print("\n✅ All supplier summary tests completed successfully!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main()) 