#!/usr/bin/env python3
"""
Simple test of the pairing system functions
"""

import sys
import os
sys.path.append('.')

# Import the pairing functions from the backend
from test_backend_simple import (
    db_insert_document, 
    maybe_create_pair_suggestions, 
    db_list_pairs,
    classify_doc
)

def test_pairing():
    print("Testing pairing system...")
    
    # Test document classification
    print("Testing document classification...")
    invoice_type = classify_doc("INVOICE INV-1001 SUP Acme", "invoice.pdf")
    dn_type = classify_doc("DELIVERY DN-1001 SUP Acme", "delivery.pdf")
    print(f"Invoice type: {invoice_type}")
    print(f"Delivery note type: {dn_type}")
    
    # Test document insertion
    print("Testing document insertion...")
    invoice_doc = {
        "sha256": "test_invoice_123",
        "filename": "invoice.pdf",
        "bytes": 100,
        "supplier": "Acme Corp",
        "invoice_no": "INV-1001",
        "delivery_no": None,
        "doc_date": "2025-01-01",
        "total": 542.10,
        "currency": "USD",
        "doc_type": "invoice"
    }
    
    try:
        invoice_id = db_insert_document(invoice_doc)
        print(f"Invoice document inserted with ID: {invoice_id}")
        
        # Create delivery note
        dn_doc = {
            "sha256": "test_dn_123",
            "filename": "delivery.pdf",
            "bytes": 100,
            "supplier": "Acme Corp",
            "invoice_no": None,
            "delivery_no": "DN-1001",
            "doc_date": "2025-01-02",
            "total": 542.10,
            "currency": "USD",
            "doc_type": "delivery_note"
        }
        
        dn_id = db_insert_document(dn_doc)
        print(f"Delivery note document inserted with ID: {dn_id}")
        
        # Test pairing suggestions
        print("Testing pairing suggestions...")
        maybe_create_pair_suggestions(invoice_id)
        maybe_create_pair_suggestions(dn_id)
        
        # Check for suggestions
        suggestions = db_list_pairs("suggested", 10)
        print(f"Found {len(suggestions)} pairing suggestions")
        
        for suggestion in suggestions:
            print(f"Suggestion: {suggestion}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pairing()
