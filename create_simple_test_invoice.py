#!/usr/bin/env python3
"""
Simple script to create one test invoice for UI testing
"""

import sqlite3
import uuid
from datetime import datetime, timedelta
import json

def create_test_invoice():
    """Create one test invoice for UI testing"""
    
    # Connect to database
    conn = sqlite3.connect('data/owlin.db')
    cursor = conn.cursor()
    
    try:
        # Create a simple test invoice
        invoice_id = f"TEST-INV-{uuid.uuid4().hex[:8]}"
        
        # Sample line items
        line_items = [
            {
                "description": "Fresh Tomatoes",
                "quantity": 50,
                "unit": "kg",
                "unit_price": 2.50,
                "vat_rate": 0.20,
                "line_total": 125.00,
                "page": 1,
                "row_idx": 1,
                "confidence": 0.95,
                "flags": []
            },
            {
                "description": "Organic Lettuce",
                "quantity": 30,
                "unit": "kg", 
                "unit_price": 1.80,
                "vat_rate": 0.20,
                "line_total": 54.00,
                "page": 1,
                "row_idx": 2,
                "confidence": 0.92,
                "flags": []
            }
        ]
        
        # Sample addresses
        addresses = {
            "supplier_address": "Fresh Foods Ltd\n123 Market Street\nLondon, UK",
            "delivery_address": "OWLIN Restaurant\n456 High Street\nLondon, UK"
        }
        
        # Insert test invoice
        cursor.execute('''
            INSERT OR REPLACE INTO invoices 
            (id, invoice_number, invoice_date, supplier_name, total_amount, status, 
             confidence, upload_timestamp, line_items, addresses, verification_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            invoice_id,
            "INV-2024-001",
            datetime.now().strftime('%Y-%m-%d'),
            "Fresh Foods Ltd",
            179.00,  # total_amount
            "processed",
            0.95,    # confidence
            datetime.now().isoformat(),
            json.dumps(line_items),  # line_items as JSON
            json.dumps(addresses),   # addresses as JSON
            "unreviewed"
        ))
        
        conn.commit()
        print(f"✅ Created test invoice: {invoice_id}")
        print(f"   Invoice Number: INV-2024-001")
        print(f"   Supplier: Fresh Foods Ltd")
        print(f"   Total: £179.00")
        print(f"   Line Items: {len(line_items)}")
        
    except Exception as e:
        print(f"❌ Error creating test invoice: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("Creating Simple Test Invoice for UI Testing")
    print("=" * 50)
    create_test_invoice()
    print("\n🎉 Test invoice creation completed!") 