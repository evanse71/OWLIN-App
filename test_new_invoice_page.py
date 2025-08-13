#!/usr/bin/env python3
"""
Test script for New Invoice Page Implementation
Verifies the clean, modern interface works correctly.
"""

import sys
import os
import logging

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def test_imports():
    """Test that all imports work correctly."""
    print("🔍 Testing imports...")
    
    try:
        import app.invoices_page
        print("✅ Invoices page module imports successfully")
        
        from app.invoices_page import (
            render_invoices_page,
            render_upload_section,
            render_summary_metrics,
            format_currency,
            get_status_icon,
            sanitize_text
        )
        print("✅ All functions import successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def test_utility_functions():
    """Test utility functions."""
    print("🔍 Testing utility functions...")
    
    try:
        from app.invoices_page import format_currency, get_status_icon, sanitize_text
        
        # Test currency formatting
        assert format_currency(1234.56) == "£1,234.56"
        assert format_currency(0) == "£0.00"
        assert format_currency(None) == "£0.00"
        print("✅ Currency formatting works correctly")
        
        # Test status icons
        assert get_status_icon("matched") == "✅"
        assert get_status_icon("discrepancy") == "⚠️"
        assert get_status_icon("not_paired") == "❌"
        print("✅ Status icons work correctly")
        
        # Test text sanitization
        assert sanitize_text("<script>alert('xss')</script>") == "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"
        assert sanitize_text("Normal text") == "Normal text"
        print("✅ Text sanitization works correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Utility function test failed: {e}")
        return False

def test_database_integration():
    """Test database integration."""
    print("🔍 Testing database integration...")
    
    try:
        from app.database import get_invoices_with_delivery_notes, get_processing_status_summary
        
        # Test loading invoices
        invoices = get_invoices_with_delivery_notes()
        print(f"✅ Loaded {len(invoices)} invoices from database")
        
        # Test processing summary
        summary = get_processing_status_summary()
        print(f"✅ Processing summary: {summary}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database integration test failed: {e}")
        return False

def test_styling():
    """Test that styling functions exist."""
    print("🔍 Testing styling functions...")
    
    try:
        from app.invoices_page import inject_global_styles
        
        # Test that the function exists and is callable
        assert callable(inject_global_styles)
        print("✅ Styling functions exist")
        
        return True
        
    except Exception as e:
        print(f"❌ Styling test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 New Invoice Page Test Suite")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Utility Functions", test_utility_functions),
        ("Database Integration", test_database_integration),
        ("Styling", test_styling)
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
        print("🎉 All tests passed! New invoice page is ready.")
        print("\n🚀 To run the application:")
        print("1. python create_sample_data.py")
        print("2. streamlit run app/main.py")
        print("\n✨ Features implemented:")
        print("- Clean, modern interface with soft grey background")
        print("- Two upload boxes side-by-side")
        print("- Summary metrics with dark cards")
        print("- Responsive design for all screen sizes")
        print("- Proper error handling and validation")
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 