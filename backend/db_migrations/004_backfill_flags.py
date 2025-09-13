import sqlite3

def apply(conn: sqlite3.Connection):
    """Backfill flag columns with default values"""
    cur = conn.cursor()
    
    # Check and backfill invoices table
    cur.execute("PRAGMA table_info(invoices)")
    invoice_cols = {row[1] for row in cur.fetchall()}
    
    if 'validation_flags' in invoice_cols:
        cur.execute("UPDATE invoices SET validation_flags = '[]' WHERE validation_flags IS NULL")
        print("Backfilled validation_flags in invoices")
    
    if 'canonical_quantities' in invoice_cols:
        cur.execute("UPDATE invoices SET canonical_quantities = '[]' WHERE canonical_quantities IS NULL")
        print("Backfilled canonical_quantities in invoices")
    
    if 'parsed_metadata' in invoice_cols:
        cur.execute("UPDATE invoices SET parsed_metadata = '{}' WHERE parsed_metadata IS NULL")
        print("Backfilled parsed_metadata in invoices")
    
    # Check and backfill delivery_notes table
    cur.execute("PRAGMA table_info(delivery_notes)")
    dn_cols = {row[1] for row in cur.fetchall()}
    
    if 'validation_flags' in dn_cols:
        cur.execute("UPDATE delivery_notes SET validation_flags = '[]' WHERE validation_flags IS NULL")
        print("Backfilled validation_flags in delivery_notes")
    
    if 'canonical_quantities' in dn_cols:
        cur.execute("UPDATE delivery_notes SET canonical_quantities = '[]' WHERE canonical_quantities IS NULL")
        print("Backfilled canonical_quantities in delivery_notes")
    
    if 'parsed_metadata' in dn_cols:
        cur.execute("UPDATE delivery_notes SET parsed_metadata = '{}' WHERE parsed_metadata IS NULL")
        print("Backfilled parsed_metadata in delivery_notes")
    
    # Backfill line_flags in invoice_line_items if column exists
    cur.execute("PRAGMA table_info(invoice_line_items)")
    item_cols = {row[1] for row in cur.fetchall()}
    
    if 'line_flags' in item_cols:
        cur.execute("UPDATE invoice_line_items SET line_flags = '[]' WHERE line_flags IS NULL")
        print("Backfilled line_flags in invoice_line_items")
    
    # Backfill line_flags in delivery_note_items if table and column exist
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='delivery_note_items'")
    if cur.fetchone():
        cur.execute("PRAGMA table_info(delivery_note_items)")
        dn_item_cols = {row[1] for row in cur.fetchall()}
        
        if 'line_flags' in dn_item_cols:
            cur.execute("UPDATE delivery_note_items SET line_flags = '[]' WHERE line_flags IS NULL")
            print("Backfilled line_flags in delivery_note_items")
    
    conn.commit()
    print("Backfill flags migration completed")

def rollback(conn: sqlite3.Connection):
    """Rollback backfill (set fields back to NULL)"""
    cur = conn.cursor()
    
    # Reset to NULL (optional - may want to keep the data)
    cur.execute("UPDATE invoices SET validation_flags = NULL WHERE validation_flags = '[]'")
    cur.execute("UPDATE invoices SET canonical_quantities = NULL WHERE canonical_quantities = '[]'")
    cur.execute("UPDATE invoices SET parsed_metadata = NULL WHERE parsed_metadata = '{}'")
    
    cur.execute("UPDATE delivery_notes SET validation_flags = NULL WHERE validation_flags = '[]'")
    cur.execute("UPDATE delivery_notes SET canonical_quantities = NULL WHERE canonical_quantities = '[]'")
    cur.execute("UPDATE delivery_notes SET parsed_metadata = NULL WHERE parsed_metadata = '{}'")
    
    cur.execute("UPDATE invoice_line_items SET line_flags = NULL WHERE line_flags = '[]'")
    
    conn.commit()
    print("Backfill flags rollback completed") 