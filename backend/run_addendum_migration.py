#!/usr/bin/env python3
"""
Migration runner for addendum features

This script applies the database migrations needed for the addendum features
including document classification, enhanced pairing, and annotation detection.
"""

import sqlite3
import os
import sys
from pathlib import Path


def run_migration():
    """Run the addendum features migration"""
    
    # Determine database path
    db_path = "data/owlin.db"
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        print("Creating database directory...")
        os.makedirs("data", exist_ok=True)
    
    # Connect to database
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    
    try:
        print("🔄 Running addendum features migration...")
        
        # Read and execute the migration SQL
        migration_file = Path(__file__).parent / "db_migrations" / "002_addendum_features.sql"
        
        if not migration_file.exists():
            print(f"❌ Migration file not found: {migration_file}")
            return False
        
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Execute the migration
        cursor.executescript(migration_sql)
        db.commit()
        
        print("✅ Migration completed successfully!")
        
        # Verify tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = [
            'doc_pairs', 'annotations', 'document_classification', 
            'pairing_rules', 'annotation_mappings'
        ]
        
        print("\n📋 Verifying table creation:")
        for table in required_tables:
            if table in tables:
                print(f"  ✅ {table}")
            else:
                print(f"  ❌ {table} - NOT FOUND")
        
        # Check for default pairing rules
        cursor.execute("SELECT COUNT(*) FROM pairing_rules")
        rule_count = cursor.fetchone()[0]
        print(f"\n📊 Default pairing rules created: {rule_count}")
        
        # Show table schemas
        print("\n📋 Table schemas:")
        for table in required_tables:
            if table in tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                print(f"\n{table}:")
                for col in columns:
                    print(f"  - {col[1]} ({col[2]})")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
        return False
    
    finally:
        db.close()


def check_existing_schema():
    """Check what tables already exist"""
    db_path = "data/owlin.db"
    
    if not os.path.exists(db_path):
        print("Database does not exist yet.")
        return
    
    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [row[0] for row in cursor.fetchall()]
    
    print("📋 Existing tables:")
    for table in existing_tables:
        print(f"  - {table}")
    
    db.close()


if __name__ == "__main__":
    print("🚀 OWLIN Addendum Features Migration")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        check_existing_schema()
    else:
        success = run_migration()
        if success:
            print("\n🎉 Addendum features are now ready!")
            print("\nNext steps:")
            print("1. Restart your OWLIN application")
            print("2. Test the new API endpoints:")
            print("   - GET /api/annotations/")
            print("   - GET /api/pairings/")
            print("   - POST /api/pairings/auto-pair")
            print("3. Run tests: python -m pytest backend/tests/test_addendum_features.py")
        else:
            print("\n❌ Migration failed. Please check the error messages above.")
            sys.exit(1)
