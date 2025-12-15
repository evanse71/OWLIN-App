#!/usr/bin/env python3
"""
Apply invoice_number migration to database.

This script adds the invoice_number column to the invoices table
and creates an index for faster lookups.

Usage:
    python apply_invoice_number_migration.py
"""

import sqlite3
import sys
from pathlib import Path

# Database path
DB_PATH = Path("data") / "owlin.db"

def apply_migration():
    """Apply the invoice_number migration."""
    
    print("=" * 80)
    print("INVOICE NUMBER MIGRATION")
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
        cursor.execute("PRAGMA table_info(invoices)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'invoice_number' in columns:
            print("\n✓ Column 'invoice_number' already exists")
            print("Migration already applied, skipping.")
            conn.close()
            return True
        
        print("\n📝 Applying migration...")
        
        # Add invoice_number column
        print("  1. Adding invoice_number column...")
        cursor.execute("ALTER TABLE invoices ADD COLUMN invoice_number TEXT")
        print("     ✓ Column added")
        
        # Create index
        print("  2. Creating index on invoice_number...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_invoice_number ON invoices(invoice_number)")
        print("     ✓ Index created")
        
        # Commit changes
        conn.commit()
        
        # Verify
        cursor.execute("PRAGMA table_info(invoices)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'invoice_number' in columns:
            print("\n✅ Migration successful!")
            print(f"   Columns: {', '.join(columns)}")
            
            # Count existing invoices
            cursor.execute("SELECT COUNT(*) FROM invoices")
            count = cursor.fetchone()[0]
            print(f"   Existing invoices: {count}")
            print(f"   Note: Existing invoices will have NULL invoice_number (will be populated on next OCR)")
            
            conn.close()
            return True
        else:
            print("\n❌ Migration verification failed")
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

def rollback_migration():
    """Rollback the invoice_number migration (if needed)."""
    
    print("\n" + "=" * 80)
    print("ROLLBACK MIGRATION")
    print("=" * 80)
    
    print("\n⚠️  SQLite does not support DROP COLUMN in ALTER TABLE.")
    print("To rollback, you would need to:")
    print("  1. Create a new table without invoice_number column")
    print("  2. Copy data from old table")
    print("  3. Drop old table")
    print("  4. Rename new table")
    print("\nRecommendation: Keep the column (NULL values are harmless)")
    print("=" * 80)

if __name__ == "__main__":
    print("\nInvoice Number Migration Script")
    print("This will add the invoice_number column to the invoices table\n")
    
    # Check for rollback flag
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        rollback_migration()
        sys.exit(0)
    
    # Apply migration
    success = apply_migration()
    
    if success:
        print("\n" + "=" * 80)
        print("✅ MIGRATION COMPLETE")
        print("=" * 80)
        print("\nNext steps:")
        print("  1. Restart backend service")
        print("  2. Upload a test invoice")
        print("  3. Check logs for: [EXTRACT] Invoice Number: ...")
        print("  4. Verify invoice_number is saved in database")
        print("=" * 80)
        sys.exit(0)
    else:
        print("\n" + "=" * 80)
        print("❌ MIGRATION FAILED")
        print("=" * 80)
        print("\nPlease review errors above and try again.")
        sys.exit(1)

