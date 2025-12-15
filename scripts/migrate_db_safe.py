"""
Safely migrate the database by adding pairing columns without deleting the file.

This works even if the backend is running (database is locked).
"""
import os
import sys

# Force path so imports always work
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app.db import init_db, DB_PATH
import sqlite3

def main():
    print("=" * 60)
    print("Owlin Database Migration (Safe Mode)")
    print("=" * 60)
    print("\nThis will add pairing columns to existing tables.")
    print("Your existing data will be preserved.\n")
    
    # Initialize DB (this adds columns safely)
    print("[MIGRATE] Adding pairing schema to existing database...")
    try:
        init_db()
        print("[MIGRATE] ✓ Migration completed successfully")
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        return 1
    
    # Verify schema
    print("\n[VERIFY] Verifying schema...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # Check invoices columns
        cur.execute("PRAGMA table_info(invoices)")
        invoice_cols = [row[1] for row in cur.fetchall()]
        print(f"\n[VERIFY] Invoices columns ({len(invoice_cols)}):")
        for col in invoice_cols:
            marker = "✓" if col in ["delivery_note_id", "pairing_status", "pairing_confidence", "pairing_model_version"] else " "
            print(f"  {marker} {col}")
        
        # Check documents columns
        cur.execute("PRAGMA table_info(documents)")
        doc_cols = [row[1] for row in cur.fetchall()]
        print(f"\n[VERIFY] Documents columns ({len(doc_cols)}):")
        for col in doc_cols:
            marker = "✓" if col == "invoice_id" else " "
            print(f"  {marker} {col}")
        
        # Check for pairing tables
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cur.fetchall()]
        print(f"\n[VERIFY] Database tables ({len(tables)}):")
        for table in tables:
            marker = "✓" if table in ["pairing_events", "supplier_stats"] else " "
            print(f"  {marker} {table}")
        
        conn.close()
        
        # Final verification
        required_invoice_cols = ["delivery_note_id", "pairing_status", "pairing_confidence", "pairing_model_version"]
        required_doc_cols = ["invoice_id"]
        required_tables = ["pairing_events", "supplier_stats"]
        
        missing_invoice_cols = [col for col in required_invoice_cols if col not in invoice_cols]
        missing_doc_cols = [col for col in required_doc_cols if col not in doc_cols]
        missing_tables = [table for table in required_tables if table not in tables]
        
        if missing_invoice_cols or missing_doc_cols or missing_tables:
            print("\n" + "=" * 60)
            print("❌ SCHEMA VERIFICATION FAILED")
            print("=" * 60)
            if missing_invoice_cols:
                print(f"Missing invoices columns: {missing_invoice_cols}")
            if missing_doc_cols:
                print(f"Missing documents columns: {missing_doc_cols}")
            if missing_tables:
                print(f"Missing tables: {missing_tables}")
            return 1
        else:
            print("\n" + "=" * 60)
            print("✅ SCHEMA VERIFICATION PASSED")
            print("=" * 60)
            print("\nAll pairing system components are present:")
            print("  ✓ invoices.delivery_note_id")
            print("  ✓ invoices.pairing_status")
            print("  ✓ invoices.pairing_confidence")
            print("  ✓ invoices.pairing_model_version")
            print("  ✓ documents.invoice_id")
            print("  ✓ pairing_events table")
            print("  ✓ supplier_stats table")
            print("\n🚀 Pairing system is ready!")
            return 0
    except Exception as e:
        print(f"[ERROR] Verification failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

