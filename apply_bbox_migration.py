#!/usr/bin/env python3
"""
Apply bbox migration to database.

This script adds the bbox column to the invoice_line_items table
and creates an index for faster lookups.

Usage:
    python apply_bbox_migration.py
"""

import sqlite3
import sys
from pathlib import Path

# Database path
DB_PATH = Path("data") / "owlin.db"

def apply_migration():
    """Apply the bbox migration."""
    
    print("=" * 80)
    print("BBOX MIGRATION")
    print("=" * 80)
    
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        print("Please ensure the database exists before running migration.")
        return False
    
    print(f"\n📁 Database: {DB_PATH}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(invoice_line_items)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'bbox' in columns:
            print("\n✓ Column 'bbox' already exists")
            print("Migration already applied, skipping.")
            conn.close()
            return True
        
        print("\n📝 Applying migration...")
        
        # Add bbox column
        print("  1. Adding bbox column...")
        cursor.execute("ALTER TABLE invoice_line_items ADD COLUMN bbox TEXT")
        print("     ✓ Column added")
        
        # Create index
        print("  2. Creating index on bbox...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_line_items_bbox ON invoice_line_items(bbox) WHERE bbox IS NOT NULL")
        print("     ✓ Index created")
        
        # Commit changes
        conn.commit()
        
        # Verify
        cursor.execute("PRAGMA table_info(invoice_line_items)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'bbox' in columns:
            print("\n✅ Migration successful!")
            print(f"   Column 'bbox' is now available in invoice_line_items table")
            
            # Check existing records
            cursor.execute("SELECT COUNT(*) FROM invoice_line_items")
            total_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM invoice_line_items WHERE bbox IS NOT NULL")
            bbox_count = cursor.fetchone()[0]
            
            print(f"\n📊 Statistics:")
            print(f"   Total line items: {total_count}")
            print(f"   Items with bbox: {bbox_count}")
            print(f"   Items without bbox: {total_count - bbox_count}")
            print(f"\n💡 Tip: Re-process invoices to populate bbox data for visual verification")
            
            conn.close()
            return True
        else:
            print("\n❌ Migration failed - column not found after creation")
            conn.close()
            return False
            
    except sqlite3.Error as e:
        print(f"\n❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = apply_migration()
    sys.exit(0 if success else 1)

