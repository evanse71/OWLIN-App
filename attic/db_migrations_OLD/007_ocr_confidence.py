# backend/db/migrations/007_ocr_confidence.py
import sqlite3

def apply(conn: sqlite3.Connection):
    cur = conn.cursor()
    
    # Check if columns already exist
    cur.execute("PRAGMA table_info(invoices)")
    columns = [col[1] for col in cur.fetchall()]
    
    if 'ocr_avg_conf_page' not in columns:
        cur.execute("ALTER TABLE invoices ADD COLUMN ocr_avg_conf_page REAL")
        print("Added ocr_avg_conf_page column to invoices")
    
    if 'ocr_min_conf_line' not in columns:
        cur.execute("ALTER TABLE invoices ADD COLUMN ocr_min_conf_line REAL")
        print("Added ocr_min_conf_line column to invoices")
    
    # Add confidence column to invoice_line_items if it doesn't exist
    cur.execute("PRAGMA table_info(invoice_line_items)")
    line_columns = [col[1] for col in cur.fetchall()]
    
    if 'ocr_confidence' not in line_columns:
        cur.execute("ALTER TABLE invoice_line_items ADD COLUMN ocr_confidence REAL")
        print("Added ocr_confidence column to invoice_line_items")
    
    conn.commit()

def rollback(conn: sqlite3.Connection):
    # Note: SQLite doesn't support DROP COLUMN in older versions
    # This would require recreating the table
    print("Rollback not implemented for OCR confidence columns")
    pass 