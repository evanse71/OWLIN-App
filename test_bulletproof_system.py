#!/usr/bin/env python3
"""
Test script for the bulletproof upload system
"""

import sys
import os
sys.path.insert(0, 'backend')

def test_database_manager():
    """Test database manager"""
    print("🧪 Testing Database Manager...")
    try:
        from db_manager_unified import get_db_manager
        db = get_db_manager()
        print("✅ Database manager initialized successfully")
        
        # Test basic operations
        stats = db.get_system_stats()
        print(f"✅ System stats retrieved: {len(stats)} metrics")
        
        return True
    except Exception as e:
        print(f"❌ Database manager test failed: {e}")
        return False

def test_schema():
    """Test database schema"""
    print("🧪 Testing Database Schema...")
    try:
        import sqlite3
        from db_manager_unified import DEFAULT_DB_PATH
        
        conn = sqlite3.connect(DEFAULT_DB_PATH)
        cursor = conn.cursor()
        
        # Check if tables exist
        tables = ['uploaded_files', 'invoices', 'delivery_notes', 'jobs', 'audit_log']
        for table in tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone():
                print(f"✅ Table {table} exists")
            else:
                print(f"❌ Table {table} missing")
                return False
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Schema test failed: {e}")
        return False

def test_upload_pipeline():
    """Test upload pipeline"""
    print("🧪 Testing Upload Pipeline...")
    try:
        from upload_pipeline_bulletproof import get_upload_pipeline
        pipeline = get_upload_pipeline()
        print("✅ Upload pipeline initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Upload pipeline test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Bulletproof Upload System")
    print("=" * 50)
    
    tests = [
        test_database_manager,
        test_schema,
        test_upload_pipeline
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System is ready.")
        return True
    else:
        print("❌ Some tests failed. System needs fixes.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 