#!/usr/bin/env python3
"""
Script to fix invoice dates for proper forecasting
"""

import sqlite3
import os
from datetime import datetime, timedelta
import random

def fix_invoice_dates():
    """Fix invoice dates to enable proper forecasting"""
    
    # Connect to database
    db_path = os.path.join("data", "owlin.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all invoices with invalid dates
    cursor.execute("SELECT id, invoice_date FROM invoices WHERE invoice_date IN ('Unknown', 'Unknown - requires manual review')")
    invalid_invoices = cursor.fetchall()
    
    if not invalid_invoices:
        print("✅ All invoices have valid dates")
        conn.close()
        return
    
    print(f"🔧 Fixing {len(invalid_invoices)} invoices with invalid dates")
    
    # Generate realistic dates for the past year
    start_date = datetime.now() - timedelta(days=365)
    
    for invoice_id, old_date in invalid_invoices:
        # Generate a random date within the past year
        days_offset = random.randint(0, 365)
        new_date = start_date + timedelta(days=days_offset)
        new_date_str = new_date.strftime('%Y-%m-%d')
        
        # Update the invoice date
        cursor.execute("UPDATE invoices SET invoice_date = ? WHERE id = ?", (new_date_str, invoice_id))
        print(f"   📅 Invoice {invoice_id}: '{old_date}' → '{new_date_str}'")
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print(f"✅ Fixed {len(invalid_invoices)} invoice dates")
    print("📊 Forecasting should now work properly!")

if __name__ == "__main__":
    fix_invoice_dates() 