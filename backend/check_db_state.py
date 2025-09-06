#!/usr/bin/env python3
"""
Simple script to check database state without terminal
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_database_state():
    """Check the current database state"""
    print("🔍 Checking Database State")
    print("=" * 40)
    
    try:
        # Check if we can import the database manager
        from db_manager_unified import get_db_manager
        print("✅ Database manager import OK")
        
        # Get database manager
        db_manager = get_db_manager()
        db_path = db_manager.db_path
        print(f"📍 Database path: {db_path}")
        print(f"📁 Database exists: {db_path.exists()}")
        
        if not db_path.exists():
            print("❌ Database file does not exist!")
            return False
        
        # Check database size
        size = db_path.stat().st_size
        print(f"📊 Database size: {size} bytes")
        
        if size == 0:
            print("❌ Database file is empty!")
            return False
        
        # Try to connect and check tables
        conn = db_manager.get_conn()
        cursor = conn.cursor()
        
        # Check what tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📋 Tables found: {tables}")
        
        # Check if required tables exist
        required_tables = ['uploaded_files', 'invoices', 'invoice_line_items']
        missing_tables = [table for table in required_tables if table not in tables]
        
        if missing_tables:
            print(f"❌ Missing required tables: {missing_tables}")
            return False
        else:
            print("✅ All required tables exist")
        
        # Check data counts
        for table in required_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"📊 {table}: {count} records")
        
        # Check if we have the test data
        cursor.execute("SELECT id, supplier_name, total_amount_pennies FROM invoices WHERE id = 'inv_seed_001'")
        test_invoice = cursor.fetchone()
        
        if test_invoice:
            print(f"✅ Test invoice found: {test_invoice}")
        else:
            print("❌ Test invoice 'inv_seed_001' not found")
            print("   You need to run: python3 seed_test_data.py")
            return False
        
        # Check line items
        cursor.execute("SELECT COUNT(*) FROM invoice_line_items WHERE invoice_id = 'inv_seed_001'")
        line_count = cursor.fetchone()[0]
        print(f"📋 Line items for test invoice: {line_count}")
        
        if line_count == 0:
            print("❌ No line items found for test invoice")
            return False
        
        print("\n🎉 Database state looks good!")
        return True
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_database_state()
    if success:
        print("\n✅ Database is ready for testing!")
        print("Next steps:")
        print("1. Start server: python3 test_server.py")
        print("2. Test API: curl http://localhost:8000/api/invoices/inv_seed_001")
    else:
        print("\n💥 Database has issues that need to be fixed!")
        print("Try running: python3 seed_test_data.py") 