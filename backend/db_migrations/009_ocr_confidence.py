import sqlite3

def _col(cur, table, col):
    cur.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in cur.fetchall())

def _has_table(cur, name):
    cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name=?", (name,))
    return cur.fetchone() is not None

def apply(conn: sqlite3.Connection):
    c = conn.cursor()

    # invoices roll-up columns
    for col, typ in (("ocr_avg_conf","REAL"), ("ocr_min_conf","REAL")):
        if _has_table(c,"invoices") and not _col(c,"invoices",col):
            c.execute(f"ALTER TABLE invoices ADD COLUMN {col} {typ}")

    # invoice_pages table (create minimal if absent)
    if not _has_table(c,"invoice_pages"):
        c.execute("""CREATE TABLE invoice_pages(
            id TEXT PRIMARY KEY,
            invoice_id TEXT NOT NULL,
            page_no INTEGER NOT NULL
        )""")

    # per-page confidence
    for col, typ in (("ocr_avg_conf_page","REAL"), ("ocr_min_conf_line","REAL")):
        if not _col(c,"invoice_pages",col):
            c.execute(f"ALTER TABLE invoice_pages ADD COLUMN {col} {typ}")

    conn.commit()

def rollback(conn): pass 