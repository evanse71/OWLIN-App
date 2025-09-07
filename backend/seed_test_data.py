#!/usr/bin/env python3
"""
Seed script to create test data for invoice API testing
"""

import sqlite3
import os
from pathlib import Path

def seed_test_data():
    """Seed the database with test invoice data"""
    
    # Get database path from environment or use default
    db_path = os.environ.get("OWLIN_DB_PATH", "data/owlin.db")
    
    print(f"🌱 Seeding database at: {db_path}")
    
    # Ensure database directory exists
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    
    try:
        cursor = conn.cursor()
        
        # Check if tables exist, create if not
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uploaded_files (
                id TEXT PRIMARY KEY,
                original_filename TEXT NOT NULL,
                canonical_path TEXT NOT NULL UNIQUE,
                file_size INTEGER NOT NULL,
                file_hash TEXT NOT NULL UNIQUE,
                mime_type TEXT NOT NULL,
                doc_type TEXT NOT NULL CHECK (doc_type IN ('invoice', 'delivery_note', 'receipt', 'utility', 'unknown')),
                doc_type_confidence REAL DEFAULT 0.0,
                upload_timestamp TEXT NOT NULL,
                processing_status TEXT NOT NULL DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed', 'timeout', 'reviewed')),
                processing_progress INTEGER DEFAULT 0 CHECK (processing_progress >= 0 AND processing_progress <= 100),
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                last_retry_timestamp TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                invoice_number TEXT,
                invoice_date TEXT,
                supplier_name TEXT,
                venue TEXT,
                total_amount_pennies INTEGER NOT NULL DEFAULT 0,
                subtotal_pennies INTEGER,
                vat_total_pennies INTEGER,
                vat_rate REAL DEFAULT 20.0,
                currency TEXT DEFAULT 'GBP',
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'scanned', 'parsed', 'matched', 'failed', 'timeout', 'reviewed')),
                confidence REAL NOT NULL DEFAULT 0.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
                paired BOOLEAN DEFAULT FALSE,
                issues_count INTEGER DEFAULT 0,
                processing_progress INTEGER DEFAULT 0 CHECK (processing_progress >= 0 AND processing_progress <= 100),
                error_message TEXT,
                page_range TEXT,
                validation_flags TEXT,
                field_confidence TEXT,
                raw_extraction TEXT,
                warnings TEXT,
                addresses TEXT,
                signature_regions TEXT,
                verification_status TEXT DEFAULT 'unreviewed' CHECK (verification_status IN ('unreviewed', 'needs_review', 'reviewed')),
                doc_type TEXT DEFAULT 'invoice',
                doc_type_score REAL DEFAULT 1.0,
                policy_action TEXT,
                reasons_json TEXT,
                validation_json TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (file_id) REFERENCES uploaded_files(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoice_line_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id TEXT NOT NULL,
                row_idx INTEGER,
                page INTEGER,
                description TEXT NOT NULL,
                quantity REAL NOT NULL DEFAULT 0,
                unit TEXT,
                unit_price_pennies INTEGER NOT NULL DEFAULT 0,
                vat_rate REAL DEFAULT 20.0,
                line_total_pennies INTEGER NOT NULL DEFAULT 0,
                confidence REAL DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
                flags TEXT,
                line_confidence REAL DEFAULT 1.0,
                row_reasons_json TEXT,
                computed_total BOOLEAN DEFAULT FALSE,
                unit_original TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
            )
        """)
        
        # Insert test data
        print("📝 Inserting test data...")
        
        # 1. Insert uploaded file
        cursor.execute("""
            INSERT OR REPLACE INTO uploaded_files
            (id, original_filename, canonical_path, file_size, file_hash, mime_type, doc_type, doc_type_confidence, upload_timestamp, processing_status, processing_progress, created_at, updated_at)
            VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?, datetime('now'), datetime('now'))
        """, (
            'seed_file_001',
            'test_invoice.pdf',
            '/tmp/test_invoice.pdf',
            12345,
            'deadbeef123456789',
            'application/pdf',
            'invoice',
            1.0,
            'completed',
            100
        ))
        
        # 2. Insert invoice (7200 pennies = £72.00)
        cursor.execute("""
            INSERT OR REPLACE INTO invoices
            (id, file_id, invoice_number, invoice_date, supplier_name, total_amount_pennies, status, confidence, created_at, updated_at)
            VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """, (
            'inv_seed_001',
            'seed_file_001',
            'INV-001',
            '2024-01-15',
            'TIA MARIA SUPPLIERS',
            7200,  # £72.00 in pennies
            'completed',
            0.95
        ))
        
        # 3. Insert line items
        cursor.execute("""
            INSERT OR REPLACE INTO invoice_line_items
            (id, invoice_id, row_idx, page, description, quantity, unit_price_pennies, line_total_pennies, created_at, updated_at)
            VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """, (
            4001,
            'inv_seed_001',
            0,
            1,
            'TIA MARIA 1L',
            6.0,
            1200,  # £12.00 in pennies
            7200   # £72.00 in pennies
        ))
        
        # Commit the changes
        conn.commit()
        print("✅ Test data seeded successfully!")
        
        # Verify the data
        print("\n🔍 Verifying seeded data...")
        
        cursor.execute("SELECT id, total_amount_pennies FROM invoices WHERE id = ?", ('inv_seed_001',))
        invoice = cursor.fetchone()
        if invoice:
            print(f"✅ Invoice: {invoice[0]}, Total: {invoice[1]} pennies (£{invoice[1]/100:.2f})")
        else:
            print("❌ Invoice not found")
        
        cursor.execute("SELECT description, quantity, unit_price_pennies, line_total_pennies FROM invoice_line_items WHERE invoice_id = ?", ('inv_seed_001',))
        line_item = cursor.fetchone()
        if line_item:
            print(f"✅ Line item: {line_item[0]}, Qty: {line_item[1]}, Unit: £{line_item[2]/100:.2f}, Total: £{line_item[3]/100:.2f}")
        else:
            print("❌ Line item not found")
        
    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    seed_test_data() 