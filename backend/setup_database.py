#!/usr/bin/env python3
"""
Database setup script for Owlin invoice management system.
Creates necessary tables for the complete upload → scan → match flow.
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import random
import numpy as np
import uuid
import os

DB_PATH = "data/owlin.db"

def create_tables():
    """Create the necessary tables for the complete invoice management system."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create uploaded_files table (tracks all uploaded files)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS uploaded_files (
            id TEXT PRIMARY KEY,
            original_filename TEXT NOT NULL,
            file_type TEXT NOT NULL,  -- 'invoice', 'delivery_note', 'receipt'
            file_path TEXT NOT NULL,
            file_size INTEGER,
            upload_timestamp TEXT NOT NULL,
            processing_status TEXT DEFAULT 'pending',  -- 'pending', 'processing', 'completed', 'failed', 'reviewed', 'escalated'
            extracted_text TEXT,
            confidence REAL,
            processed_images INTEGER,
            extraction_timestamp TEXT,
            error_message TEXT,
            reviewed_by TEXT,
            reviewed_at TEXT
        )
    """)
    
    # Create invoices table (processed invoice data)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            invoice_number TEXT,
            invoice_date TEXT,
            supplier_name TEXT,
            total_amount REAL,
            currency TEXT DEFAULT 'GBP',
            status TEXT DEFAULT 'pending',  -- 'pending', 'scanned', 'matched', 'unmatched', 'error', 'reviewed'
            confidence REAL,
            upload_timestamp TEXT NOT NULL,
            processing_timestamp TEXT,
            delivery_note_id TEXT,  -- Foreign key to delivery_notes
            venue TEXT,
            reviewed_by TEXT,
            reviewed_at TEXT,
            FOREIGN KEY (file_id) REFERENCES uploaded_files (id),
            FOREIGN KEY (delivery_note_id) REFERENCES delivery_notes (id)
        )
    """)
    
    # Create delivery_notes table (processed delivery note data)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS delivery_notes (
            id TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            delivery_note_number TEXT,
            delivery_date TEXT,
            supplier_name TEXT,
            status TEXT DEFAULT 'pending',  -- 'pending', 'scanned', 'matched', 'unmatched', 'error', 'reviewed'
            confidence REAL,
            upload_timestamp TEXT NOT NULL,
            processing_timestamp TEXT,
            invoice_id TEXT,  -- Foreign key to invoices
            reviewed_by TEXT,
            reviewed_at TEXT,
            FOREIGN KEY (file_id) REFERENCES uploaded_files (id),
            FOREIGN KEY (invoice_id) REFERENCES invoices (id)
        )
    """)
    
    # Create invoice_line_items table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoice_line_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id TEXT NOT NULL,
            item_description TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit_price REAL NOT NULL,
            total_price REAL NOT NULL,
            source TEXT DEFAULT 'ocr',  -- 'ocr', 'manual', 'corrected'
            confidence REAL,
            flagged BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (invoice_id) REFERENCES invoices (id)
        )
    """)
    
    # Create delivery_line_items table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS delivery_line_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            delivery_note_id TEXT NOT NULL,
            item_description TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit_price REAL NOT NULL,
            total_price REAL NOT NULL,
            source TEXT DEFAULT 'ocr',  -- 'ocr', 'manual', 'corrected'
            confidence REAL,
            flagged BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (delivery_note_id) REFERENCES delivery_notes (id)
        )
    """)
    
    # Create price_forecasting tables (existing - keep for compatibility)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_forecasting_invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT NOT NULL,
            supplier_name TEXT NOT NULL,
            invoice_date DATE NOT NULL,
            total_amount REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_forecasting_line_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            item TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit_price REAL NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY (invoice_id) REFERENCES price_forecasting_invoices (id)
        )
    """)
    
    # Create indexes for better performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_uploaded_files_type_status ON uploaded_files (file_type, processing_status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices (status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_delivery_notes_status ON delivery_notes (status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_supplier_date ON invoices (supplier_name, invoice_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_delivery_notes_supplier_date ON delivery_notes (supplier_name, delivery_date)")
    
    conn.commit()
    conn.close()
    print("✅ Database tables created successfully")

