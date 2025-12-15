#!/usr/bin/env python3
"""
Backend API Contract Test
Tests that /api/invoices returns the normalized keys as expected by the frontend.
"""
import requests
import json
import sys
from typing import Dict, Any

def test_invoices_api_contract():
    """Test that /api/invoices returns the expected contract"""
    try:
        # Test the invoices endpoint
        response = requests.get('http://127.0.0.1:8000/api/invoices')
        
        if response.status_code != 200:
            print(f"❌ API returned status {response.status_code}")
            return False
            
        data = response.json()
        
        # Check required top-level keys
        required_keys = ['invoices', 'count', 'total', 'limit', 'offset']
        for key in required_keys:
            if key not in data:
                print(f"❌ Missing required key: {key}")
                return False
        
        # Check that invoices is a list
        if not isinstance(data['invoices'], list):
            print(f"❌ 'invoices' should be a list, got {type(data['invoices'])}")
            return False
        
        # If there are invoices, check the structure
        if data['invoices']:
            invoice = data['invoices'][0]
            
            # Check required invoice keys
            required_invoice_keys = [
                'id', 'filename', 'supplier', 'date', 'total_value', 
                'status', 'confidence', 'venue', 'issues_count', 'paired'
            ]
            
            for key in required_invoice_keys:
                if key not in invoice:
                    print(f"❌ Missing required invoice key: {key}")
                    return False
            
            # Check confidence is between 0 and 1
            confidence = invoice.get('confidence', 0)
            if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 1):
                print(f"❌ Confidence should be between 0-1, got {confidence}")
                return False
            
            # Check status is a string
            status = invoice.get('status', '')
            if not isinstance(status, str):
                print(f"❌ Status should be a string, got {type(status)}")
                return False
            
            # Check total_value is a number
            total_value = invoice.get('total_value', 0)
            if not isinstance(total_value, (int, float)):
                print(f"❌ Total value should be a number, got {type(total_value)}")
                return False
        
        print("✅ API contract test passed")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server. Make sure it's running on port 8000")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

def test_health_details_api():
    """Test that /api/health/details returns the expected structure"""
    try:
        response = requests.get('http://127.0.0.1:8000/api/health/details')
        
        if response.status_code != 200:
            print(f"❌ Health details API returned status {response.status_code}")
            return False
            
        data = response.json()
        
        # Check required keys
        required_keys = ['status', 'db_path_abs']
        for key in required_keys:
            if key not in data:
                print(f"❌ Missing required health key: {key}")
                return False
        
        # Check db_path_abs is a string and looks like a path
        db_path = data.get('db_path_abs', '')
        if not isinstance(db_path, str) or not db_path:
            print(f"❌ db_path_abs should be a non-empty string, got {db_path}")
            return False
        
        print("✅ Health details API test passed")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server. Make sure it's running on port 8000")
        return False
    except Exception as e:
        print(f"❌ Health details test failed with error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Running API contract tests...")
    
    tests = [
        test_invoices_api_contract,
        test_health_details_api
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing between tests
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("💥 Some tests failed!")
        sys.exit(1)
