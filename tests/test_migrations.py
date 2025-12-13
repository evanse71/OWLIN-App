#!/usr/bin/env python3
"""
Test migrations work correctly
"""

import os
import sys
import tempfile
import sqlite3
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from db_manager_unified import DatabaseManager

def test_migrations_fresh_db():
    """Test migrations on a fresh database"""
    print("🧪 Testing migrations on fresh database...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Initialize database manager
        db_manager = DatabaseManager(db_path)
        
        # Run migrations
        db_manager.run_migrations()
        
        # Verify tables exist
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check required tables
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
            
            # Check migrations were recorded
            cursor.execute("SELECT version, name FROM migrations ORDER BY version")
            applied_migrations = cursor.fetchall()
            
            if not applied_migrations:
                print("❌ No migrations recorded")
                return False
            
            print(f"✅ {len(applied_migrations)} migrations applied:")
            for version, name in applied_migrations:
                print(f"   - {version}: {name}")
            
            return True
            
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)

def test_migrations_idempotent():
    """Test migrations are idempotent (can run twice safely)"""
    print("🧪 Testing migrations are idempotent...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Initialize database manager
        db_manager = DatabaseManager(db_path)
        
        # Run migrations first time
        db_manager.run_migrations()
        
        # Get migration count after first run
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM migrations")
            first_count = cursor.fetchone()[0]
        
        # Run migrations second time
        db_manager.run_migrations()
        
        # Get migration count after second run
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM migrations")
            second_count = cursor.fetchone()[0]
        
        # Should be the same (no new migrations applied)
        if first_count != second_count:
            print(f"❌ Migration count changed: {first_count} -> {second_count}")
            return False
        
        print(f"✅ Migration count unchanged: {first_count}")
        return True
        
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)

def test_migration_ordering():
    """Test migrations are applied in correct order"""
    print("🧪 Testing migration ordering...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Initialize database manager
        db_manager = DatabaseManager(db_path)
        
        # Run migrations
        db_manager.run_migrations()
        
        # Check migrations were applied in order
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT version FROM migrations ORDER BY version")
            versions = [row[0] for row in cursor.fetchall()]
            
            # Check versions are in ascending order
            if versions != sorted(versions):
                print(f"❌ Migrations not in order: {versions}")
                return False
            
            print(f"✅ Migrations applied in order: {versions}")
            return True
            
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)

def main():
    """Run all migration tests"""
    print("🚀 Testing Database Migrations")
    print("=" * 50)
    
    tests = [
        test_migrations_fresh_db,
        test_migrations_idempotent,
        test_migration_ordering
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
        print("🎉 All migration tests passed!")
        return True
    else:
        print("❌ Some migration tests failed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 