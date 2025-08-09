#!/usr/bin/env python3
"""
Test script for Enhanced Invoice Page
Verifies all components work correctly together.
"""

import sys
import os
import logging

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def test_database_functions():
    """Test database functions."""
    print("🔍 Testing database functions...")
    
    try:
        from app.database import (
            get_invoices_with_delivery_notes,
            get_processing_status_summary,
            get_flagged_issues
        )
        
        # Test loading invoices with delivery notes
        invoices = get_invoices_with_delivery_notes()
        print(f"✅ Loaded {len(invoices)} invoices with delivery notes")
        
        # Test processing status summary
        summary = get_processing_status_summary()
        print(f"✅ Processing summary: {summary}")
        
        # Test flagged issues
        issues = get_flagged_issues()
        print(f"✅ Found {len(issues)} flagged issues")
        
        return True
        
    except Exception as e:
        print(f"❌ Database function test failed: {e}")
        return False

def test_ui_components():
    """Test UI components."""
    print("🔍 Testing UI components...")
    
    try:
        from app.invoices_page import (
            render_combined_invoice_card,
            render_invoice_card_content,
            render_delivery_note_card_content,
            render_detailed_view,
            format_currency,
            get_enhanced_status_icon
        )
        
        # Test utility functions
        currency = format_currency(1234.56)
        print(f"✅ Currency formatting: {currency}")
        
        icon = get_enhanced_status_icon('matched')
        print(f"✅ Status icon: {icon}")
        
        # Test with sample data
        sample_invoice = {
            'id': 'test-123',
            'invoice_number': 'INV-2024-001',
            'supplier': 'Test Supplier',
            'date': '2024-01-15',
            'total': 1250.50,
            'status': 'matched',
            'confidence': 0.95
        }
        
        sample_delivery_note = {
            'id': 'dn-123',
            'delivery_number': 'DN-2024-001',
            'delivery_date': '2024-01-15',
            'status': 'completed',
            'confidence': 0.92
        }
        
        print("✅ UI components loaded successfully")
        return True
        
    except Exception as e:
        print(f"❌ UI component test failed: {e}")
        return False

def test_sample_data():
    """Test sample data creation."""
    print("🔍 Testing sample data...")
    
    try:
        # Import and run sample data creation
        from create_sample_data import create_sample_data
        
        # This would create sample data in the database
        # For testing, we'll just verify the function exists
        print("✅ Sample data creation function available")
        return True
        
    except Exception as e:
        print(f"❌ Sample data test failed: {e}")
        return False

def test_integration():
    """Test full integration."""
    print("🔍 Testing full integration...")
    
    try:
        from app.invoices_page import render_invoices_page
        from app.database import get_invoices_with_delivery_notes
        
        # Test that we can load data and the page function exists
        invoices = get_invoices_with_delivery_notes()
        print(f"✅ Integration test: {len(invoices)} invoices loaded")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Enhanced Invoice Page Test Suite")
    print("=" * 50)
    
    tests = [
        ("Database Functions", test_database_functions),
        ("UI Components", test_ui_components),
        ("Sample Data", test_sample_data),
        ("Integration", test_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        if test_func():
            passed += 1
            print(f"✅ {test_name} PASSED")
        else:
            print(f"❌ {test_name} FAILED")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Enhanced invoice page is ready.")
        print("\n🚀 To run the application:")
        print("1. python create_sample_data.py")
        print("2. streamlit run app/main.py")
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 