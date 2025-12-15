#!/usr/bin/env python3
"""
Migration script to fix existing delivery note line items.

This script updates delivery note line items that were stored before the fix
was implemented. It sets invoice_id = NULL for delivery note line items where
invoice_id = doc_id.

Usage:
    python scripts/fix_delivery_note_line_items.py
"""

import sqlite3
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = "data/owlin.db"


def check_doc_type_column_exists(cursor):
    """Check if doc_type column exists in documents table"""
    cursor.execute("PRAGMA table_info(documents)")
    columns = [row[1] for row in cursor.fetchall()]
    return 'doc_type' in columns


def fix_delivery_note_line_items():
    """Fix existing delivery note line items"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if doc_type column exists
        if not check_doc_type_column_exists(cursor):
            print("⚠️  doc_type column does not exist in documents table.")
            print("   This migration only applies if doc_type column exists.")
            print("   Skipping migration.")
            conn.close()
            return
        
        # Count delivery notes before update
        cursor.execute("""
            SELECT COUNT(DISTINCT doc_id)
            FROM invoice_line_items
            WHERE doc_id IN (
                SELECT id FROM documents WHERE doc_type = 'delivery_note'
            )
            AND invoice_id = doc_id
        """)
        delivery_notes_to_fix = cursor.fetchone()[0]
        
        if delivery_notes_to_fix == 0:
            print("✅ No delivery note line items need fixing.")
            print("   All delivery note line items already have invoice_id = NULL")
            conn.close()
            return
        
        print(f"📋 Found {delivery_notes_to_fix} delivery note(s) with line items to fix")
        
        # Count total line items to update
        cursor.execute("""
            SELECT COUNT(*)
            FROM invoice_line_items
            WHERE doc_id IN (
                SELECT id FROM documents WHERE doc_type = 'delivery_note'
            )
            AND invoice_id = doc_id
        """)
        line_items_to_fix = cursor.fetchone()[0]
        print(f"📋 Found {line_items_to_fix} line item(s) to update")
        
        # Update line items
        cursor.execute("""
            UPDATE invoice_line_items
            SET invoice_id = NULL
            WHERE doc_id IN (
                SELECT id FROM documents WHERE doc_type = 'delivery_note'
            )
            AND invoice_id = doc_id
        """)
        
        updated_count = cursor.rowcount
        conn.commit()
        
        # Verify the update
        cursor.execute("""
            SELECT COUNT(*)
            FROM invoice_line_items
            WHERE doc_id IN (
                SELECT id FROM documents WHERE doc_type = 'delivery_note'
            )
            AND invoice_id IS NULL
        """)
        verified_count = cursor.fetchone()[0]
        
        print(f"✅ Updated {updated_count} line item(s)")
        print(f"✅ Verified {verified_count} delivery note line item(s) now have invoice_id = NULL")
        
        if updated_count != line_items_to_fix:
            print(f"⚠️  Warning: Expected to update {line_items_to_fix} items, but updated {updated_count}")
        
        conn.close()
        print("\n✅ Migration completed successfully!")
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        if conn:
            conn.rollback()
            conn.close()
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        if conn:
            conn.close()
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Fix Delivery Note Line Items")
    print("=" * 60)
    print()
    
    if not Path(DB_PATH).exists():
        print(f"❌ Database not found at {DB_PATH}")
        sys.exit(1)
    
    fix_delivery_note_line_items()