def generate_sample_data():
    """Generate realistic sample data for the complete invoice management system."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Sample products with realistic price ranges and trends
    products = {
        'Milk': {'base_price': 1.20, 'volatility': 0.15, 'trend': 0.02},
        'Carrots': {'base_price': 0.80, 'volatility': 0.25, 'trend': 0.05},
        'Pork Shoulder': {'base_price': 3.50, 'volatility': 0.30, 'trend': -0.01},
        'Chicken Breast': {'base_price': 2.80, 'volatility': 0.20, 'trend': 0.03},
        'Tomatoes': {'base_price': 1.50, 'volatility': 0.40, 'trend': 0.08},
        'Potatoes': {'base_price': 0.60, 'volatility': 0.10, 'trend': 0.01},
        'Onions': {'base_price': 0.70, 'volatility': 0.20, 'trend': 0.02},
        'Bread': {'base_price': 1.10, 'volatility': 0.08, 'trend': 0.015},
    }
    
    suppliers = ['Fresh Foods Ltd', 'Quality Meats Co', 'Green Grocers Inc', 'Farm Fresh Supply']
    
    # Generate 18 months of data (from 2023-01 to 2024-06)
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2024, 6, 30)
    
    invoice_id = 1
    current_date = start_date
    
    while current_date <= end_date:
        # Generate 2-4 invoices per month
        invoices_per_month = random.randint(2, 4)
        
        for _ in range(invoices_per_month):
            supplier = random.choice(suppliers)
            invoice_date = current_date + timedelta(days=random.randint(0, 28))
            
            # Create uploaded file record
            file_id = f"FILE-{uuid.uuid4().hex[:8]}"
            cursor.execute("""
                INSERT INTO uploaded_files 
                (id, original_filename, file_type, file_path, file_size, upload_timestamp, processing_status, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_id,
                f"INV-{invoice_id:04d}.pdf",
                'invoice',
                f"uploads/invoices/INV-{invoice_id:04d}.pdf",
                1024 * 1024,  # 1MB
                invoice_date.isoformat(),
                'completed',
                0.85 + random.random() * 0.15  # 85-100% confidence
            ))
            
            # Insert invoice
            cursor.execute("""
                INSERT INTO price_forecasting_invoices (invoice_number, supplier_name, invoice_date, total_amount)
                VALUES (?, ?, ?, ?)
            """, (f"INV-{invoice_id:04d}", supplier, invoice_date.strftime('%Y-%m-%d'), 0.0))
            
            # Generate line items for this invoice
            total_amount = 0.0
            items_in_invoice = random.sample(list(products.keys()), random.randint(2, 5))
            
            for item in items_in_invoice:
                product_info = products[item]
                
                # Calculate price with trend and seasonal effects
                months_since_start = (current_date.year - 2023) * 12 + current_date.month - 1
                trend_factor = 1 + (product_info['trend'] * months_since_start)
                
                # Add seasonal variation (higher prices in winter for some items)
                seasonal_factor = 1.0
                if current_date.month in [12, 1, 2]:  # Winter months
                    if item in ['Milk', 'Bread']:
                        seasonal_factor = 1.1  # 10% higher in winter
                    elif item in ['Tomatoes', 'Carrots']:
                        seasonal_factor = 1.2  # 20% higher in winter
                
                # Add random volatility
                volatility_factor = 1 + random.uniform(-product_info['volatility'], product_info['volatility'])
                
                # Calculate final price
                unit_price = product_info['base_price'] * trend_factor * seasonal_factor * volatility_factor
                unit_price = max(0.1, unit_price)  # Ensure positive price
                
                quantity = random.uniform(1, 10)
                price = unit_price * quantity
                total_amount += price
                
                # Insert line item
                cursor.execute("""
                    INSERT INTO price_forecasting_line_items (invoice_id, item, quantity, unit_price, price)
                    VALUES (?, ?, ?, ?, ?)
                """, (invoice_id, item, quantity, unit_price, price))
            
            # Update invoice total
            cursor.execute("""
                UPDATE price_forecasting_invoices SET total_amount = ? WHERE id = ?
            """, (total_amount, invoice_id))
            
            invoice_id += 1
        
        # Move to next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
    
    conn.commit()
    conn.close()
    print(f"✅ Generated {invoice_id - 1} invoices with realistic price data")

def verify_data():
    """Verify the generated data looks realistic."""
    conn = sqlite3.connect(DB_PATH)
    
    # Check total records
    invoices_count = pd.read_sql("SELECT COUNT(*) as count FROM price_forecasting_invoices", conn).iloc[0]['count']
    line_items_count = pd.read_sql("SELECT COUNT(*) as count FROM price_forecasting_line_items", conn).iloc[0]['count']
    
    print(f"📊 Database contains:")
    print(f"   - {invoices_count} invoices")
    print(f"   - {line_items_count} line items")
    
    # Show sample price trends
    sample_products = ['Milk', 'Carrots', 'Pork Shoulder']
    for product in sample_products:
        query = """
        SELECT 
            strftime('%Y-%m', i.invoice_date) as month,
            AVG(li.unit_price) as avg_price,
            COUNT(*) as transactions
        FROM price_forecasting_line_items li
        JOIN price_forecasting_invoices i ON li.invoice_id = i.id
        WHERE li.item = ?
        GROUP BY strftime('%Y-%m', i.invoice_date)
        ORDER BY month
        """
        df = pd.read_sql(query, conn, params=(product,))
        print(f"\n📈 {product} price trends:")
        print(df.to_string(index=False))
    
    conn.close()

if __name__ == "__main__":
    print("🚀 Setting up Owlin invoice management database...")
    create_tables()
    generate_sample_data()
    verify_data()
    print("\n✅ Database setup complete! Ready for invoice management.") 