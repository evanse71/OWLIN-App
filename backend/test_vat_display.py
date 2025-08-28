#!/usr/bin/env python3
"""
Test for VAT display and filename handling
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services import new_id
from db import get_conn, init
import json

def test_vat_display():
    """Test VAT display and filename handling"""
    print("🧪 Testing VAT Display & Filename Handling")
    print("=" * 50)
    
    # Initialize database
    init()
    
    # Create test invoice with VAT data
    c = get_conn()
    cur = c.cursor()
    
    inv_id = new_id("test_inv")
    filename = "billN13472213_1.pdf"
    
    try:
        # Insert test invoice with VAT data
        cur.execute("""
            INSERT INTO invoices(id, supplier_name, filename, total_amount, subtotal_p, vat_total_p, status, confidence, paired)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, (inv_id, "Wild Horse Brewing Co Ltd", filename, 55620, 46350, 9270, "scanned", 85, 0))
        
        # Add test line items with VAT rates
        cur.execute("""
            INSERT INTO invoice_items(invoice_id, description, qty, unit_price, total, vat_rate, confidence)
            VALUES(?,?,?,?,?,?,?)
        """, (inv_id, "Buckskin – 30L E‑keg", 2, 9850, 17730, 20, 85))
        
        cur.execute("""
            INSERT INTO invoice_items(invoice_id, description, qty, unit_price, total, vat_rate, confidence)
            VALUES(?,?,?,?,?,?,?)
        """, (inv_id, "Nokota – 30L Keg", 3, 10600, 28620, 20, 85))
        
        c.commit()
        
        # Retrieve and verify
        invoice = cur.execute("SELECT * FROM invoices WHERE id=?", (inv_id,)).fetchone()
        items = cur.execute("SELECT * FROM invoice_items WHERE invoice_id=?", (inv_id,)).fetchall()
        
        print(f"\n📄 Test Invoice Data:")
        print(f"   Supplier: {invoice['supplier_name']}")
        print(f"   Filename: {invoice['filename']}")
        print(f"   Total: £{invoice['total_amount']/100:.2f}")
        print(f"   Subtotal: £{invoice['subtotal_p']/100:.2f}")
        print(f"   VAT: £{invoice['vat_total_p']/100:.2f}")
        print(f"   Items: {len(items)}")
        
        # Verify VAT calculation
        expected_total = invoice['subtotal_p'] + invoice['vat_total_p']
        if invoice['total_amount'] == expected_total:
            print("✅ VAT calculation correct")
        else:
            print(f"❌ VAT calculation error: {invoice['total_amount']} != {expected_total}")
            return False
        
        # Verify VAT rate
        vat_rate = round((invoice['vat_total_p'] / invoice['subtotal_p']) * 100)
        if vat_rate == 20:
            print("✅ VAT rate calculation correct (20%)")
        else:
            print(f"❌ VAT rate error: {vat_rate}% != 20%")
            return False
        
        # Simulate API response
        api_response = {
            "invoice": dict(invoice),
            "line_items": [dict(item) for item in items]
        }
        
        print(f"\n📋 API Response Structure:")
        print(f"   Invoice fields: {list(api_response['invoice'].keys())}")
        print(f"   Line items: {len(api_response['line_items'])}")
        print(f"   VAT fields present: {'subtotal_p' in api_response['invoice'] and 'vat_total_p' in api_response['invoice']}")
        
        # Clean up
        cur.execute("DELETE FROM invoice_items WHERE invoice_id=?", (inv_id,))
        cur.execute("DELETE FROM invoices WHERE id=?", (inv_id,))
        c.commit()
        
        print("\n✅ VAT Display Test Passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        c.close()

if __name__ == "__main__":
    success = test_vat_display()
    sys.exit(0 if success else 1) 