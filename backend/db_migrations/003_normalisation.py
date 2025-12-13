import sqlite3

def apply(conn: sqlite3.Connection):
    """Add normalisation fields to tables"""
    cur = conn.cursor()
    
    # Add fields to invoices table
    cur.execute("PRAGMA table_info(invoices)")
    invoice_cols = {row[1] for row in cur.fetchall()}
    
    if 'validation_flags' not in invoice_cols:
        cur.execute("ALTER TABLE invoices ADD COLUMN validation_flags TEXT DEFAULT '[]'")
        print("Added validation_flags to invoices")
    
    if 'canonical_quantities' not in invoice_cols:
        cur.execute("ALTER TABLE invoices ADD COLUMN canonical_quantities TEXT DEFAULT '[]'")
        print("Added canonical_quantities to invoices")
    
    if 'parsed_metadata' not in invoice_cols:
        cur.execute("ALTER TABLE invoices ADD COLUMN parsed_metadata TEXT DEFAULT '{}'")
        print("Added parsed_metadata to invoices")
    
    # Add fields to delivery_notes table
    cur.execute("PRAGMA table_info(delivery_notes)")
    dn_cols = {row[1] for row in cur.fetchall()}
    
    if 'validation_flags' not in dn_cols:
        cur.execute("ALTER TABLE delivery_notes ADD COLUMN validation_flags TEXT DEFAULT '[]'")
        print("Added validation_flags to delivery_notes")
    
    if 'canonical_quantities' not in dn_cols:
        cur.execute("ALTER TABLE delivery_notes ADD COLUMN canonical_quantities TEXT DEFAULT '[]'")
        print("Added canonical_quantities to delivery_notes")
    
    if 'parsed_metadata' not in dn_cols:
        cur.execute("ALTER TABLE delivery_notes ADD COLUMN parsed_metadata TEXT DEFAULT '{}'")
        print("Added parsed_metadata to delivery_notes")
    
    # Add fields to invoice_line_items table
    cur.execute("PRAGMA table_info(invoice_line_items)")
    item_cols = {row[1] for row in cur.fetchall()}
    
    new_columns = [
        ('uom_key', 'TEXT'),
        ('packs', 'REAL'),
        ('units_per_pack', 'REAL'),
        ('quantity_each', 'REAL'),
        ('unit_size_ml', 'REAL'),
        ('unit_size_g', 'REAL'),
        ('unit_size_l', 'REAL'),
        ('quantity_ml', 'REAL'),
        ('quantity_g', 'REAL'),
        ('quantity_l', 'REAL'),
        ('line_flags', 'TEXT DEFAULT \'[]\''),
        ('discount_kind', 'TEXT'),
        ('discount_value', 'REAL'),
        ('discount_residual_pennies', 'INTEGER'),
        ('implied_discount_pct', 'REAL')
    ]
    
    for col_name, col_type in new_columns:
        if col_name not in item_cols:
            cur.execute(f"ALTER TABLE invoice_line_items ADD COLUMN {col_name} {col_type}")
            print(f"Added {col_name} to invoice_line_items")
    
    # Add fields to delivery_note_items table if it exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='delivery_note_items'")
    if cur.fetchone():
        cur.execute("PRAGMA table_info(delivery_note_items)")
        dn_item_cols = {row[1] for row in cur.fetchall()}
        
        dn_new_columns = [
            ('uom_key', 'TEXT'),
            ('packs', 'REAL'),
            ('units_per_pack', 'REAL'),
            ('quantity_each', 'REAL'),
            ('unit_size_ml', 'REAL'),
            ('unit_size_g', 'REAL'),
            ('unit_size_l', 'REAL'),
            ('quantity_ml', 'REAL'),
            ('quantity_g', 'REAL'),
            ('quantity_l', 'REAL'),
            ('line_flags', 'TEXT DEFAULT \'[]\'')
        ]
        
        for col_name, col_type in dn_new_columns:
            if col_name not in dn_item_cols:
                cur.execute(f"ALTER TABLE delivery_note_items ADD COLUMN {col_name} {col_type}")
                print(f"Added {col_name} to delivery_note_items")
    
    # Create index if missing
    cur.execute("CREATE INDEX IF NOT EXISTS idx_processing_logs_stage ON processing_logs(stage)")
    
    conn.commit()
    print("Normalisation migration completed")

def rollback(conn: sqlite3.Connection):
    """Rollback normalisation migration (SQLite limitation)"""
    print("SQLite doesn't support DROP COLUMN - manual cleanup required") 