#!/usr/bin/env python3
"""
Quick test to verify the pairing system is working
"""

import sqlite3
import os
from pathlib import Path

# Test database connection and table creation
DB_PATH = Path("data/owlin.db")

def test_db():
    print("Testing database connection...")
    
    # Create database directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    
    try:
        # Run migration
        print("Running migration...")
        with open("migrations/0003_pairs.sql", "r") as f:
            migration_sql = f.read()
        conn.executescript(migration_sql)
        conn.commit()
        print("Migration completed")
        
        # Test table creation
        print("Checking tables...")
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Tables: {tables}")
        
        if 'documents' in tables and 'pairs' in tables:
            print("Tables created successfully")
        else:
            print("Tables not found")
            
        # Test inserting a document
        print("Testing document insertion...")
        test_doc = {
            "sha256": "test123",
            "filename": "test.pdf",
            "bytes": 100,
            "supplier": "Test Supplier",
            "invoice_no": "INV-001",
            "delivery_no": None,
            "doc_date": "2025-01-01",
            "total": 100.0,
            "currency": "USD",
            "doc_type": "invoice"
        }
        
        cursor = conn.execute("""
            INSERT INTO documents
              (sha256, filename, bytes, supplier, invoice_no, delivery_no, doc_date, total, currency, doc_type)
            VALUES
              (:sha256, :filename, :bytes, :supplier, :invoice_no, :delivery_no, :doc_date, :total, :currency, :doc_type)
        """, test_doc)
        
        doc_id = cursor.lastrowid
        print(f"Document inserted with ID: {doc_id}")
        
        # Test querying documents
        cursor = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        doc = cursor.fetchone()
        if doc:
            print(f"Document retrieved: {dict(doc)}")
        else:
            print("Document not found")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    test_db()
