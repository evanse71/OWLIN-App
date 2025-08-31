#!/usr/bin/env python3
"""
Test VAT system functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_manager_unified import get_db_manager

def test_vat_system():
    """Test VAT system functionality"""
    try:
        db_manager = get_db_manager()
        
        with db_manager.get_connection() as conn:
            # Test VAT system logic
            cursor = conn.execute("SELECT * FROM invoices WHERE vat_rate IS NOT NULL LIMIT 1")
            invoice = cursor.fetchone()
            
            if invoice:
                print(f"✅ Found invoice with VAT: {invoice['id']}")
                print(f"   VAT Rate: {invoice.get('vat_rate', 'N/A')}")
                print(f"   VAT Total: {invoice.get('vat_total_pennies', 'N/A')}")
                print(f"   Subtotal: {invoice.get('subtotal_pennies', 'N/A')}")
                print(f"   Total: {invoice.get('total_amount_pennies', 'N/A')}")
            else:
                print("ℹ️ No invoices with VAT found in database")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_vat_system() 