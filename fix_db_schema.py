#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Schema Repair Script

This script ensures that required columns exist in the database:
- invoices.invoice_number (TEXT)
- invoice_line_items.bbox (TEXT)

It safely checks for column existence before attempting to add them,
avoiding errors if columns already exist.
"""

import sqlite3
import sys
from pathlib import Path


def get_db_path():
    """Get the database path using the same resolution as backend/app/db.py"""
    # Resolve DB_PATH as absolute path relative to project root
    # This script is in project root, so we go: project_root -> data -> owlin.db
    project_root = Path(__file__).resolve().parent
    db_path = project_root / "data" / "owlin.db"
    return str(db_path)


def table_has_column(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    """Return True if a column exists on the table."""
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def add_column_if_missing(cursor: sqlite3.Cursor, table: str, column: str, definition: str) -> bool:
    """
    Add a column to a table if it is missing.
    
    Returns:
        True if column was added, False if it already existed
    """
    if table_has_column(cursor, table, column):
        print(f"  ✓ Column '{column}' already exists in '{table}' table")
        return False
    
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")
        print(f"  ✓ Added column '{column}' to '{table}' table")
        return True
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print(f"  ✓ Column '{column}' already exists in '{table}' table (detected via error)")
            return False
        else:
            print(f"  ✗ Error adding column '{column}' to '{table}': {e}")
            raise


def main():
    """Main function to repair database schema"""
    db_path = get_db_path()
    
    print(f"Database Schema Repair Script")
    print(f"==============================")
    print(f"Database path: {db_path}")
    print()
    
    # Check if database file exists
    if not Path(db_path).exists():
        print(f"✗ ERROR: Database file not found at: {db_path}")
        print(f"  Please ensure the database exists before running this script.")
        sys.exit(1)
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Checking database schema...")
        print()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invoices'")
        if not cursor.fetchone():
            print("✗ ERROR: 'invoices' table does not exist")
            conn.close()
            sys.exit(1)
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invoice_line_items'")
        if not cursor.fetchone():
            print("✗ ERROR: 'invoice_line_items' table does not exist")
            conn.close()
            sys.exit(1)
        
        print("Tables found: invoices, invoice_line_items")
        print()
        
        # Add missing columns
        changes_made = False
        
        print("Checking/adding columns...")
        print()
        
        # Add invoice_number to invoices table
        if add_column_if_missing(cursor, "invoices", "invoice_number", "TEXT"):
            changes_made = True
        
        # Add bbox to invoice_line_items table
        if add_column_if_missing(cursor, "invoice_line_items", "bbox", "TEXT"):
            changes_made = True
        
        # Commit changes
        if changes_made:
            conn.commit()
            print()
            print("Schema Fixed")
            print("✓ All required columns are now present in the database")
        else:
            print()
            print("Schema Fixed")
            print("✓ All required columns were already present")
        
        conn.close()
        sys.exit(0)
        
    except sqlite3.Error as e:
        print(f"✗ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
