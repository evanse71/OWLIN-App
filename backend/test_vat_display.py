#!/usr/bin/env python3
"""
Test VAT display functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_manager_unified import get_db_manager

def test_vat_display():
    """Test VAT display functionality"""
    try:
        db_manager = get_db_manager()
        
        with db_manager.get_connection() as c:
            # Test VAT display logic
            cursor = c.execute("SELECT * FROM invoices LIMIT 1")
            invoice = cursor.fetchone()
            
            if invoice:
                print(f"✅ Found invoice: {invoice['id']}")
                print(f"   VAT Rate: {invoice.get('vat_rate', 'N/A')}")
                print(f"   VAT Total: {invoice.get('vat_total_pennies', 'N/A')}")
                print(f"   Total Amount: {invoice.get('total_amount_pennies', 'N/A')}")
            else:
                print("ℹ️ No invoices found in database")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_vat_display() 