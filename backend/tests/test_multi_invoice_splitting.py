#!/usr/bin/env python3
"""
Test multi-invoice splitting functionality
"""

import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.ocr.splitter import split_pages_into_invoices, extract_invoice_metadata_from_chunk

def test_splitter_multi_invoice():
    """Test that splitter correctly identifies multiple invoices"""
    pages = [
        {"page_index": 0, "text": "Invoice No 123\nSupplier: ABC Ltd\n..."},
        {"page_index": 1, "text": "Line items for invoice 123\n..."},
        {"page_index": 2, "text": "Invoice Number 456\nSupplier: XYZ Corp\n..."},
        {"page_index": 3, "text": "Line items for invoice 456\n..."},
    ]
    chunks = split_pages_into_invoices(pages)
    assert len(chunks) == 2
    assert chunks[0][0]["page_index"] == 0
    assert chunks[1][0]["page_index"] == 2

def test_splitter_single_invoice():
    """Test that splitter handles single invoices correctly"""
    pages = [
        {"page_index": 0, "text": "Invoice No 123\nSupplier: ABC Ltd\n..."},
        {"page_index": 1, "text": "Line items for invoice 123\n..."},
    ]
    chunks = split_pages_into_invoices(pages)
    assert len(chunks) == 1
    assert len(chunks[0]) == 2

def test_extract_invoice_metadata():
    """Test metadata extraction from invoice chunks"""
    chunk = [
        {"page_index": 0, "text": "Invoice No: INV-001\nABC Ltd\nDate: 01/01/2024\n..."},
        {"page_index": 1, "text": "Line items...\n..."},
    ]
    metadata = extract_invoice_metadata_from_chunk(chunk)
    assert metadata["invoice_number"] == "INV-001"
    assert "ABC" in metadata["supplier_name"]
    assert metadata["invoice_date"] == "01/01/2024"
    assert metadata["page_range"] == (0, 1)

def test_totals_fallback():
    """Test totals fallback computation"""
    from backend.services import compute_totals_fallback
    
    lines = [
        {"qty": 2, "unit_price": 3.0, "line_total": 6.0},
        {"qty": 1, "unit_price": 4.0, "line_total": 4.0}
    ]
    totals = compute_totals_fallback(lines)
    assert totals["subtotal"] == 10.0

if __name__ == "__main__":
    pytest.main([__file__]) 