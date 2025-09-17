# Adds delivery note matching and audit features. Idempotent.
import sqlite3, os
from pathlib import Path

DB_PATH = os.environ.get("OWLIN_DB_PATH") or str(Path("data") / "owlin.db")

DDL = """
-- Add matching fields to delivery_notes table
ALTER TABLE delivery_notes ADD COLUMN matched_invoice_id TEXT;
ALTER TABLE delivery_notes ADD COLUMN suggested_invoice_id TEXT;
ALTER TABLE delivery_notes ADD COLUMN suggested_score REAL;
ALTER TABLE delivery_notes ADD COLUMN suggested_reason TEXT;

-- Create audit_logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    meta JSON,
    ip_address TEXT,
    user_agent TEXT
);

-- Create indexes for audit_logs
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_logs(actor);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_logs(resource_type, resource_id);

-- Create indexes for delivery note matching
CREATE INDEX IF NOT EXISTS idx_dn_matched_invoice ON delivery_notes(matched_invoice_id);
CREATE INDEX IF NOT EXISTS idx_dn_suggested_invoice ON delivery_notes(suggested_invoice_id);

-- Add foreign key constraint for matched invoice
-- Note: SQLite doesn't support adding foreign key constraints to existing tables
-- This would need to be done during table creation in a real migration
"""

def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    try:
        # Check if columns already exist before adding them
        cursor = con.cursor()
        cursor.execute("PRAGMA table_info(delivery_notes)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Add columns only if they don't exist
        if 'matched_invoice_id' not in columns:
            cursor.execute("ALTER TABLE delivery_notes ADD COLUMN matched_invoice_id TEXT")
        
        if 'suggested_invoice_id' not in columns:
            cursor.execute("ALTER TABLE delivery_notes ADD COLUMN suggested_invoice_id TEXT")
            
        if 'suggested_score' not in columns:
            cursor.execute("ALTER TABLE delivery_notes ADD COLUMN suggested_score REAL")
            
        if 'suggested_reason' not in columns:
            cursor.execute("ALTER TABLE delivery_notes ADD COLUMN suggested_reason TEXT")
        
        # Create audit_logs table and indexes
        con.executescript("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id TEXT,
                meta JSON,
                ip_address TEXT,
                user_agent TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
            CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_logs(actor);
            CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);
            CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_logs(resource_type, resource_id);
            CREATE INDEX IF NOT EXISTS idx_dn_matched_invoice ON delivery_notes(matched_invoice_id);
            CREATE INDEX IF NOT EXISTS idx_dn_suggested_invoice ON delivery_notes(suggested_invoice_id);
        """)
        
        con.commit()
        print("matching_and_audit features ensured")
    finally:
        con.close()

if __name__ == "__main__":
    main()
