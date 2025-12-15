#!/usr/bin/env python3
"""
Debug script to trace OCR pipeline execution for a real PDF.

This script exercises the same code path as /api/upload → process_document_ocr,
but runs in-process for easier debugging.

Usage:
    python scripts/debug_ocr_runtime.py <path_to_pdf>
    
    Or set TEST_PDF_PATH environment variable:
    $env:TEST_PDF_PATH="data/uploads/test_invoice.pdf"
    python scripts/debug_ocr_runtime.py
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.ocr_service import process_document_ocr
from backend.app.db import get_line_items_for_doc, init_db, DB_PATH
import sqlite3

def debug_ocr(file_path: str):
    """Run OCR pipeline and print detailed debug output."""
    print("=" * 80)
    print("OWLIN OCR RUNTIME DEBUG")
    print("=" * 80)
    print(f"Test file: {file_path}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Verify file exists
    file_path = Path(file_path).resolve()
    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        return
    
    print(f"File exists: {file_path}")
    print(f"File size: {file_path.stat().st_size} bytes")
    print()
    
    # Initialize database
    print("Initializing database...")
    init_db()
    print("Database initialized.")
    print()
    
    # Generate a test doc_id
    import uuid
    doc_id = str(uuid.uuid4())
    print(f"Generated doc_id: {doc_id}")
    print()
    
    # Insert a temporary document record
    from backend.app.db import insert_document
    try:
        insert_document(
            doc_id=doc_id,
            filename=file_path.name,
            stored_path=str(file_path),
            size_bytes=file_path.stat().st_size
        )
        print(f"Inserted document record: doc_id={doc_id}")
    except Exception as e:
        print(f"WARNING: Failed to insert document record: {e}")
        print("Continuing anyway...")
    print()
    
    # Run OCR processing
    print("=" * 80)
    print("RUNNING OCR PIPELINE")
    print("=" * 80)
    print()
    
    try:
        result = process_document_ocr(doc_id, str(file_path))
        
        print("=" * 80)
        print("OCR RESULT SUMMARY")
        print("=" * 80)
        print(f"Status: {result.get('status')}")
        print(f"Doc ID: {result.get('doc_id')}")
        print(f"Confidence: {result.get('confidence', 0.0)}")
        print(f"Error: {result.get('error', 'None')}")
        print()
        
        # Check database state
        print("=" * 80)
        print("DATABASE STATE")
        print("=" * 80)
        
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # Get document
        try:
            cur.execute("""
                SELECT id, filename, status, ocr_stage, ocr_confidence, ocr_error
                FROM documents
                WHERE id = ?
            """, (doc_id,))
            doc_row = cur.fetchone()
            if doc_row:
                print(f"Document found:")
                print(f"  ID: {doc_row[0]}")
                print(f"  Filename: {doc_row[1]}")
                print(f"  Status: {doc_row[2] if doc_row[2] else 'None'}")
                print(f"  OCR Stage: {doc_row[3] if doc_row[3] else 'None'}")
                print(f"  OCR Confidence: {doc_row[4] if doc_row[4] is not None else 'None'}")
                print(f"  OCR Error: {doc_row[5] if doc_row[5] else 'None'}")
            else:
                print("WARNING: Document not found in database")
        except sqlite3.OperationalError as e:
            print(f"WARNING: Error querying document: {e}")
        print()
        
        # Get invoice
        try:
            cur.execute("""
                SELECT id, supplier, date, value, invoice_number, confidence, status
                FROM invoices
                WHERE id = ?
            """, (doc_id,))
            inv_row = cur.fetchone()
            if inv_row:
                print(f"Invoice found:")
                print(f"  ID: {inv_row[0]}")
                print(f"  Supplier: {inv_row[1]}")
                print(f"  Date: {inv_row[2]}")
                print(f"  Total: {inv_row[3]}")
                print(f"  Invoice Number: {inv_row[4] if inv_row[4] else 'None'}")
                print(f"  Confidence: {inv_row[5] if inv_row[5] is not None else 'None'}")
                print(f"  Status: {inv_row[6] if inv_row[6] else 'None'}")
            else:
                print("WARNING: Invoice not found in database")
        except sqlite3.OperationalError as e:
            print(f"WARNING: Error querying invoice: {e}")
        print()
        
        conn.close()
        
        line_items = get_line_items_for_doc(doc_id)
        print(f"Line items count: {len(line_items)}")
        if line_items:
            print("Sample line items (first 3):")
            for i, item in enumerate(line_items[:3]):
                print(f"  {i+1}. {item.get('description', 'N/A')[:50]}")
                print(f"     Qty: {item.get('qty')}, Unit: {item.get('unit_price')}, Total: {item.get('total')}")
        else:
            print("WARNING: No line items found")
        print()
        
        # Print full result JSON (truncated)
        print("=" * 80)
        print("FULL RESULT (JSON)")
        print("=" * 80)
        result_json = json.dumps(result, indent=2, default=str)
        # Truncate if too long
        if len(result_json) > 5000:
            print(result_json[:5000])
            print("\n... (truncated)")
        else:
            print(result_json)
        print()
        
        # Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"[OK] OCR pipeline executed: {result.get('status') != 'error'}")
        print(f"[OK] Document in DB: {doc_row is not None}")
        print(f"[OK] Invoice in DB: {inv_row is not None}")
        print(f"[OK] Line items extracted: {len(line_items)} items")
        print(f"[OK] Confidence: {result.get('confidence', 0.0):.3f}")
        
        if result.get('status') == 'error':
            print(f"\n[ERROR] {result.get('error')}")
        elif result.get('confidence', 0.0) == 0.0:
            print("\n[WARNING] Confidence is 0.0 - OCR may have failed")
        elif len(line_items) == 0:
            print("\n[WARNING] No line items extracted")
        else:
            print("\n[SUCCESS] OCR pipeline completed with data")
        
    except Exception as e:
        print("=" * 80)
        print("EXCEPTION DURING OCR PROCESSING")
        print("=" * 80)
        import traceback
        print(f"Error: {e}")
        print()
        print("Traceback:")
        traceback.print_exc()
        print()

if __name__ == "__main__":
    # Get file path from command line or environment
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = os.getenv("TEST_PDF_PATH")
        if not file_path:
            print("ERROR: No file path provided.")
            print("Usage: python scripts/debug_ocr_runtime.py <path_to_pdf>")
            print("   Or: $env:TEST_PDF_PATH='path/to/file.pdf'; python scripts/debug_ocr_runtime.py")
            sys.exit(1)
    
    debug_ocr(file_path)

