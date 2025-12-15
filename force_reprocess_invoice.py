#!/usr/bin/env python3
"""
Force re-process an invoice by deleting it from the database and clearing OCR cache.
This ensures the new extraction code runs with fresh data.
"""
import sqlite3
import os
import shutil
from pathlib import Path

DB_PATH = "backend/data/owlin.db"
UPLOADS_DIR = Path("backend/data/uploads")

def find_invoice_by_supplier(supplier_name: str):
    """Find invoice IDs matching supplier name"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check actual schema
    cursor.execute("PRAGMA table_info(invoices)")
    columns = [row[1] for row in cursor.fetchall()]
    
    # Use correct column names based on actual schema
    if 'supplier_name' in columns:
        supplier_col = 'supplier_name'
    elif 'supplier' in columns:
        supplier_col = 'supplier'
    else:
        supplier_col = None
    
    if 'file_id' in columns:
        doc_id_col = 'file_id'
    elif 'doc_id' in columns:
        doc_id_col = 'doc_id'
    else:
        doc_id_col = 'id'  # Fallback
    
    if supplier_col:
        cursor.execute(f"""
            SELECT id, {doc_id_col}, {supplier_col}, invoice_number, invoice_date, total_amount
            FROM invoices
            WHERE {supplier_col} LIKE ?
            ORDER BY invoice_date DESC
            LIMIT 10
        """, (f"%{supplier_name}%",))
    else:
        cursor.execute(f"""
            SELECT id, {doc_id_col}, 'Unknown' as supplier, invoice_number, invoice_date, total_amount
            FROM invoices
            LIMIT 10
        """)
    
    results = cursor.fetchall()
    conn.close()
    
    return results

def delete_invoice(doc_id: str):
    """Delete invoice and its line items from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check schema
    cursor.execute("PRAGMA table_info(invoices)")
    columns = [row[1] for row in cursor.fetchall()]
    
    doc_id_col = 'file_id' if 'file_id' in columns else ('doc_id' if 'doc_id' in columns else 'id')
    
    # Try to find invoice by file_id/doc_id first
    cursor.execute(f"SELECT id FROM invoices WHERE {doc_id_col} = ?", (doc_id,))
    invoice_row = cursor.fetchone()
    
    # If not found, try using doc_id as invoice id
    if not invoice_row:
        cursor.execute("SELECT id FROM invoices WHERE id = ?", (doc_id,))
        invoice_row = cursor.fetchone()
    
    if invoice_row:
        invoice_id = invoice_row[0]
        
        # Delete line items (try both doc_id and invoice_id)
        cursor.execute("DELETE FROM invoice_line_items WHERE doc_id = ?", (doc_id,))
        deleted_items = cursor.rowcount
        if deleted_items > 0:
            print(f"  ✓ Deleted {deleted_items} line items by doc_id")
        
        cursor.execute("DELETE FROM invoice_line_items WHERE invoice_id = ?", (invoice_id,))
        deleted_items = cursor.rowcount
        if deleted_items > 0:
            print(f"  ✓ Deleted {deleted_items} line items by invoice_id")
        
        # Delete invoice
        cursor.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
        print(f"  ✓ Deleted invoice id={invoice_id}")
        
        # Delete document if table exists
        try:
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            print(f"  ✓ Deleted document doc_id={doc_id}")
        except:
            pass
        
        conn.commit()
        conn.close()
        return True
    else:
        # Try deleting by doc_id directly
        cursor.execute(f"DELETE FROM invoices WHERE {doc_id_col} = ?", (doc_id,))
        cursor.execute("DELETE FROM invoice_line_items WHERE doc_id = ?", (doc_id,))
        try:
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        except:
            pass
        conn.commit()
        conn.close()
        return False

def clear_ocr_cache(doc_id: str):
    """Delete OCR cache folder for this document"""
    cache_folders = list(UPLOADS_DIR.glob(f"*{doc_id}*"))
    
    if not cache_folders:
        # Try finding by supplier name in folder names
        cache_folders = list(UPLOADS_DIR.glob("*stori*"))
        cache_folders.extend(list(UPLOADS_DIR.glob("*Stori*")))
    
    deleted_count = 0
    for folder in cache_folders:
        if folder.is_dir():
            try:
                shutil.rmtree(folder)
                print(f"  ✓ Deleted cache folder: {folder.name}")
                deleted_count += 1
            except Exception as e:
                print(f"  ✗ Failed to delete {folder.name}: {e}")
    
    return deleted_count

def main():
    print("=" * 70)
    print("FORCE RE-PROCESS INVOICE")
    print("=" * 70)
    print()
    
    # Find Stori invoices
    print("🔍 Searching for Stori invoices...")
    invoices = find_invoice_by_supplier("Stori")
    
    if not invoices:
        print("❌ No Stori invoices found in database")
        return
    
    print(f"\n📋 Found {len(invoices)} invoice(s):")
    for idx, (invoice_id, doc_id, supplier, inv_no, date, value) in enumerate(invoices, 1):
        print(f"  {idx}. {supplier}")
        print(f"     Invoice: {inv_no or 'N/A'}")
        print(f"     Doc ID: {doc_id}")
        print(f"     Date: {date}")
        print(f"     Value: £{value:.2f}")
        print()
    
    # Process first invoice (or ask user)
    if len(invoices) == 1:
        doc_id = invoices[0][1]
        print(f"🎯 Processing invoice: {invoices[0][2]}")
    else:
        # Use first one
        doc_id = invoices[0][1]
        print(f"🎯 Processing first invoice: {invoices[0][2]}")
    
    print(f"\n🗑️  Deleting invoice from database (doc_id={doc_id})...")
    if delete_invoice(doc_id):
        print("  ✅ Invoice deleted from database")
    else:
        print("  ⚠️  Invoice not found in database (may already be deleted)")
    
    print(f"\n🗑️  Clearing OCR cache...")
    deleted = clear_ocr_cache(doc_id)
    if deleted > 0:
        print(f"  ✅ Deleted {deleted} cache folder(s)")
    else:
        print("  ⚠️  No cache folders found (may already be cleared)")
    
    print("\n" + "=" * 70)
    print("✅ RE-PROCESSING READY")
    print("=" * 70)
    print("\n📤 Next steps:")
    print("  1. Re-upload the Stori invoice PDF via the UI")
    print("  2. The new extraction code will run with fresh data")
    print("  3. You should see:")
    print("     - Real invoice number (852021_162574)")
    print("     - Product descriptions (not 'Unknown item')")
    print("     - Correct quantities (8, 2)")
    print("     - Correct totals")
    print()

if __name__ == "__main__":
    main()

