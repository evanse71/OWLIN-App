#!/usr/bin/env python3
"""
Quick check script for STORI invoice data after upload.
Run this after uploading the STORI PDF to verify extraction.
"""
import sqlite3
import sys

DB_PATH = "data/owlin.db"

try:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Get most recent invoice
    cur.execute("""
        SELECT id, supplier, date, value, status 
        FROM invoices 
        ORDER BY rowid DESC 
        LIMIT 1
    """)
    
    inv_row = cur.fetchone()
    if not inv_row:
        print("No invoices found in database.")
        sys.exit(0)
    
    invoice_id, supplier, date, value, status = inv_row
    print(f"Invoice ID: {invoice_id}")
    print(f"Supplier: {supplier}")
    print(f"Date: {date}")
    print(f"Value: {value} (pounds)")
    print(f"Status: {status}")
    print()
    
    # Get line items
    cur.execute("""
        SELECT invoice_id, description, qty, unit_price, total, confidence
        FROM invoice_line_items 
        WHERE invoice_id = ?
        ORDER BY line_number
    """, (invoice_id,))
    
    items = cur.fetchall()
    if items:
        print(f"Line items ({len(items)}):")
        for item in items:
            inv_id, desc, qty, unit_price, total, conf = item
            print(f"  - {desc}")
            print(f"    Qty: {qty}, Unit: £{unit_price:.2f}, Total: £{total:.2f}, Conf: {conf:.2f}")
    else:
        print("No line items found.")
    
    conn.close()
    
    # Check if this looks like STORI data
    if "Stori" in supplier:
        print("\n✓ STORI supplier detected")
    if date and date.startswith("2025-08-21"):
        print("✓ Expected date (2025-08-21)")
    if value and abs(value - 289.17) < 1.0:
        print("✓ Expected total (~£289.17)")
    if len(items) == 2:
        print("✓ Expected 2 line items")
        
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

