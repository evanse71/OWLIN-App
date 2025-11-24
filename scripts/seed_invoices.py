#!/usr/bin/env python3
"""
Seed realistic invoice data for testing price timelines.
Generates ~60 rows for TestCo and ~40 rows for VeggieFresh across 12 months.
"""

import sqlite3
import uuid
import random
import argparse
from datetime import datetime, timedelta
import os

def ensure_documents_exist(conn, doc_ids):
    """Ensure document records exist for the given doc_ids"""
    cursor = conn.cursor()
    for doc_id in doc_ids:
        cursor.execute("""
            INSERT OR IGNORE INTO documents (id, path, type, created_at)
            VALUES (?, ?, ?, ?)
        """, (doc_id, f"data/uploads/{doc_id}.pdf", "invoice", datetime.now().isoformat()))
    conn.commit()

def generate_price_series(base_price, months, trend=0.02, volatility=0.1):
    """Generate a realistic price series with trend and volatility"""
    prices = []
    current_price = base_price
    
    for i in range(months):
        # Add trend (small monthly increase)
        current_price *= (1 + trend)
        
        # Add random volatility
        noise = random.gauss(0, volatility)
        current_price *= (1 + noise)
        
        # Ensure positive prices
        current_price = max(current_price, base_price * 0.5)
        
        prices.append(round(current_price, 2))
    
    return prices

def seed_invoices(reset=False):
    """Seed invoice data for testing"""
    # Ensure database exists
    os.makedirs("data", exist_ok=True)
    
    conn = sqlite3.connect("data/owlin.db")
    cursor = conn.cursor()
    
    if reset:
        print("Resetting seeded data...")
        cursor.execute("DELETE FROM invoices WHERE supplier IN ('TestCo', 'VeggieFresh')")
        cursor.execute("DELETE FROM documents WHERE path LIKE 'data/uploads/%'")
        conn.commit()
    
    # Generate TestCo data (60 invoices over 12 months)
    print("Generating TestCo data...")
    testco_prices = generate_price_series(120, 12, trend=0.015, volatility=0.08)
    testco_doc_ids = []
    testco_count = 0
    
    for month in range(12):
        # 5 invoices per month on average
        invoices_this_month = random.randint(4, 6)
        
        for _ in range(invoices_this_month):
            doc_id = str(uuid.uuid4())
            testco_doc_ids.append(doc_id)
            
            # Random day in the month
            day = random.randint(1, 28)
            date = datetime(2024, month + 1, day).strftime("%Y-%m-%d")
            
            # Price with some variation around the monthly average
            base_price = testco_prices[month]
            price = round(base_price * random.uniform(0.95, 1.05), 2)
            
            cursor.execute("""
                INSERT OR REPLACE INTO invoices (id, document_id, supplier, invoice_date, total_value)
                VALUES (?, ?, ?, ?, ?)
            """, (doc_id, doc_id, "TestCo", date, price))
            
            testco_count += 1
    
    # Generate VeggieFresh data (40 invoices over 12 months)
    print("Generating VeggieFresh data...")
    veggiefresh_prices = generate_price_series(80, 12, trend=0.02, volatility=0.12)
    veggiefresh_doc_ids = []
    veggiefresh_count = 0
    
    for month in range(12):
        # 3-4 invoices per month on average
        invoices_this_month = random.randint(3, 4)
        
        for _ in range(invoices_this_month):
            doc_id = str(uuid.uuid4())
            veggiefresh_doc_ids.append(doc_id)
            
            # Random day in the month
            day = random.randint(1, 28)
            date = datetime(2024, month + 1, day).strftime("%Y-%m-%d")
            
            # Price with some variation around the monthly average
            base_price = veggiefresh_prices[month]
            price = round(base_price * random.uniform(0.92, 1.08), 2)
            
            cursor.execute("""
                INSERT OR REPLACE INTO invoices (id, document_id, supplier, invoice_date, total_value)
                VALUES (?, ?, ?, ?, ?)
            """, (doc_id, doc_id, "VeggieFresh", date, price))
            
            veggiefresh_count += 1
    
    # Ensure document records exist
    all_doc_ids = testco_doc_ids + veggiefresh_doc_ids
    ensure_documents_exist(conn, all_doc_ids)
    
    conn.commit()
    conn.close()
    
    print(f"Seeded {testco_count} invoices for TestCo")
    print(f"Seeded {veggiefresh_count} invoices for VeggieFresh")
    print(f"Total: {testco_count + veggiefresh_count} invoices")

def main():
    parser = argparse.ArgumentParser(description="Seed invoice data for testing")
    parser.add_argument("--reset", action="store_true", help="Reset existing seeded data first")
    args = parser.parse_args()
    
    seed_invoices(reset=args.reset)

if __name__ == "__main__":
    main()
