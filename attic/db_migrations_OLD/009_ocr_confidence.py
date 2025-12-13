import sqlite3

def apply(conn: sqlite3.Connection):
    """Add OCR confidence tracking columns"""
    cur = conn.cursor()
    
    # Check if columns already exist in invoice_pages
    cur.execute("PRAGMA table_info(invoice_pages)")
    existing_cols = {row[1] for row in cur.fetchall()}
    
    if 'ocr_avg_conf_page' not in existing_cols:
        cur.execute("ALTER TABLE invoice_pages ADD COLUMN ocr_avg_conf_page REAL")
        print("Added ocr_avg_conf_page to invoice_pages")
    
    if 'ocr_min_conf_line' not in existing_cols:
        cur.execute("ALTER TABLE invoice_pages ADD COLUMN ocr_min_conf_line REAL")
        print("Added ocr_min_conf_line to invoice_pages")
    
    # Check if columns already exist in invoices
    cur.execute("PRAGMA table_info(invoices)")
    existing_cols = {row[1] for row in cur.fetchall()}
    
    if 'ocr_avg_conf' not in existing_cols:
        cur.execute("ALTER TABLE invoices ADD COLUMN ocr_avg_conf REAL")
        print("Added ocr_avg_conf to invoices")
    
    if 'ocr_min_conf' not in existing_cols:
        cur.execute("ALTER TABLE invoices ADD COLUMN ocr_min_conf REAL")
        print("Added ocr_min_conf to invoices")
    
    # Add indexes for confidence queries
    cur.execute("CREATE INDEX IF NOT EXISTS idx_invoices_ocr_conf ON invoices(ocr_avg_conf)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_invoice_pages_ocr_conf ON invoice_pages(ocr_avg_conf_page)")
    
    conn.commit()
    print("OCR confidence columns added")

def rollback(conn: sqlite3.Connection):
    """Remove OCR confidence columns (SQLite doesn't support DROP COLUMN)"""
    print("SQLite doesn't support DROP COLUMN - manual cleanup required")
    # In production, would recreate tables without these columns 