#!/usr/bin/env python3
"""
Sample Data Creation Script
Creates sample invoices and delivery notes for testing the enhanced UI.
"""

import sqlite3
import os
import uuid
from datetime import datetime, timedelta
import random

def get_db_connection():
    """Get database connection."""
    db_path = os.path.join("data", "owlin.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return sqlite3.connect(db_path, check_same_thread=False)

def create_sample_data():
    """Create sample invoices and delivery notes."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Sample suppliers
    suppliers = [
        "Fresh Foods Ltd",
        "Quality Meats Co",
        "Organic Produce Inc",
        "Beverage Solutions",
        "Kitchen Supplies Pro"
    ]
    
    # Sample invoice data
    sample_invoices = [
        {
            'invoice_number': 'INV-2024-001',
            'supplier': 'Fresh Foods Ltd',
            'total': 1250.50,
            'status': 'matched',
            'has_delivery_note': True
        },
        {
            'invoice_number': 'INV-2024-002',
            'supplier': 'Quality Meats Co',
            'total': 890.75,
            'status': 'discrepancy',
            'has_delivery_note': True
        },
        {
            'invoice_number': 'INV-2024-003',
            'supplier': 'Organic Produce Inc',
            'total': 567.25,
            'status': 'not_paired',
            'has_delivery_note': False
        },
        {
            'invoice_number': 'INV-2024-004',
            'supplier': 'Beverage Solutions',
            'total': 2340.00,
            'status': 'matched',
            'has_delivery_note': True
        },
        {
            'invoice_number': 'INV-2024-005',
            'supplier': 'Kitchen Supplies Pro',
            'total': 445.80,
            'status': 'pending',
            'has_delivery_note': False
        }
    ]
    
    # Create sample uploaded files first
    for i, invoice_data in enumerate(sample_invoices):
        # Create file record
        file_id = f"FILE-{uuid.uuid4().hex[:8]}"
        cursor.execute('''
            INSERT OR REPLACE INTO uploaded_files 
            (id, original_filename, file_type, file_path, file_size, confidence, 
             processing_status, upload_timestamp, extracted_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            file_id,
            f"{invoice_data['invoice_number']}.pdf",
            'invoice',
            f"uploads/invoices/{invoice_data['invoice_number']}.pdf",
            1024 * 1024,  # 1MB
            0.85 + random.random() * 0.15,  # 85-100% confidence
            'completed',
            (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
            f"Sample extracted text for {invoice_data['invoice_number']}"
        ))
        
        # Create invoice record
        invoice_id = f"INV-{uuid.uuid4().hex[:8]}"
        cursor.execute('''
            INSERT OR REPLACE INTO invoices 
            (id, invoice_number, invoice_date, supplier, total_amount, status, 
             file_id, confidence, upload_timestamp, processing_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            invoice_id,
            invoice_data['invoice_number'],
            (datetime.now() - timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d'),
            invoice_data['supplier'],
            invoice_data['total'],
            invoice_data['status'],
            file_id,
            0.85 + random.random() * 0.15,
            (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
            'completed'
        ))
        
        # Create delivery note if paired
        if invoice_data['has_delivery_note']:
            # Create delivery note file
            dn_file_id = f"DN-FILE-{uuid.uuid4().hex[:8]}"
            cursor.execute('''
                INSERT OR REPLACE INTO uploaded_files 
                (id, original_filename, file_type, file_path, file_size, confidence, 
                 processing_status, upload_timestamp, extracted_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                dn_file_id,
                f"DN-{invoice_data['invoice_number']}.pdf",
                'delivery_note',
                f"uploads/delivery_notes/DN-{invoice_data['invoice_number']}.pdf",
                1024 * 1024,  # 1MB
                0.85 + random.random() * 0.15,  # 85-100% confidence
                'completed',
                (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
                f"Sample extracted text for delivery note DN-{invoice_data['invoice_number']}"
            ))
            
            # Create delivery note record
            delivery_note_id = f"DN-{uuid.uuid4().hex[:8]}"
            cursor.execute('''
                INSERT OR REPLACE INTO delivery_notes 
                (id, delivery_number, delivery_date, supplier, invoice_id, file_id, 
                 confidence, upload_timestamp, processing_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                delivery_note_id,
                f"DN-{invoice_data['invoice_number']}",
                (datetime.now() - timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d'),
                invoice_data['supplier'],
                invoice_id,
                dn_file_id,
                0.85 + random.random() * 0.15,
                (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
                'completed'
            ))
    
    # Create some sample line items
    sample_items = [
        ('Fresh Tomatoes', 50, 2.50, 125.00),
        ('Organic Lettuce', 30, 1.80, 54.00),
        ('Premium Beef', 25, 15.60, 390.00),
        ('Chicken Breast', 40, 8.75, 350.00),
        ('Carrots', 60, 1.20, 72.00),
        ('Onions', 45, 0.80, 36.00),
        ('Soft Drinks', 100, 1.50, 150.00),
        ('Bottled Water', 80, 0.75, 60.00),
        ('Cooking Oil', 20, 12.00, 240.00),
        ('Spices Mix', 15, 8.50, 127.50)
    ]
    
    # Get invoice IDs to add line items
    cursor.execute('SELECT id FROM invoices')
    invoice_ids = [row[0] for row in cursor.fetchall()]
    
    for invoice_id in invoice_ids:
        # Add 3-5 random line items per invoice
        num_items = random.randint(3, 5)
        selected_items = random.sample(sample_items, num_items)
        
        for item_name, qty, price, total in selected_items:
            cursor.execute('''
                INSERT OR REPLACE INTO invoice_line_items 
                (invoice_id, item, qty, price, total, delivery_qty, flagged, source, upload_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                invoice_id,
                item_name,
                qty,
                price,
                total,
                qty + random.randint(-5, 5),  # Slight variation for delivery qty
                random.choice([0, 1]),  # Some items flagged
                'invoice',
                datetime.now().isoformat()
            ))
    
    conn.commit()
    conn.close()
    
    print("✅ Sample data created successfully!")
    print(f"📄 Created {len(sample_invoices)} sample invoices")
    print(f"📦 Created {sum(1 for inv in sample_invoices if inv['has_delivery_note'])} paired delivery notes")
    print(f"📋 Created sample line items for all invoices")

def main():
    """Main function to create sample data."""
    print("Creating Sample Data for Enhanced Invoice UI")
    print("=" * 50)
    
    try:
        create_sample_data()
        print("\n🎉 Sample data creation completed!")
        print("\nYou can now run the Streamlit app to see the enhanced UI:")
        print("streamlit run app/main.py")
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")

if __name__ == "__main__":
    main() 