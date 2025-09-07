import sqlite3

def apply(conn: sqlite3.Connection):
    """Add line verdict column to invoice_items"""
    cur = conn.cursor()
    
    # Check if column already exists
    cur.execute("PRAGMA table_info(invoice_items)")
    existing_cols = {row[1] for row in cur.fetchall()}
    
    if 'line_verdict' not in existing_cols:
        cur.execute("ALTER TABLE invoice_items ADD COLUMN line_verdict TEXT")
        print("Added line_verdict to invoice_items")
    
    # Add index for verdict queries
    cur.execute("CREATE INDEX IF NOT EXISTS idx_invoice_items_verdict ON invoice_items(line_verdict)")
    
    conn.commit()
    print("Line verdict column added")

def rollback(conn: sqlite3.Connection):
    """Remove line verdict column (SQLite limitation)"""
    print("SQLite doesn't support DROP COLUMN - manual cleanup required") 