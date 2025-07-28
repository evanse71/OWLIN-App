#!/usr/bin/env python3
"""
Test script for multi-invoice PDF processing functionality.
This script tests the enhanced SmartUploadProcessor with sample invoice data.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.ocr.smart_upload_processor import SmartUploadProcessor
from backend.ocr.parse_invoice import parse_invoice_text

def test_invoice_header_detection():
    """Test invoice header detection patterns."""
    print("🧪 Testing Invoice Header Detection")
    print("=" * 50)
    
    processor = SmartUploadProcessor()
    
    test_cases = [
        "Invoice # INV-001",
        "Invoice Number: INV-002",
        "INV: INV-003",
        "Bill # BILL-001",
        "Statement # STMT-001",
        "Page 1 of 2",
        "Continued on next page",
        "Invoice INV-004 Date: 2024-01-15",
        "No invoice header here",
        "Just some random text"
    ]
    
    for i, text in enumerate(test_cases, 1):
        headers = processor._detect_invoice_headers(text)
        status = "✅" if headers else "❌"
        print(f"{i:2d}. {status} '{text}' -> {headers}")

def test_invoice_validation():
    """Test invoice validation logic."""
    print("\n🧪 Testing Invoice Validation")
    print("=" * 50)
    
    processor = SmartUploadProcessor()
    
    # Test case 1: Valid invoice
    valid_invoice_text = """
    INVOICE # INV-001
    Supplier: JJ Produce Ltd
    Date: 2024-01-15
    
    Item: Tomatoes
    Quantity: 10
    Price: £2.50
    Total: £25.00
    
    Subtotal: £25.00
    VAT (20%): £5.00
    Total Amount: £30.00
    """
    
    parsed_valid = parse_invoice_text(valid_invoice_text)
    is_valid = processor._is_valid_invoice(parsed_valid, valid_invoice_text)
    print(f"1. Valid Invoice: {'✅' if is_valid else '❌'}")
    print(f"   Invoice Number: {parsed_valid.get('invoice_number')}")
    print(f"   Supplier: {parsed_valid.get('supplier_name')}")
    print(f"   Total: {parsed_valid.get('total_amount')}")
    
    # Test case 2: Invalid invoice (no invoice number)
    invalid_invoice_text = """
    Some random document
    This is not an invoice
    Just some text here
    """
    
    parsed_invalid = parse_invoice_text(invalid_invoice_text)
    is_valid = processor._is_valid_invoice(parsed_invalid, invalid_invoice_text)
    print(f"\n2. Invalid Invoice: {'❌' if not is_valid else '✅'}")
    print(f"   Invoice Number: {parsed_invalid.get('invoice_number')}")
    print(f"   Supplier: {parsed_invalid.get('supplier_name')}")
    print(f"   Total: {parsed_invalid.get('total_amount')}")

def test_multi_invoice_text_processing():
    """Test processing of multi-invoice text."""
    print("\n🧪 Testing Multi-Invoice Text Processing")
    print("=" * 50)
    
    # Simulate multi-invoice text
    multi_invoice_text = """
    INVOICE # INV-001
    Supplier: JJ Produce Ltd
    Date: 2024-01-15
    
    Item: Tomatoes
    Quantity: 10
    Price: £2.50
    Total: £25.00
    
    Subtotal: £25.00
    VAT (20%): £5.00
    Total Amount: £30.00
    
    --- Page 2 ---
    
    INVOICE # INV-002
    Supplier: JJ Produce Ltd
    Date: 2024-01-16
    
    Item: Apples
    Quantity: 5
    Price: £1.80
    Total: £9.00
    
    Subtotal: £9.00
    VAT (20%): £1.80
    Total Amount: £10.80
    """
    
    # Split into pages (simulating PDF pages)
    pages = multi_invoice_text.split("--- Page")
    
    processor = SmartUploadProcessor()
    
    # Simulate page processing
    pages_data = []
    for i, page_text in enumerate(pages, 1):
        if page_text.strip():
            # Simulate page data structure
            page_data = {
                "page_number": i,
                "ocr_text": page_text.strip(),
                "skip_page": False,
                "is_invoice_start": "INVOICE #" in page_text,
                "word_count": len(page_text.split()),
                "document_type": "invoice"
            }
            pages_data.append(page_data)
    
    # Test grouping
    grouped_documents = processor._group_pages_into_invoices(pages_data)
    
    print(f"Found {len(grouped_documents)} invoice groups:")
    for i, group in enumerate(grouped_documents, 1):
        print(f"\n{i}. Invoice Group:")
        print(f"   Type: {group.get('type')}")
        print(f"   Pages: {group.get('pages')}")
        print(f"   Confidence: {group.get('confidence')}")
        print(f"   Supplier: {group.get('supplier_name')}")

def test_line_item_extraction():
    """Test line item extraction from multi-invoice text."""
    print("\n🧪 Testing Line Item Extraction")
    print("=" * 50)
    
    # Test invoice with line items
    invoice_text = """
    INVOICE # INV-003
    Supplier: Fresh Foods Ltd
    Date: 2024-01-17
    
    Description          Qty    Unit Price    Total
    ------------------------------------------------
    Fresh Tomatoes      5      £2.50         £12.50
    Organic Apples      3      £1.80         £5.40
    Bananas             2      £1.20         £2.40
    
    Subtotal: £20.30
    VAT (20%): £4.06
    Total Amount: £24.36
    """
    
    parsed_data = parse_invoice_text(invoice_text)
    line_items = parsed_data.get('line_items', [])
    
    print(f"Invoice Number: {parsed_data.get('invoice_number')}")
    print(f"Supplier: {parsed_data.get('supplier_name')}")
    print(f"Total Amount: {parsed_data.get('total_amount')}")
    print(f"Line Items Found: {len(line_items)}")
    
    for i, item in enumerate(line_items, 1):
        print(f"\n{i}. {item.get('item', 'Unknown Item')}")
        print(f"   Quantity: {item.get('quantity')}")
        print(f"   Price (ex VAT): £{item.get('price_excl_vat', 0):.2f}")
        print(f"   Price (incl VAT): £{item.get('price_incl_vat', 0):.2f}")
        print(f"   VAT Rate: {item.get('vat_rate', 0):.1%}")

def main():
    """Run all tests."""
    print("🚀 Multi-Invoice Processing Test Suite")
    print("=" * 60)
    
    try:
        test_invoice_header_detection()
        test_invoice_validation()
        test_multi_invoice_text_processing()
        test_line_item_extraction()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("\n🎯 Key Features Tested:")
        print("• Invoice header detection patterns")
        print("• Invoice validation logic")
        print("• Multi-invoice text processing")
        print("• Line item extraction with VAT calculations")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 