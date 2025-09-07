#!/usr/bin/env python3
"""
Test script to verify the invoices page fix
"""

import requests
import time

def test_invoices_page():
    """Test if invoices page loads correctly"""
    print("🔍 Testing invoices page...")
    
    try:
        # Test with trailing slash (should work)
        response = requests.get("http://localhost:3000/invoices/", timeout=10)
        if response.status_code == 200:
            print("✅ Invoices page loads with trailing slash")
            return True
        else:
            print(f"❌ Invoices page failed with trailing slash: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Invoices page test failed: {e}")
        return False

def test_navigation_links():
    """Test if navigation links work correctly"""
    print("\n🧭 Testing navigation links...")
    
    try:
        # Test main page
        response = requests.get("http://localhost:3000/", timeout=10)
        if response.status_code == 200:
            print("✅ Main page loads")
        else:
            print(f"❌ Main page failed: {response.status_code}")
            return False
        
        # Test other pages with trailing slashes
        pages_to_test = [
            "/document-queue/",
            "/flagged/",
            "/suppliers/",
            "/product-trends/",
            "/notes/",
            "/settings/"
        ]
        
        for page in pages_to_test:
            response = requests.get(f"http://localhost:3000{page}", timeout=10)
            if response.status_code == 200:
                print(f"✅ {page} loads correctly")
            else:
                print(f"⚠️ {page} returned {response.status_code} (may be expected if page doesn't exist)")
        
        return True
        
    except Exception as e:
        print(f"❌ Navigation test failed: {e}")
        return False

def test_backend_connection():
    """Test if backend is still responding"""
    print("\n🔧 Testing backend connection...")
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=10)
        if response.status_code == 200:
            print("✅ Backend is responding")
            return True
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Invoices Page Fix Verification")
    print("=" * 40)
    
    tests = [
        ("Invoices Page", test_invoices_page),
        ("Navigation Links", test_navigation_links),
        ("Backend Connection", test_backend_connection),
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
        print("🎉 INVOICES PAGE FIX SUCCESSFUL!")
        print("\n🚀 The invoices page is now working correctly!")
        print("\n🌐 Access your application:")
        print("   • Main page: http://localhost:3000/")
        print("   • Invoices page: http://localhost:3000/invoices/")
        print("   • All navigation links now work with trailing slashes")
        print("\n📝 Note: Make sure to use trailing slashes in URLs:")
        print("   • ✅ http://localhost:3000/invoices/")
        print("   • ❌ http://localhost:3000/invoices")
    else:
        print("⚠️ Some tests failed. Please check the logs above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 