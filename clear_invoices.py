#!/usr/bin/env python3
"""
Clear all invoices, line items, and documents from the database.
This is useful for testing with fresh uploads.

Usage:
    python clear_invoices.py          # Interactive mode
    python clear_invoices.py --yes    # Non-interactive mode
"""
import sqlite3
import os
import sys
from pathlib import Path

DB_PATH = "data/owlin.db"

def clear_invoices(confirm=True):
    """Clear all invoices, line items, and documents from database"""
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return False
    
    if confirm and '--yes' not in sys.argv:
        print("=" * 60)
        print("Owlin Database Cleaner")
        print("=" * 60)
        print("\nThis will delete ALL invoices, line items, and documents.")
        print("Audit logs will be preserved.")
        response = input("\nAre you sure you want to continue? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Cancelled.")
            return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Get counts before deletion
        cursor.execute("SELECT COUNT(*) FROM invoices")
        invoice_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM invoice_line_items")
        line_item_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM documents")
        document_count = cursor.fetchone()[0]
        
        print(f"Found {invoice_count} invoices, {line_item_count} line items, {document_count} documents")
        
        if invoice_count == 0 and line_item_count == 0 and document_count == 0:
            print("Database is already empty.")
            return True
        
        # Clear tables in correct order (respecting foreign keys)
        print("\nClearing tables...")
        
        # Clear line items first (has foreign keys to invoices)
        cursor.execute("DELETE FROM invoice_line_items")
        print(f"  [OK] Cleared invoice_line_items")
        
        # Clear invoices
        cursor.execute("DELETE FROM invoices")
        print(f"  [OK] Cleared invoices")
        
        # Clear documents
        cursor.execute("DELETE FROM documents")
        print(f"  [OK] Cleared documents")
        
        # Commit changes
        conn.commit()
        
        # Vacuum to reclaim space
        cursor.execute("VACUUM")
        print(f"  [OK] Vacuumed database")
        
        print(f"\n[SUCCESS] Successfully cleared all invoices, line items, and documents!")
        print(f"   Database is now empty and ready for fresh uploads.")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Error clearing database: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    clear_invoices()
