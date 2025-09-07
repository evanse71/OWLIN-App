#!/usr/bin/env python3
"""
Quick test to verify the invoice API is working
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_basic_imports():
    """Test that basic imports work"""
    try:
        from services.invoice_query import fetch_invoice  # type: ignore
        print("✅ invoice_query import OK")
        
        from db_manager_unified import get_db_manager  # type: ignore
        print("✅ db_manager_unified import OK")
        
        from test_server import app  # type: ignore
        print("✅ test_server import OK")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_database_connection():
    """Test database connection"""
    try:
        from db_manager_unified import get_db_manager
        db_manager = get_db_manager()
        
        # Test connection
        conn = db_manager.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        if result and result[0] == 1:
            print("✅ Database connection OK")
            return True
        else:
            print("❌ Database connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_fetch_invoice_function():
    """Test the fetch_invoice function"""
    try:
        from services.invoice_query import fetch_invoice
        
        # Test with a non-existent ID first
        result = fetch_invoice("non_existent_id")
        if result is None:
            print("✅ fetch_invoice returns None for non-existent ID (expected)")
        else:
            print("⚠️ fetch_invoice returned data for non-existent ID")
        
        return True
        
    except Exception as e:
        print(f"❌ fetch_invoice test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Quick Invoice API Test")
    print("=" * 30)
    
    tests = [
        ("Basic Imports", test_basic_imports),
        ("Database Connection", test_database_connection),
        ("Fetch Invoice Function", test_fetch_invoice_function),
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
        print("🎉 All tests passed! The invoice API should be working.")
        print("\nNext steps:")
        print("1. Run: python3 seed_test_data.py")
        print("2. Run: python3 test_server.py")
        print("3. Test with: curl http://localhost:8000/api/invoices/inv_seed_001")
    else:
        print("💥 Some tests failed. Check the errors above.") 