#!/usr/bin/env python3
"""Check if HTR tables exist in the database."""

import sqlite3
import sys

def check_htr_tables(db_path="data/owlin.db"):
    """Check if HTR tables exist."""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'htr_%'")
            tables = cursor.fetchall()
            
            print(f"HTR tables in {db_path}:")
            for table in tables:
                print(f"  - {table[0]}")
            
            if not tables:
                print("No HTR tables found!")
                return False
            else:
                print(f"Found {len(tables)} HTR tables")
                return True
                
    except Exception as e:
        print(f"Error checking tables: {e}")
        return False

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/owlin.db"
    check_htr_tables(db_path)
