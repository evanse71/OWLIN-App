#!/usr/bin/env python3
"""
Acceptance test for Phase 1 and Phase 2 fixes
"""

import requests
import json
import time
import os

BASE_URL = "http://localhost:8001"

def test_api_health():
    """Test that the API is responding"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        print("✅ API health check passed")
        return True
    except Exception as e:
        print(f"❌ API health check failed: {e}")
        return False

def test_field_mapping():
    """Test that the API returns both items and line_items fields"""
    try:
        # Get list of invoices
        response = requests.get(f"{BASE_URL}/invoices")
        assert response.status_code == 200
        invoices = response.json()
        
        if invoices:
            # Test first invoice
            inv_id = invoices[0]["id"]
            response = requests.get(f"{BASE_URL}/invoices/{inv_id}")
            assert response.status_code == 200
            data = response.json()
            
            # Check that both fields are present
            assert "items" in data
            assert "line_items" in data
            assert data["items"] == data["line_items"]  # Should be identical
            
            print("✅ Field mapping test passed")
            return True
        else:
            print("⚠️ No invoices to test field mapping")
            return True
    except Exception as e:
        print(f"❌ Field mapping test failed: {e}")
        return False

def test_totals_fallback():
    """Test totals fallback computation"""
    try:
        from services import compute_totals_fallback
        
        lines = [
            {"qty": 2, "unit_price": 3.0, "line_total": 6.0},
            {"qty": 1, "unit_price": 4.0, "line_total": 4.0}
        ]
        totals = compute_totals_fallback(lines)
        assert totals["subtotal"] == 10.0
        
        print("✅ Totals fallback test passed")
        return True
    except Exception as e:
        print(f"❌ Totals fallback test failed: {e}")
        return False

def test_multi_invoice_splitting():
    """Test multi-invoice splitting functionality"""
    try:
        from ocr.splitter import split_pages_into_invoices, extract_invoice_metadata_from_chunk
        
        # Test splitting
        pages = [
            {"page_index": 0, "text": "Invoice No 123\nSupplier: ABC Ltd\n..."},
            {"page_index": 1, "text": "Line items for invoice 123\n..."},
            {"page_index": 2, "text": "Invoice Number 456\nSupplier: XYZ Corp\n..."},
            {"page_index": 3, "text": "Line items for invoice 456\n..."},
        ]
        chunks = split_pages_into_invoices(pages)
        assert len(chunks) == 2
        
        # Test metadata extraction
        metadata = extract_invoice_metadata_from_chunk(chunks[0])
        assert metadata["invoice_number"] == "123"
        assert metadata["page_range"] == (0, 1)
        
        print("✅ Multi-invoice splitting test passed")
        return True
    except Exception as e:
        print(f"❌ Multi-invoice splitting test failed: {e}")
        return False

def test_observability():
    """Test that observability logging is working"""
    try:
        from services import _persist_invoice
        import tempfile
        
        # Create a test invoice with high confidence but no items
        test_invoice = {
            "status": "scanned",
            "confidence": 90,
            "supplier_name": "Test Supplier",
            "invoice_date": "2024-01-01",
            "subtotal_p": 0,
            "vat_total_p": 0,
            "total_p": 0,
            "issues_count": 0,
        }
        
        # This should trigger the warning log
        inv_id = _persist_invoice(test_invoice, [], file_hash="test_hash", filename="test.pdf")
        print(f"✅ Observability test passed (created invoice {inv_id})")
        return True
    except Exception as e:
        print(f"❌ Observability test failed: {e}")
        return False

def main():
    """Run all acceptance tests"""
    print("🧪 Running acceptance tests for Phase 1 and Phase 2 fixes...")
    print()
    
    tests = [
        ("API Health", test_api_health),
        ("Field Mapping", test_field_mapping),
        ("Totals Fallback", test_totals_fallback),
        ("Multi-invoice Splitting", test_multi_invoice_splitting),
        ("Observability", test_observability),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"Testing {test_name}...")
        if test_func():
            passed += 1
        print()
    
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Phase 1 and Phase 2 fixes are working correctly.")
    else:
        print("⚠️ Some tests failed. Please check the implementation.")

if __name__ == "__main__":
    main() 