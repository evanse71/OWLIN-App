# backend/db/migrations/005_supplier_discounts.py
import sqlite3

def apply(conn: sqlite3.Connection):
    cur = conn.cursor()
    
    # Check if table already exists
    cur.execute("PRAGMA table_info(supplier_discounts)")
    if cur.fetchall():
        print("Table supplier_discounts already exists, skipping")
        return
    
    cur.executescript("""
    PRAGMA foreign_keys=ON;

    -- Supplier discount rules with versioning
    CREATE TABLE IF NOT EXISTS supplier_discounts (
        id                INTEGER PRIMARY KEY,
        supplier_id       TEXT NOT NULL,
        scope             TEXT NOT NULL CHECK(scope IN ('supplier','category','sku')),
        kind              TEXT NOT NULL CHECK(kind IN ('percent','per_case','per_litre')),
        value             REAL NOT NULL,
        ruleset_id        INTEGER NOT NULL DEFAULT 1,
        created_at        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        valid_from        TEXT,
        valid_to          TEXT,
        evidence_ref      TEXT,
        UNIQUE(supplier_id, scope, kind, ruleset_id)
    );

    -- Indexes for performance
    CREATE INDEX IF NOT EXISTS idx_supplier_discounts_supplier ON supplier_discounts(supplier_id);
    CREATE INDEX IF NOT EXISTS idx_supplier_discounts_scope ON supplier_discounts(scope);
    CREATE INDEX IF NOT EXISTS idx_supplier_discounts_ruleset ON supplier_discounts(ruleset_id);
    CREATE INDEX IF NOT EXISTS idx_supplier_discounts_valid ON supplier_discounts(valid_from, valid_to);
    """)
    conn.commit()

def rollback(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.executescript("""
    DROP TABLE IF EXISTS supplier_discounts;
    """)
    conn.commit() 