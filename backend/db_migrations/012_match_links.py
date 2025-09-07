import sqlite3

def _has_table(cur, name):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None

def apply(conn: sqlite3.Connection):
    c = conn.cursor()
    if not _has_table(c,"match_links"):
        c.execute("""CREATE TABLE match_links(
            id TEXT PRIMARY KEY,
            invoice_id TEXT NOT NULL,
            dn_id TEXT NOT NULL,
            score REAL,
            created_at TEXT
        )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_match_links_inv ON match_links(invoice_id)")

    if not _has_table(c,"match_link_items"):
        c.execute("""CREATE TABLE match_link_items(
            link_id TEXT NOT NULL,
            invoice_item_id TEXT NOT NULL,
            dn_item_id TEXT,
            reason TEXT,                 -- PARTIAL_DELIVERY | OVER_SUPPLIED | QTY_MISMATCH
            qty_match_pct REAL,
            PRIMARY KEY(link_id, invoice_item_id)
        )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_match_link_items_link ON match_link_items(link_id)")
    conn.commit()

def rollback(conn): pass 