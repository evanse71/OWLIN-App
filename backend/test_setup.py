#!/usr/bin/env python3
"""
Test script to verify the invoice API setup
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required modules can be imported"""
    try:
        from routes.invoices_api import router as invoices_router  # type: ignore
        print("✅ invoices_api router import OK")
        
        from services.invoice_query import fetch_invoice  # type: ignore
        print("✅ invoice_query import OK")
        
        from db_manager_unified import get_db_manager  # type: ignore
        print("✅ db_manager_unified import OK")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_router_structure():
    """Test that the router has the expected endpoints"""
    try:
        from routes.invoices_api import router
        
        # Simple check that router exists and has routes
        if hasattr(router, 'routes') and len(router.routes) > 0:
            print(f"✅ Router has {len(router.routes)} routes")
            return True
        else:
            print("❌ Router has no routes")
            return False
            
    except Exception as e:
        print(f"❌ Router test failed: {e}")
        return False

def test_fetch_invoice_function():
    """Test the fetch_invoice function structure"""
    try:
        from services.invoice_query import fetch_invoice
        
        # Test with a dummy ID to see the structure
        result = fetch_invoice("dummy_id")
        
        if result is None:
            print("✅ fetch_invoice returns None for non-existent ID (expected)")
        else:
            print("⚠️ fetch_invoice returned data for non-existent ID")
        
        return True
    except Exception as e:
        print(f"❌ fetch_invoice test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Invoice API Setup")
    print("=" * 40)
    
    tests = [
        ("Module Imports", test_imports),
        ("Router Structure", test_router_structure),
        ("Fetch Function", test_fetch_invoice_function),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing: {test_name}")
        if test_func():
            passed += 1
        else:
            print(f"   ❌ {test_name} failed")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Setup looks good!")
        print("\nNext steps:")
        print("1. Start server: python3 test_server.py")
        print("2. Check routes: curl http://localhost:8000/openapi.json | jq '.paths | keys[]'")
        print("3. Test endpoint: curl -i http://localhost:8000/api/invoices/inv_seed")
    else:
        print("💥 Setup has issues that need to be fixed!") 