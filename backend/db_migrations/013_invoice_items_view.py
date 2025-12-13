import sqlite3

def _has_table(cur, name):
    cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name=?", (name,))
    return cur.fetchone() is not None

def apply(conn: sqlite3.Connection):
    c = conn.cursor()
    if _has_table(c,"invoice_line_items") and not _has_table(c,"invoice_items"):
        cols = [r[1] for r in c.execute("PRAGMA table_info(invoice_line_items)").fetchall()]
        c.execute(f"CREATE VIEW invoice_items AS SELECT {', '.join(cols)} FROM invoice_line_items")
        conn.commit()

def rollback(conn): pass 