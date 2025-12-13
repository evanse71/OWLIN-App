import sqlite3
def _has_table(cur, name):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None

def apply(conn: sqlite3.Connection):
    c = conn.cursor()
    if not _has_table(c,"supplier_discounts"):
        c.execute("""CREATE TABLE supplier_discounts(
            id TEXT PRIMARY KEY,
            supplier_id TEXT NOT NULL,
            scope TEXT CHECK(scope IN('supplier','category','sku')) NOT NULL,
            kind TEXT CHECK(kind IN('percent','per_case','per_litre')) NOT NULL,
            value REAL NOT NULL,
            ruleset_id TEXT,
            created_at TEXT NOT NULL
        )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_supplier_discounts_supplier ON supplier_discounts(supplier_id)")
    conn.commit()

def rollback(conn): pass 