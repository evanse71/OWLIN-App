#!/usr/bin/env python3
"""
Check what columns actually exist in the documents table
"""

import sqlite3
from pathlib import Path

DB_PATH = Path("data/owlin.db")

def check_columns():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    
    try:
        # Get table info
        cursor = conn.execute("PRAGMA table_info(documents)")
        columns = cursor.fetchall()
        print("Documents table columns:")
        for col in columns:
            print(f"  {col['name']} ({col['type']})")
        
        # Get column names as a set
        col_names = {col['name'] for col in columns}
        print(f"\nColumn names: {col_names}")
        
        # Check what we're missing
        expected_cols = {"sha256", "filename", "bytes", "supplier", "invoice_no", "delivery_no", "doc_date", "total", "currency", "doc_type"}
        missing_cols = expected_cols - col_names
        print(f"Missing columns: {missing_cols}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_columns()
