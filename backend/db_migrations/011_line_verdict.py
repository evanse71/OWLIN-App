import sqlite3

def _col(cur, table, col):
    cur.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in cur.fetchall())

def _has_table(cur, name):
    cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name=?", (name,))
    return cur.fetchone() is not None

def apply(conn: sqlite3.Connection):
    c = conn.cursor()

    # Canonical & discount columns should already exist; enforce verdict column
    if _has_table(c, "invoice_line_items"):
        if not _col(c, "invoice_line_items", "line_verdict"):
            c.execute("ALTER TABLE invoice_line_items ADD COLUMN line_verdict TEXT")
        # compatibility view for scripts expecting invoice_items
        if not _has_table(c, "invoice_items"):
            # project all columns transparently
            cols = [r[1] for r in c.execute("PRAGMA table_info(invoice_line_items)").fetchall()]
            c.execute(f"CREATE VIEW invoice_items AS SELECT {', '.join(cols)} FROM invoice_line_items")
    else:
        # last-ditch: create minimal table if truly missing (should not happen in real repo)
        c.execute("""CREATE TABLE invoice_line_items(
            id TEXT PRIMARY KEY,
            invoice_id TEXT,
            sku TEXT, desc TEXT,
            quantity_each REAL, packs REAL, units_per_pack REAL,
            quantity_ml REAL, quantity_l REAL, quantity_g REAL,
            unit_price REAL, nett_price REAL, line_total REAL,
            discount_kind TEXT, discount_value REAL, discount_residual_pennies INTEGER,
            line_flags TEXT, line_verdict TEXT
        )""")
        c.execute("CREATE VIEW invoice_items AS SELECT * FROM invoice_line_items")

    conn.commit()

def rollback(conn): pass 