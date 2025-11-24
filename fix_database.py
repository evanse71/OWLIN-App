#!/usr/bin/env python3
"""
Fix database schema for pairing system
"""

import sqlite3
import os
from pathlib import Path

DB_PATH = Path("data/owlin.db")

def fix_database():
    print("Fixing database schema...")
    
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    
    try:
        # Check existing tables
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Existing tables: {tables}")
        
        # Create documents table if it doesn't exist
        if 'documents' not in tables:
            print("Creating documents table...")
            conn.execute("""
                CREATE TABLE documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sha256 TEXT UNIQUE NOT NULL,
                    filename TEXT NOT NULL,
                    bytes INTEGER NOT NULL,
                    supplier TEXT,
                    invoice_no TEXT,
                    delivery_no TEXT,
                    doc_date TEXT,
                    total REAL,
                    currency TEXT,
                    doc_type TEXT DEFAULT 'unknown',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            # Add missing columns to existing documents table
            print("Updating documents table...")
            try:
                conn.execute("ALTER TABLE documents ADD COLUMN doc_type TEXT DEFAULT 'unknown'")
            except sqlite3.OperationalError:
                print("doc_type column already exists")
            
            try:
                conn.execute("ALTER TABLE documents ADD COLUMN supplier TEXT")
            except sqlite3.OperationalError:
                print("supplier column already exists")
                
            try:
                conn.execute("ALTER TABLE documents ADD COLUMN invoice_no TEXT")
            except sqlite3.OperationalError:
                print("invoice_no column already exists")
                
            try:
                conn.execute("ALTER TABLE documents ADD COLUMN delivery_no TEXT")
            except sqlite3.OperationalError:
                print("delivery_no column already exists")
                
            try:
                conn.execute("ALTER TABLE documents ADD COLUMN doc_date TEXT")
            except sqlite3.OperationalError:
                print("doc_date column already exists")
                
            try:
                conn.execute("ALTER TABLE documents ADD COLUMN total REAL")
            except sqlite3.OperationalError:
                print("total column already exists")
                
            try:
                conn.execute("ALTER TABLE documents ADD COLUMN currency TEXT")
            except sqlite3.OperationalError:
                print("currency column already exists")
        
        # Create pairs table if it doesn't exist
        if 'pairs' not in tables:
            print("Creating pairs table...")
            conn.execute("""
                CREATE TABLE pairs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id INTEGER NOT NULL,
                    delivery_id INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    status TEXT DEFAULT 'suggested',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    decided_at DATETIME,
                    FOREIGN KEY (invoice_id) REFERENCES documents(id),
                    FOREIGN KEY (delivery_id) REFERENCES documents(id),
                    UNIQUE(invoice_id, delivery_id)
                )
            """)
        
        # Create indexes
        print("Creating indexes...")
        try:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_sha256 ON documents(sha256)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_doc_type ON documents(doc_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_supplier ON documents(supplier)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pairs_status ON pairs(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pairs_confidence ON pairs(confidence)")
        except Exception as e:
            print(f"Index creation error: {e}")
        
        conn.commit()
        print("Database schema updated successfully")
        
        # Test the tables
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Updated tables: {tables}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_database()
