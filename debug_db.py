#!/usr/bin/env python3
"""
Debug script to test database connection and query
"""

import os
import sqlite3

def test_db():
    """Test database connection and query"""
    
    # Test the same path logic as the backend
    DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
    DB_PATH = os.path.join(DATA_DIR, "owlin.db")
    
    print(f"Current directory: {os.getcwd()}")
    print(f"Script directory: {os.path.dirname(__file__)}")
    print(f"Data directory: {DATA_DIR}")
    print(f"Database path: {DB_PATH}")
    print(f"Database exists: {os.path.exists(DB_PATH)}")
    
    if not os.path.exists(DB_PATH):
        print("❌ Database not found!")
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Test the exact query from get_all_invoices
        cursor.execute("""
            SELECT 
                id,
                invoice_number,
                invoice_date,
                supplier_name,
                total_amount,
                status,
                confidence,
                upload_timestamp,
                parent_pdf_filename,
                page_numbers,
                line_items,
                subtotal,
                vat,
                vat_rate,
                total_incl_vat,
                ocr_text,
                page_range,
                addresses,
                signature_regions,
                verification_status
            FROM invoices
            ORDER BY upload_timestamp DESC
        """)
        
        rows = cursor.fetchall()
        print(f"✅ Query successful! Found {len(rows)} rows")
        
        for i, row in enumerate(rows):
            print(f"Row {i}: {row[:5]}...")  # Show first 5 columns
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    print("Debugging Database Connection")
    print("=" * 40)
    test_db() 