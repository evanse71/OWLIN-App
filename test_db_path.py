#!/usr/bin/env python3

import os
import sqlite3

# Test the database path calculation
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "owlin.db")
print(f"Database path: {db_path}")
print(f"Path exists: {os.path.exists(db_path)}")

if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invoices'")
        invoices_exists = cursor.fetchone()
        print(f"Invoices table exists: {invoices_exists is not None}")
        
        if invoices_exists:
            cursor.execute("SELECT COUNT(*) FROM invoices")
            count = cursor.fetchone()[0]
            print(f"Invoices count: {count}")
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='delivery_notes'")
        delivery_notes_exists = cursor.fetchone()
        print(f"Delivery notes table exists: {delivery_notes_exists is not None}")
        
        if delivery_notes_exists:
            cursor.execute("SELECT COUNT(*) FROM delivery_notes")
            count = cursor.fetchone()[0]
            print(f"Delivery notes count: {count}")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
else:
    print("Database file not found!") 