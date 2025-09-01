# backend/db/migrations/006_match_link_items.py
import sqlite3

def apply(conn: sqlite3.Connection):
    cur = conn.cursor()
    
    # Check if table already exists
    cur.execute("PRAGMA table_info(match_link_items)")
    if cur.fetchall():
        print("Table match_link_items already exists, skipping")
        return
    
    cur.executescript("""
    PRAGMA foreign_keys=ON;

    -- Line-level matching evidence and reasons
    CREATE TABLE IF NOT EXISTS match_link_items (
        id                 INTEGER PRIMARY KEY,
        match_id           INTEGER NOT NULL REFERENCES match_links(id) ON DELETE CASCADE,
        invoice_line_id    INTEGER,
        delivery_line_id   INTEGER,
        reason             TEXT NOT NULL,
        weight             REAL DEFAULT 0,
        score_contribution REAL DEFAULT 0,
        created_at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(match_id, invoice_line_id, delivery_line_id)
    );

    -- Indexes for performance
    CREATE INDEX IF NOT EXISTS idx_match_link_items_match ON match_link_items(match_id);
    CREATE INDEX IF NOT EXISTS idx_match_link_items_invoice ON match_link_items(invoice_line_id);
    CREATE INDEX IF NOT EXISTS idx_match_link_items_delivery ON match_link_items(delivery_line_id);
    CREATE INDEX IF NOT EXISTS idx_match_link_items_reason ON match_link_items(reason);
    """)
    conn.commit()

def rollback(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.executescript("""
    DROP TABLE IF EXISTS match_link_items;
    """)
    conn.commit() 