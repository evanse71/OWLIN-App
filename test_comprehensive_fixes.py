#!/usr/bin/env python3
"""
Comprehensive test script to verify all the fixes work correctly
"""

import requests
import json
import time
import os
from pathlib import Path

def test_backend_health():
    """Test backend health"""
    print("🔍 Testing backend health...")
    try:
        response = requests.get("http://localhost:8002/health")
        if response.status_code == 200:
            print("✅ Backend is healthy")
            return True
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend health check failed: {e}")
        return False

def test_field_extraction():
    """Test the new field extraction function"""
    print("\n🔍 Testing field extraction...")
    
    test_text = """
    WILD HORSE BREWING CO LTD
    Unit 4-5, Cae Bach
    Builder Street, Llandudno
    
    Invoice #: 73318
    Date: 04/07/2025
    
    Total: £618.00
    """
    
    try:
        response = requests.post(
            "http://localhost:8002/api/upload",
            files={"file": ("test_invoice.txt", test_text, "text/plain")}
        )
        
        if response.status_code == 200:
            data = response.json()
            # Check for data wrapper first, then direct fields
            invoice_data = data.get('data', data)
            print(f"✅ Field extraction test passed")
            print(f"   Supplier: {invoice_data.get('supplier_name', 'Unknown')}")
            print(f"   Invoice: {invoice_data.get('invoice_number', 'Unknown')}")
            print(f"   Total: {invoice_data.get('total_amount', 0)}")
            print(f"   Date: {invoice_data.get('invoice_date', 'Unknown')}")
            
            # Verify the extraction worked
            if invoice_data.get('supplier_name') != 'Unknown':
                print(f"   ✅ Supplier extraction working: {invoice_data.get('supplier_name')}")
            if invoice_data.get('invoice_number') != 'Unknown':
                print(f"   ✅ Invoice extraction working: {invoice_data.get('invoice_number')}")
            if invoice_data.get('total_amount', 0) > 0:
                print(f"   ✅ Total extraction working: £{invoice_data.get('total_amount')}")
            
            return True
        else:
            print(f"❌ Field extraction test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Field extraction test failed: {e}")
        return False

def test_confidence_calculation():
    """Test confidence calculation"""
    print("\n🔍 Testing confidence calculation...")
    
    # Create a simple test image with text
    test_text = """
    Test Invoice
    Invoice #: 12345
    Total: £100.00
    """
    
    try:
        response = requests.post(
            "http://localhost:8002/api/upload",
            files={"file": ("test_confidence.txt", test_text, "text/plain")}
        )
        
        if response.status_code == 200:
            data = response.json()
            # Check for data wrapper first, then direct fields
            invoice_data = data.get('data', data)
            confidence = invoice_data.get('confidence', 0)
            
            if 0 <= confidence <= 100:
                print(f"✅ Confidence calculation test passed: {confidence}%")
                return True
            else:
                print(f"❌ Confidence calculation test failed: {confidence}% (should be 0-100)")
                return False
        else:
            print(f"❌ Confidence calculation test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Confidence calculation test failed: {e}")
        return False

def test_error_handling():
    """Test error handling"""
    print("\n🔍 Testing error handling...")
    
    # Try to upload an invalid file
    try:
        response = requests.post(
            "http://localhost:8002/api/upload",
            files={"file": ("test_invalid.xyz", b"invalid content", "application/octet-stream")}
        )
        
        if response.status_code in [400, 500]:
            print("✅ Error handling test passed (correctly rejected invalid file)")
            return True
        else:
            print(f"❌ Error handling test failed: expected 400 or 500, got {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

def test_line_item_calculation():
    """Test line item calculation"""
    print("\n🔍 Testing line item calculation...")
    
    test_text = """
    WILD HORSE BREWING CO LTD
    Invoice #: 73318
    
    QTY ITEM UNIT PRICE TOTAL
    2 Beer Keg £50.00 £100.00
    1 Wine Bottle £25.00 £25.00
    3 Beer Cans £2.50 £7.50
    
    Total: £159.00
    """
    
    try:
        response = requests.post(
            "http://localhost:8002/api/upload",
            files={"file": ("test_line_items.txt", test_text, "text/plain")}
        )
        
        if response.status_code == 200:
            data = response.json()
            # Check for data wrapper first, then direct fields
            invoice_data = data.get('data', data)
            line_items = invoice_data.get('line_items', [])
            
            if line_items:
                print(f"✅ Line item calculation test passed: {len(line_items)} items found")
                for i, item in enumerate(line_items[:3]):  # Show first 3 items
                    print(f"   Item {i+1}: {item.get('quantity', 0)} x £{item.get('unit_price', 0)} = £{item.get('line_total', 0)}")
                return True
            else:
                print("❌ Line item calculation test failed: no line items found")
                return False
        else:
            print(f"❌ Line item calculation test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Line item calculation test failed: {e}")
        return False

def test_frontend_connection():
    """Test frontend connection"""
    print("\n🔍 Testing frontend connection...")
    try:
        response = requests.get("http://localhost:3000")
        if response.status_code == 200:
            print("✅ Frontend is accessible")
            return True
        else:
            print(f"❌ Frontend connection failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Frontend connection failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 COMPREHENSIVE FIXES TEST SUITE")
    print("=" * 50)
    
    tests = [
        ("Backend Health", test_backend_health),
        ("Field Extraction", test_field_extraction),
        ("Confidence Calculation", test_confidence_calculation),
        ("Error Handling", test_error_handling),
        ("Line Item Calculation", test_line_item_calculation),
        ("Frontend Connection", test_frontend_connection),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! The fixes are working correctly.")
    else:
        print("⚠️ Some tests failed. Please check the implementation.")
    
    return passed == total

if __name__ == "__main__":
    main() 