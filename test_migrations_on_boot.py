#!/usr/bin/env python3
"""
Test Migrations on Boot - Olympic Judge Certification
"""

import sys
import os
import tempfile
import sqlite3
import shutil
from pathlib import Path

# Add backend to path
sys.path.insert(0, 'backend')

def test_empty_db_migrations():
    """Test migrations on completely empty database"""
    print("🧪 Testing migrations on empty database...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Set environment variable
        os.environ['OWLIN_DB'] = db_path
        
        # Initialize database manager
        from db_manager_unified import DatabaseManager
        db = DatabaseManager(db_path)
        
        # Run migrations
        db.run_migrations()
        
        # Verify schema
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check required tables exist
            required_tables = [
                'uploaded_files', 'invoices', 'delivery_notes', 
                'invoice_line_items', 'delivery_line_items',
                'jobs', 'audit_log', 'match_links', 'match_line_links',
                'processing_logs', 'migrations'
            ]
            
            for table in required_tables:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if not cursor.fetchone():
                    print(f"❌ Table {table} missing")
                    return False
                else:
                    print(f"✅ Table {table} exists")
            
            # Check migrations table is populated
            cursor.execute("SELECT version, name FROM migrations ORDER BY version")
            migrations = cursor.fetchall()
            if not migrations:
                print("❌ No migrations recorded")
                return False
            
            print(f"✅ {len(migrations)} migrations applied:")
            for version, name in migrations:
                print(f"   - {version}: {name}")
            
            # Verify schema_master content
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            all_tables = [row[0] for row in cursor.fetchall()]
            print(f"✅ All tables in schema: {all_tables}")
        
        return True
        
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)

def test_dirty_db_migrations():
    """Test migrations on database with existing data"""
    print("🧪 Testing migrations on dirty database...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Create a "dirty" database with some existing data
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Create some old tables that shouldn't conflict
        conn.execute("CREATE TABLE old_table (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO old_table (id) VALUES (1)")
        
        # Create migrations table with old migration
        conn.execute("""
            CREATE TABLE migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
        """)
        conn.execute("INSERT INTO migrations (version, name, applied_at) VALUES (0, 'old_migration', datetime('now'))")
        
        conn.commit()
        conn.close()
        
        # Set environment variable
        os.environ['OWLIN_DB'] = db_path
        
        # Initialize database manager
        from db_manager_unified import DatabaseManager
        db = DatabaseManager(db_path)
        
        # Run migrations
        db.run_migrations()
        
        # Verify schema
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check required tables exist
            required_tables = [
                'uploaded_files', 'invoices', 'delivery_notes', 
                'invoice_line_items', 'delivery_line_items',
                'jobs', 'audit_log', 'match_links', 'match_line_links',
                'processing_logs', 'migrations'
            ]
            
            for table in required_tables:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if not cursor.fetchone():
                    print(f"❌ Table {table} missing")
                    return False
                else:
                    print(f"✅ Table {table} exists")
            
            # Check old table still exists (shouldn't be touched)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='old_table'")
            if not cursor.fetchone():
                print("❌ Old table was incorrectly removed")
                return False
            else:
                print("✅ Old table preserved")
            
            # Check migrations table has both old and new migrations
            cursor.execute("SELECT version, name FROM migrations ORDER BY version")
            migrations = cursor.fetchall()
            if len(migrations) < 2:
                print(f"❌ Expected at least 2 migrations, got {len(migrations)}")
                return False
            
            print(f"✅ {len(migrations)} migrations applied (including old):")
            for version, name in migrations:
                print(f"   - {version}: {name}")
        
        return True
        
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)

def test_idempotent_migrations():
    """Test that running migrations multiple times is idempotent"""
    print("🧪 Testing migrations are idempotent...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Set environment variable
        os.environ['OWLIN_DB'] = db_path
        
        # Initialize database manager
        from db_manager_unified import DatabaseManager
        db = DatabaseManager(db_path)
        
        # Run migrations first time
        db.run_migrations()
        
        # Get migration count
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM migrations")
            initial_count = cursor.fetchone()[0]
        
        # Run migrations again
        db.run_migrations()
        
        # Get migration count again
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM migrations")
            final_count = cursor.fetchone()[0]
        
        if initial_count == final_count:
            print(f"✅ Migration count unchanged: {final_count}")
            return True
        else:
            print(f"❌ Migration count changed: {initial_count} -> {final_count}")
            return False
        
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)

def main():
    """Run all migration tests"""
    print("🚀 TESTING MIGRATIONS ON BOOT")
    print("=" * 50)
    
    tests = [
        test_empty_db_migrations,
        test_dirty_db_migrations,
        test_idempotent_migrations
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL MIGRATION TESTS PASSED!")
        print("✅ Migrations work correctly on boot")
        return True
    else:
        print("❌ Some migration tests failed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 