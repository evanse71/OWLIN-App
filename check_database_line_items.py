#!/usr/bin/env python3
"""
Diagnostic script to check database for line items after upload.

Usage:
    python check_database_line_items.py [doc_id]
    
If doc_id is not provided, shows the latest invoice.
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = "data/owlin.db"

def check_latest_invoice():
    """Check the latest invoice and its line items."""
    if not Path(DB_PATH).exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        return None
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Get the latest invoice
        cursor.execute("""
            SELECT 
                i.id, 
                i.doc_id,
                i.supplier, 
                i.date, 
                i.value,
                i.status,
                i.created_at,
                (SELECT COUNT(*) FROM invoice_line_items WHERE doc_id = i.doc_id) as line_item_count
            FROM invoices i
            ORDER BY i.id DESC
            LIMIT 1
        """)
        
        invoice = cursor.fetchone()
        
        if not invoice:
            print("No invoices found in database")
            return None
        
        print("=" * 60)
        print("Latest Invoice")
        print("=" * 60)
        print(f"ID: {invoice['id']}")
        print(f"Doc ID: {invoice['doc_id']}")
        print(f"Supplier: {invoice['supplier']}")
        print(f"Date: {invoice['date']}")
        print(f"Value: £{invoice['value']:.2f}")
        print(f"Status: {invoice['status']}")
        print(f"Created: {invoice['created_at']}")
        print(f"Line Items Count: {invoice['line_item_count']}")
        print()
        
        # Get line items if any
        if invoice['line_item_count'] > 0:
            cursor.execute("""
                SELECT 
                    line_number,
                    description,
                    qty,
                    unit_price,
                    total,
                    uom,
                    confidence
                FROM invoice_line_items
                WHERE doc_id = ?
                ORDER BY line_number
            """, (invoice['doc_id'],))
            
            items = cursor.fetchall()
            print(f"Line Items ({len(items)}):")
            print("-" * 60)
            for item in items:
                print(f"  Line {item['line_number']}: {item['description']}")
                print(f"    Qty: {item['qty']}, Unit Price: £{item['unit_price']:.2f}, Total: £{item['total']:.2f}")
                print(f"    UOM: {item['uom']}, Confidence: {item['confidence']:.3f}")
        else:
            print("⚠ No line items found for this invoice")
        
        return invoice['doc_id']
        
    except Exception as e:
        print(f"ERROR: Database query failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        conn.close()

def check_specific_doc(doc_id: str):
    """Check a specific document by doc_id."""
    if not Path(DB_PATH).exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                i.id, 
                i.doc_id,
                i.supplier, 
                i.date, 
                i.value,
                i.status,
                (SELECT COUNT(*) FROM invoice_line_items WHERE doc_id = i.doc_id) as line_item_count
            FROM invoices i
            WHERE i.doc_id = ?
        """, (doc_id,))
        
        invoice = cursor.fetchone()
        
        if not invoice:
            print(f"No invoice found with doc_id: {doc_id}")
            return
        
        print("=" * 60)
        print(f"Invoice: {doc_id}")
        print("=" * 60)
        print(f"Supplier: {invoice['supplier']}")
        print(f"Date: {invoice['date']}")
        print(f"Value: £{invoice['value']:.2f}")
        print(f"Status: {invoice['status']}")
        print(f"Line Items Count: {invoice['line_item_count']}")
        print()
        
        if invoice['line_item_count'] > 0:
            cursor.execute("""
                SELECT 
                    line_number,
                    description,
                    qty,
                    unit_price,
                    total,
                    confidence
                FROM invoice_line_items
                WHERE doc_id = ?
                ORDER BY line_number
            """, (doc_id,))
            
            items = cursor.fetchall()
            print(f"Line Items:")
            for item in items:
                print(f"  {item['line_number']}. {item['description']} - Qty: {item['qty']}, Price: £{item['unit_price']:.2f}, Total: £{item['total']:.2f}")
        else:
            print("⚠ No line items found")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

def main():
    if len(sys.argv) > 1:
        doc_id = sys.argv[1]
        check_specific_doc(doc_id)
    else:
        doc_id = check_latest_invoice()
        if doc_id:
            print("\n" + "=" * 60)
            print("To check this specific document:")
            print(f"  python check_database_line_items.py {doc_id}")
            print("\nTo check API response:")
            print(f"  curl 'http://localhost:8000/api/upload/status?doc_id={doc_id}' | jq")

if __name__ == "__main__":
    main()

