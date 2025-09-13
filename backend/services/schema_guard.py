# backend/services/schema_guard.py
from threading import Lock
from backend.db import get_engine
import sqlite3
from pathlib import Path

_lock = Lock()
_done = False

def ensure_schema_once():
    global _done
    if _done: 
        return
    with _lock:
        if _done: 
            return
        
        # Use SQLite directly for schema setup (simpler than SQLAlchemy for this case)
        db_path = Path("data/owlin.db")
        db_path.parent.mkdir(exist_ok=True)
        
        with sqlite3.connect(str(db_path)) as conn:
            c = conn.cursor()
            
            # Create invoices table
            c.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    id TEXT PRIMARY KEY,
                    supplier_id TEXT NOT NULL,
                    supplier_name TEXT NOT NULL,
                    invoice_date TEXT NOT NULL,
                    invoice_ref TEXT NOT NULL,
                    currency TEXT DEFAULT 'GBP',
                    status TEXT DEFAULT 'manual_entered',
                    entry_mode TEXT DEFAULT 'manual',
                    total_net TEXT,
                    total_vat TEXT,
                    total_gross TEXT,
                    notes TEXT,
                    meta_json TEXT
                )
            """)
            
            # Create delivery_notes table
            c.execute("""
                CREATE TABLE IF NOT EXISTS delivery_notes (
                    id TEXT PRIMARY KEY,
                    supplier_id TEXT NOT NULL,
                    supplier_name TEXT NOT NULL,
                    delivery_date TEXT NOT NULL,
                    delivery_ref TEXT NOT NULL,
                    currency TEXT DEFAULT 'GBP',
                    status TEXT DEFAULT 'manual_entered',
                    entry_mode TEXT DEFAULT 'manual',
                    notes TEXT,
                    meta_json TEXT
                )
            """)
            
            # Create audit_log table
            c.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY,
                    ts TEXT NOT NULL DEFAULT (datetime('now')),
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    entity TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    details_json TEXT NOT NULL
                )
            """)
            
            # Create invoice_delivery_links table
            c.execute("""
                CREATE TABLE IF NOT EXISTS invoice_delivery_links (
                    id INTEGER PRIMARY KEY,
                    invoice_id TEXT NOT NULL,
                    delivery_note_id TEXT NOT NULL,
                    linked_at TEXT NOT NULL DEFAULT (datetime('now')),
                    linked_by TEXT NOT NULL,
                    UNIQUE(invoice_id, delivery_note_id),
                    FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
                    FOREIGN KEY(delivery_note_id) REFERENCES delivery_notes(id) ON DELETE CASCADE
                )
            """)
            
            conn.commit()
        
        _done = True
