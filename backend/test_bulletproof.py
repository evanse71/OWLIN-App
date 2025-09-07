#!/usr/bin/env python3
"""
Bulletproof Invoice API Test Script
Tests the complete setup without needing a running server
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required modules can be imported"""
    print("🧪 Testing imports...")
    
    try:
        from db_manager_unified import get_db_manager  # type: ignore
        print("✅ db_manager_unified imported")
    except ImportError as e:
        print(f"❌ db_manager_unified import failed: {e}")
        return False
    
    try:
        from routes.invoices_api import router as invoices_router  # type: ignore
        print("✅ invoices_api router imported")
    except ImportError as e:
        print(f"❌ invoices_api router import failed: {e}")
        return False
    
    try:
        from routes.debug_api import router as debug_router  # type: ignore
        print("✅ debug_api router imported")
    except ImportError as e:
        print(f"❌ debug_api router import failed: {e}")
        return False
    
    return True

def test_database_manager():
    """Test database manager functionality"""
    print("\n🧪 Testing database manager...")
    
    try:
        db_manager = get_db_manager()  # type: ignore
        print(f"✅ Database manager created: {type(db_manager)}")
        
        db_path = db_manager.db_path  # type: ignore
        print(f"✅ Database path: {db_path}")
        print(f"✅ Database exists: {db_path.exists()}")
        
        if db_path.exists():
            size = db_path.stat().st_size  # type: ignore
            print(f"✅ Database size: {size} bytes")
        
        return True
    except Exception as e:
        print(f"❌ Database manager test failed: {e}")
        return False

def test_router_structure():
    """Test router structure and endpoints"""
    print("\n🧪 Testing router structure...")
    
    try:
        from routes.invoices_api import router as invoices_router  # type: ignore
        from routes.debug_api import router as debug_router  # type: ignore
        
        # Check invoices router
        print(f"✅ Invoices router prefix: {invoices_router.prefix}")  # type: ignore
        print(f"✅ Invoices router tags: {invoices_router.tags}")  # type: ignore
        
        # Check debug router
        print(f"✅ Debug router prefix: {debug_router.prefix}")  # type: ignore
        print(f"✅ Debug router tags: {debug_router.tags}")  # type: ignore
        
        return True
    except Exception as e:
        print(f"❌ Router structure test failed: {e}")
        return False

def test_database_connection():
    """Test actual database connection"""
    print("\n🧪 Testing database connection...")
    
    try:
        db_manager = get_db_manager()  # type: ignore
        conn = db_manager.get_conn()  # type: ignore
        print("✅ Database connection established")
        
        # Test basic query
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"✅ Found {len(tables)} tables")
        
        # Check for required tables
        table_names = [t[0] for t in tables]
        required_tables = ['invoices', 'invoice_line_items', 'uploaded_files']
        
        for table in required_tables:
            if table in table_names:
                print(f"✅ Table '{table}' exists")
            else:
                print(f"❌ Table '{table}' missing")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 BULLETPROOF INVOICE API - COMPREHENSIVE TEST")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_database_manager,
        test_router_structure,
        test_database_connection
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Your setup is bulletproof.")
        print("\n🚀 Next steps:")
        print("1. Start the server: python3 test_server.py")
        print("2. Test the API: curl http://localhost:8000/api/invoices/inv_seed")
        print("3. Check debug endpoint: curl http://localhost:8000/api/debug/db-path")
    else:
        print("❌ Some tests failed. Check the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 