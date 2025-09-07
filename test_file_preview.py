#!/usr/bin/env python3
"""
Test script for file preview functionality.
"""

import sqlite3
import os
from datetime import datetime
import uuid

def add_sample_invoice_data():
    """Add sample invoice data to the database for testing."""
    db_path = "data/owlin.db"
    
    # Get a list of PDF files from the uploads directory
    uploads_dir = "data/uploads"
    pdf_files = [f for f in os.listdir(uploads_dir) if f.endswith('.pdf')]
    
    if not pdf_files:
        print("No PDF files found in uploads directory")
        return
    
    # Take the first few PDF files
    sample_files = pdf_files[:5]
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for i, filename in enumerate(sample_files):
        invoice_id = str(uuid.uuid4())
        invoice_number = f"INV-{i+1:03d}"
        supplier_name = f"Supplier {i+1}"
        total_amount = 100.0 + (i * 50.0)
        
        cursor.execute("""
            INSERT INTO invoices (
                id, invoice_number, invoice_date, supplier_name, 
                total_amount, status, confidence, upload_timestamp, 
                parent_pdf_filename
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            invoice_id,
            invoice_number,
            datetime.now().strftime("%Y-%m-%d"),
            supplier_name,
            total_amount,
            "processed",
            0.95,
            datetime.now().isoformat(),
            filename
        ))
    
    conn.commit()
    conn.close()
    
    print(f"Added {len(sample_files)} sample invoices to database")
    return sample_files

def test_file_listing():
    """Test the file listing endpoint."""
    import requests
    
    try:
        response = requests.get("http://localhost:8000/api/files")
        print(f"File listing response: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Found {len(data.get('files', []))} files")
            for file in data.get('files', []):
                print(f"  - {file.get('filename')} (ID: {file.get('id')})")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error testing file listing: {e}")

def test_file_preview(invoice_id):
    """Test the file preview endpoint."""
    import requests
    
    try:
        response = requests.get(f"http://localhost:8000/api/files/{invoice_id}/preview")
        print(f"File preview response: {response.status_code}")
        if response.status_code == 200:
            print("File preview successful")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error testing file preview: {e}")

if __name__ == "__main__":
    print("Adding sample data to database...")
    sample_files = add_sample_invoice_data()
    
    print("\nTesting file listing endpoint...")
    test_file_listing()
    
    # Test preview with the first invoice ID
    if sample_files:
        print("\nTesting file preview endpoint...")
        # Get the first invoice ID from the database
        conn = sqlite3.connect("data/owlin.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM invoices LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        
        if row:
            test_file_preview(row[0]) 