#!/usr/bin/env python3
"""
Simple test for OCR debug functionality
"""

import requests
import json

def test_backend_health():
    """Test if backend is responding"""
    print("🔍 Testing backend health...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=10)
        if response.status_code == 200:
            print("✅ Backend is responding")
            return True
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend health check failed: {e}")
        return False

def test_invoices_endpoint():
    """Test if invoices endpoint returns data"""
    print("\n📄 Testing invoices endpoint...")
    try:
        response = requests.get("http://localhost:8000/api/invoices", timeout=10)
        if response.status_code == 200:
            invoices = response.json()
            print(f"✅ Found {len(invoices)} invoices")
            
            # Check if any invoice has OCR debug info
            debug_count = 0
            for invoice in invoices:
                if 'ocr_debug' in invoice:
                    debug_count += 1
                    print(f"✅ Invoice {invoice.get('id', 'unknown')} has OCR debug info")
            
            if debug_count > 0:
                print(f"✅ {debug_count} invoices have OCR debug information")
            else:
                print("⚠️ No existing invoices have OCR debug info (this is normal for old data)")
            
            return True
        else:
            print(f"❌ Invoices endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Invoices endpoint test failed: {e}")
        return False

def test_frontend_loading():
    """Test if frontend is loading"""
    print("\n🌐 Testing frontend...")
    try:
        response = requests.get("http://localhost:3000", timeout=10)
        if response.status_code == 200:
            print("✅ Frontend is loading")
            return True
        else:
            print(f"❌ Frontend failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Frontend test failed: {e}")
        return False

def main():
    """Run simple tests"""
    print("🧪 Simple OCR Debug Test")
    print("=" * 40)
    
    tests = [
        ("Backend Health", test_backend_health),
        ("Invoices Endpoint", test_invoices_endpoint),
        ("Frontend Loading", test_frontend_loading),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        print("-" * 20)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 40)
    print("📊 TEST RESULTS")
    print("=" * 40)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 SYSTEM IS READY FOR OCR DEBUG TESTING!")
        print("\n🚀 Next Steps:")
        print("   1. Go to http://localhost:3000/invoices")
        print("   2. Upload a document")
        print("   3. Click on the invoice card")
        print("   4. Look for '🔍 OCR Processing Debug' section")
        print("   5. Click 'Show Debug Info' to see processing details")
    else:
        print("⚠️ Some tests failed. Please check the logs above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 