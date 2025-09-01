import sqlite3

def apply(conn: sqlite3.Connection):
    """Create match links tables for line-level pairing"""
    cur = conn.cursor()
    
    # Check if tables already exist
    cur.execute("PRAGMA table_info(match_links)")
    if cur.fetchall():
        print("Match links tables already exist, skipping")
        return
    
    cur.executescript("""
    PRAGMA foreign_keys=ON;
    
    -- Document-level pairing links
    CREATE TABLE IF NOT EXISTS match_links (
        id TEXT PRIMARY KEY,
        invoice_id TEXT NOT NULL,
        dn_id TEXT NOT NULL,
        score REAL NOT NULL CHECK(score BETWEEN 0 AND 100),
        status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','confirmed','rejected')),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        confirmed_at TEXT,
        FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
        FOREIGN KEY(dn_id) REFERENCES delivery_notes(id) ON DELETE CASCADE,
        UNIQUE(invoice_id, dn_id)
    );
    
    -- Line-level pairing with reasons
    CREATE TABLE IF NOT EXISTS match_link_items (
        link_id TEXT NOT NULL,
        invoice_item_id TEXT NOT NULL,
        dn_item_id TEXT,  -- NULL for unmatched invoice lines
        reason TEXT NOT NULL,  -- PARTIAL_DELIVERY, OVER_SUPPLIED, QTY_MISMATCH, etc.
        qty_match_pct REAL,   -- 0-100, how much of invoice line is covered
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(link_id, invoice_item_id),
        FOREIGN KEY(link_id) REFERENCES match_links(id) ON DELETE CASCADE,
        FOREIGN KEY(invoice_item_id) REFERENCES invoice_items(id) ON DELETE CASCADE,
        FOREIGN KEY(dn_item_id) REFERENCES delivery_note_items(id) ON DELETE CASCADE
    );
    
    -- Indexes for performance
    CREATE INDEX IF NOT EXISTS idx_match_links_invoice ON match_links(invoice_id);
    CREATE INDEX IF NOT EXISTS idx_match_links_dn ON match_links(dn_id);
    CREATE INDEX IF NOT EXISTS idx_match_links_score ON match_links(score DESC);
    CREATE INDEX IF NOT EXISTS idx_match_link_items_invoice ON match_link_items(invoice_item_id);
    CREATE INDEX IF NOT EXISTS idx_match_link_items_dn ON match_link_items(dn_item_id);
    """)
    
    conn.commit()
    print("Match links tables created")

def rollback(conn: sqlite3.Connection):
    """Remove match links tables"""
    cur = conn.cursor()
    cur.executescript("""
    DROP TABLE IF EXISTS match_link_items;
    DROP TABLE IF EXISTS match_links;
    """)
    conn.commit()
    print("Match links tables removed") 