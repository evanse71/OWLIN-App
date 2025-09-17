#!/usr/bin/env python3
"""
Backfill script to ensure all existing invoices have at least one page row.
This fixes the issue where invoices exist but have no corresponding invoice_pages entries.
"""
import sqlite3
import json
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import from backend
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import execute, fetch_all

def main():
    """Backfill missing invoice_pages entries for existing invoices."""
    print("Starting invoice pages backfill...")
    
    # Find invoices without any pages
    missing_invoices = fetch_all("""
        SELECT i.id
        FROM invoices i
        LEFT JOIN invoice_pages p ON p.invoice_id = i.id
        GROUP BY i.id
        HAVING COUNT(p.id) = 0
    """)
    
    if not missing_invoices:
        print("No invoices need backfilling.")
        return
    
    print(f"Found {len(missing_invoices)} invoices without page entries.")
    
    # Add page 0 for each missing invoice
    for invoice in missing_invoices:
        inv_id = invoice["id"]
        execute(
            "INSERT INTO invoice_pages (id, invoice_id, page_no, ocr_json) VALUES (?, ?, 0, json('{}'))",
            (f"backfill-{inv_id}", inv_id),
        )
        print(f"Added page 0 for invoice {inv_id}")
    
    print(f"Successfully backfilled {len(missing_invoices)} invoices with page 0.")

if __name__ == "__main__":
    main()