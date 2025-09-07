#!/usr/bin/env python3
"""
Seed script for supplier scorecard testing.
Creates 3 suppliers with different performance profiles.
"""

import sqlite3
import os
from datetime import datetime, timedelta
from uuid import uuid4

DB_PATH = "data/owlin.db"

def seed_suppliers():
    """Seed the database with test supplier data."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Clear existing test data
    cursor.execute("DELETE FROM invoices WHERE supplier_name LIKE 'Test%'")
    cursor.execute("DELETE FROM delivery_notes WHERE supplier_name LIKE 'Test%'")
    cursor.execute("DELETE FROM flagged_issues WHERE supplier_name LIKE 'Test%'")
    
    # Supplier A (Balanced) - Good performance
    supplier_a = "Test Supplier A"
    
    # Add invoices for Supplier A
    for i in range(10):
        date = datetime.now() - timedelta(days=i*3)
        cursor.execute("""
            INSERT INTO invoices (id, invoice_number, invoice_date, supplier_name, total_amount, status, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            f"inv_a_{i}",
            f"INV-A-{i:03d}",
            date.strftime("%Y-%m-%d"),
            supplier_a,
            1000.0 + (i * 50),  # Varying amounts
            "matched",
            0.88 + (i * 0.01)  # High confidence
        ))
    
    # Add delivery notes for Supplier A (mostly on time)
    for i in range(8):
        date = datetime.now() - timedelta(days=i*3)
        cursor.execute("""
            INSERT INTO delivery_notes (id, delivery_note_number, delivery_date, supplier_name, status)
            VALUES (?, ?, ?, ?, ?)
        """, (
            f"dn_a_{i}",
            f"DN-A-{i:03d}",
            date.strftime("%Y-%m-%d"),
            supplier_a,
            "matched"
        ))
    
    # Supplier B (Problematic) - Poor performance
    supplier_b = "Test Supplier B"
    
    # Add invoices for Supplier B
    for i in range(8):
        date = datetime.now() - timedelta(days=i*4)
        cursor.execute("""
            INSERT INTO invoices (id, invoice_number, invoice_date, supplier_name, total_amount, status, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            f"inv_b_{i}",
            f"INV-B-{i:03d}",
            date.strftime("%Y-%m-%d"),
            supplier_b,
            500.0 + (i * 200),  # More volatile amounts
            "matched",
            0.65 + (i * 0.02)  # Lower confidence
        ))
    
    # Add delivery notes for Supplier B (mostly late)
    for i in range(3):
        date = datetime.now() - timedelta(days=i*4)
        cursor.execute("""
            INSERT INTO delivery_notes (id, delivery_note_number, delivery_date, supplier_name, status)
            VALUES (?, ?, ?, ?, ?)
        """, (
            f"dn_b_{i}",
            f"DN-B-{i:03d}",
            date.strftime("%Y-%m-%d"),
            supplier_b,
            "unmatched"  # Late deliveries
        ))
    
    # Add flagged issues for Supplier B
    for i in range(3):
        cursor.execute("""
            INSERT INTO flagged_issues (id, invoice_id, supplier_name, type, created_at, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            f"issue_b_{i}",
            f"inv_b_{i}",
            supplier_b,
            "credit",
            (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
            (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        ))
    
    # Supplier C (Stable, high share) - Excellent performance
    supplier_c = "Test Supplier C"
    
    # Add invoices for Supplier C (high volume)
    for i in range(20):
        date = datetime.now() - timedelta(days=i*2)
        cursor.execute("""
            INSERT INTO invoices (id, invoice_number, invoice_date, supplier_name, total_amount, status, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            f"inv_c_{i}",
            f"INV-C-{i:03d}",
            date.strftime("%Y-%m-%d"),
            supplier_c,
            2000.0 + (i * 25),  # High, stable amounts
            "matched",
            0.93 + (i * 0.005)  # Very high confidence
        ))
    
    # Add delivery notes for Supplier C (all on time)
    for i in range(18):
        date = datetime.now() - timedelta(days=i*2)
        cursor.execute("""
            INSERT INTO delivery_notes (id, delivery_note_number, delivery_date, supplier_name, status)
            VALUES (?, ?, ?, ?, ?)
        """, (
            f"dn_c_{i}",
            f"DN-C-{i:03d}",
            date.strftime("%Y-%m-%d"),
            supplier_c,
            "matched"
        ))
    
    conn.commit()
    conn.close()
    
    print("✅ Seeded suppliers:")
    print(f"  - {supplier_a}: Balanced performance (10 invoices, 8 deliveries)")
    print(f"  - {supplier_b}: Problematic performance (8 invoices, 3 deliveries, 3 issues)")
    print(f"  - {supplier_c}: Excellent performance (20 invoices, 18 deliveries)")
    print("\nTest with:")
    print(f"  curl -s 'http://localhost:8000/api/suppliers/{supplier_a}/scorecard'")
    print(f"  curl -s 'http://localhost:8000/api/suppliers/{supplier_b}/scorecard'")
    print(f"  curl -s 'http://localhost:8000/api/suppliers/{supplier_c}/scorecard'")

if __name__ == "__main__":
    seed_suppliers() 