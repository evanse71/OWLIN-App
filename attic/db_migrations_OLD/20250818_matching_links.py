# backend/db/migrations/20250818_matching_links.py
import sqlite3

def apply(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.executescript("""
    PRAGMA foreign_keys=ON;

    -- Links created by the pairing engine at invoice level
    CREATE TABLE IF NOT EXISTS match_links (
        id                INTEGER PRIMARY KEY,
        invoice_id        INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
        delivery_note_id  INTEGER NOT NULL REFERENCES delivery_notes(id) ON DELETE CASCADE,
        level             TEXT    NOT NULL CHECK(level IN ('invoice','document','line')),
        score             REAL    NOT NULL DEFAULT 0,
        created_at        TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    -- Optional per-line evidence behind a link (reasons/weights)
    CREATE TABLE IF NOT EXISTS match_link_items (
        id                 INTEGER PRIMARY KEY,
        match_id           INTEGER NOT NULL REFERENCES match_links(id) ON DELETE CASCADE,
        invoice_line_id    INTEGER,
        delivery_line_id   INTEGER,
        reason             TEXT,
        weight             REAL DEFAULT 0,
        UNIQUE(match_id, invoice_line_id, delivery_line_id)
    );

    CREATE INDEX IF NOT EXISTS idx_match_links_invoice ON match_links(invoice_id);
    CREATE INDEX IF NOT EXISTS idx_match_links_delivery ON match_links(delivery_note_id);
    CREATE INDEX IF NOT EXISTS idx_match_link_items_match ON match_link_items(match_id);
    """)
    conn.commit()

def rollback(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.executescript("""
    DROP TABLE IF EXISTS match_link_items;
    DROP TABLE IF EXISTS match_links;
    """)
    conn.commit() 