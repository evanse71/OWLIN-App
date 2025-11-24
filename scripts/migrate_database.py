#!/usr/bin/env python
"""Migrate existing database to new schema"""
import sys
import sqlite3
sys.path.insert(0, '.')

DB_PATH = "data/owlin.db"

def column_exists(cursor, table, column):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns

def table_exists(cursor, table):
    """Check if a table exists"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cursor.fetchone() is not None

def migrate():
    """Apply migration to existing database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Checking database schema...")
    
    # Add status tracking columns to documents if they don't exist
    if not column_exists(cursor, 'documents', 'status'):
        print("Adding status column to documents...")
        cursor.execute("ALTER TABLE documents ADD COLUMN status TEXT DEFAULT 'pending'")
    
    if not column_exists(cursor, 'documents', 'ocr_confidence'):
        print("Adding ocr_confidence column to documents...")
        cursor.execute("ALTER TABLE documents ADD COLUMN ocr_confidence REAL DEFAULT 0.0")
    
    if not column_exists(cursor, 'documents', 'ocr_stage'):
        print("Adding ocr_stage column to documents...")
        cursor.execute("ALTER TABLE documents ADD COLUMN ocr_stage TEXT DEFAULT 'upload'")
    
    if not column_exists(cursor, 'documents', 'ocr_error'):
        print("Adding ocr_error column to documents...")
        cursor.execute("ALTER TABLE documents ADD COLUMN ocr_error TEXT DEFAULT NULL")
    
    # Add extra columns to invoices if they don't exist
    if not column_exists(cursor, 'invoices', 'confidence'):
        print("Adding confidence column to invoices...")
        cursor.execute("ALTER TABLE invoices ADD COLUMN confidence REAL DEFAULT 0.9")
    
    if not column_exists(cursor, 'invoices', 'status'):
        print("Adding status column to invoices...")
        cursor.execute("ALTER TABLE invoices ADD COLUMN status TEXT DEFAULT 'scanned'")
    
    if not column_exists(cursor, 'invoices', 'venue'):
        print("Adding venue column to invoices...")
        cursor.execute("ALTER TABLE invoices ADD COLUMN venue TEXT DEFAULT 'Main Restaurant'")
    
    if not column_exists(cursor, 'invoices', 'issues_count'):
        print("Adding issues_count column to invoices...")
        cursor.execute("ALTER TABLE invoices ADD COLUMN issues_count INTEGER DEFAULT 0")
    
    if not column_exists(cursor, 'invoices', 'paired'):
        print("Adding paired column to invoices...")
        cursor.execute("ALTER TABLE invoices ADD COLUMN paired INTEGER DEFAULT 0")
    
    if not column_exists(cursor, 'invoices', 'created_at'):
        print("Adding created_at column to invoices...")
        cursor.execute("ALTER TABLE invoices ADD COLUMN created_at TEXT DEFAULT NULL")
    
    # Create invoice_line_items table if it doesn't exist
    if not table_exists(cursor, 'invoice_line_items'):
        print("Creating invoice_line_items table...")
        cursor.execute("""
            CREATE TABLE invoice_line_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT NOT NULL,
                invoice_id TEXT,
                line_number INTEGER NOT NULL,
                description TEXT,
                qty REAL,
                unit_price REAL,
                total REAL,
                uom TEXT,
                confidence REAL DEFAULT 0.9,
                created_at TEXT DEFAULT NULL,
                FOREIGN KEY(doc_id) REFERENCES documents(id),
                FOREIGN KEY(invoice_id) REFERENCES invoices(id)
            )
        """)
        
        # Create indexes
        print("Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_line_items_doc_id ON invoice_line_items(doc_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_line_items_invoice_id ON invoice_line_items(invoice_id)")
    
    conn.commit()
    conn.close()
    
    print("Migration completed successfully!")

if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

