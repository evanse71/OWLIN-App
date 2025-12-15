"""
Manually add pairing columns to existing database tables.

This script explicitly adds each column and handles errors gracefully.
"""
import os
import sys
import sqlite3

# Force path so imports always work
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app.db import DB_PATH

def column_exists(cursor, table, column):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())

def add_column_safe(cursor, table, column, definition):
    """Add a column if it doesn't exist"""
    if not column_exists(cursor, table, column):
        try:
            # Combine column name with definition
            full_definition = f"{column} {definition}"
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {full_definition}")
            print(f"  ✓ Added {table}.{column}")
            return True
        except sqlite3.OperationalError as e:
            print(f"  ✗ Failed to add {table}.{column}: {e}")
            return False
    else:
        print(f"  - {table}.{column} already exists")
        return True

def main():
    print("=" * 60)
    print("Adding Pairing Columns to Database")
    print("=" * 60)
    print()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("[1/5] Adding columns to invoices table...")
    add_column_safe(cursor, "invoices", "delivery_note_id", "TEXT")
    add_column_safe(cursor, "invoices", "pairing_status", "TEXT DEFAULT 'unpaired'")
    add_column_safe(cursor, "invoices", "pairing_confidence", "REAL")
    add_column_safe(cursor, "invoices", "pairing_model_version", "TEXT")
    
    # Set default pairing_status for existing rows
    if column_exists(cursor, "invoices", "pairing_status"):
        cursor.execute("""
            UPDATE invoices
            SET pairing_status = 'unpaired'
            WHERE pairing_status IS NULL
        """)
        print("  ✓ Set default pairing_status for existing invoices")
    
    print("\n[2/5] Adding columns to documents table...")
    add_column_safe(cursor, "documents", "invoice_id", "TEXT")
    
    print("\n[3/5] Creating indexes...")
    # Create indexes only if columns exist
    if column_exists(cursor, "invoices", "delivery_note_id"):
        try:
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_invoices_delivery_note_unique
                ON invoices(delivery_note_id)
                WHERE delivery_note_id IS NOT NULL
            """)
            print("  ✓ Created index on invoices.delivery_note_id")
        except Exception as e:
            print(f"  ✗ Failed to create index: {e}")
    
    if column_exists(cursor, "documents", "invoice_id"):
        try:
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_invoice_unique
                ON documents(invoice_id)
                WHERE invoice_id IS NOT NULL
            """)
            print("  ✓ Created index on documents.invoice_id")
        except Exception as e:
            print(f"  ✗ Failed to create index: {e}")
    
    if column_exists(cursor, "invoices", "pairing_status"):
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_invoices_pairing_status
                ON invoices(pairing_status)
            """)
            print("  ✓ Created index on invoices.pairing_status")
        except Exception as e:
            print(f"  ✗ Failed to create index: {e}")
    
    print("\n[4/5] Verifying tables exist...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('pairing_events', 'supplier_stats')")
    existing_tables = [row[0] for row in cursor.fetchall()]
    
    if 'pairing_events' not in existing_tables:
        print("  Creating pairing_events table...")
        cursor.execute("""
            CREATE TABLE pairing_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                invoice_id TEXT NOT NULL,
                delivery_note_id TEXT,
                action TEXT NOT NULL,
                actor_type TEXT NOT NULL,
                user_id TEXT,
                previous_delivery_note_id TEXT,
                feature_vector_json TEXT,
                model_version TEXT,
                FOREIGN KEY(invoice_id) REFERENCES invoices(id),
                FOREIGN KEY(delivery_note_id) REFERENCES documents(id),
                FOREIGN KEY(previous_delivery_note_id) REFERENCES documents(id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pairing_events_invoice_id ON pairing_events(invoice_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pairing_events_delivery_note_id ON pairing_events(delivery_note_id)")
        print("  ✓ Created pairing_events table")
    else:
        print("  - pairing_events table already exists")
    
    if 'supplier_stats' not in existing_tables:
        print("  Creating supplier_stats table...")
        cursor.execute("""
            CREATE TABLE supplier_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_id TEXT NOT NULL,
                venue_id TEXT NOT NULL DEFAULT '__default__',
                typical_delivery_weekdays TEXT,
                avg_days_between_deliveries REAL,
                std_days_between_deliveries REAL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(supplier_id, venue_id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_supplier_stats_supplier ON supplier_stats(supplier_id)")
        print("  ✓ Created supplier_stats table")
    else:
        print("  - supplier_stats table already exists")
    
    conn.commit()
    
    print("\n[5/5] Final verification...")
    # Verify all columns exist
    cursor.execute("PRAGMA table_info(invoices)")
    invoice_cols = [row[1] for row in cursor.fetchall()]
    cursor.execute("PRAGMA table_info(documents)")
    doc_cols = [row[1] for row in cursor.fetchall()]
    
    required_invoice_cols = ["delivery_note_id", "pairing_status", "pairing_confidence", "pairing_model_version"]
    required_doc_cols = ["invoice_id"]
    
    missing_invoice = [col for col in required_invoice_cols if col not in invoice_cols]
    missing_doc = [col for col in required_doc_cols if col not in doc_cols]
    
    if missing_invoice or missing_doc:
        print("\n❌ Some columns are still missing:")
        if missing_invoice:
            print(f"  invoices: {missing_invoice}")
        if missing_doc:
            print(f"  documents: {missing_doc}")
        conn.close()
        return 1
    else:
        print("\n✅ All pairing columns are present!")
        print("\nInvoices columns:")
        for col in required_invoice_cols:
            print(f"  ✓ {col}")
        print("\nDocuments columns:")
        for col in required_doc_cols:
            print(f"  ✓ {col}")
        print("\nTables:")
        print("  ✓ pairing_events")
        print("  ✓ supplier_stats")
        print("\n🚀 Pairing system is ready!")
        conn.close()
        return 0

if __name__ == "__main__":
    sys.exit(main())

