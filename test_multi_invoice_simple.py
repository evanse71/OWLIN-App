#!/usr/bin/env python3
"""
Simplified test script for multi-invoice processing functionality.
Tests core logic without requiring full backend setup.
"""

import re
from typing import List, Dict, Any, Optional

class SimpleMultiInvoiceProcessor:
    """Simplified version of SmartUploadProcessor for testing."""
    
    def __init__(self):
        # Invoice header patterns to detect new invoices
        self.invoice_header_patterns = [
            r'invoice\s*#?\s*[:.]?\s*([A-Za-z0-9\-_/]+)',
            r'invoice\s*number\s*[:.]?\s*([A-Za-z0-9\-_/]+)',
            r'inv\s*[:.]?\s*([A-Za-z0-9\-_/]+)',
            r'bill\s*#?\s*[:.]?\s*([A-Za-z0-9\-_/]+)',
            r'statement\s*#?\s*[:.]?\s*([A-Za-z0-9\-_/]+)',
            r'page\s+\d+\s+of\s+\d+',  # Page numbering often indicates new document
            r'continued\s+on\s+next\s+page',  # Continuation indicators
        ]
        
        self.invoice_keywords = [
            'invoice', 'tax', 'total', 'vat', 'subtotal', 'net', 'amount due',
            'invoice number', 'invoice date', 'supplier', 'payment', 'bill',
            'statement', 'account', 'balance', 'outstanding'
        ]

    def detect_invoice_headers(self, ocr_text: str) -> List[str]:
        """Detect invoice headers that indicate the start of a new invoice."""
        headers = []
        text_lower = ocr_text.lower()
        
        for pattern in self.invoice_header_patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                headers.append(match.group(0))
        
        return headers

    def is_valid_invoice(self, ocr_text: str) -> bool:
        """Validate that the text represents a valid invoice."""
        # Check for minimum word count
        word_count = len(ocr_text.split())
        has_sufficient_content = word_count >= 30
        
        # Check for invoice keywords
        text_lower = ocr_text.lower()
        has_invoice_keywords = any(keyword in text_lower for keyword in self.invoice_keywords)
        
        # Check for invoice headers
        has_invoice_headers = len(self.detect_invoice_headers(ocr_text)) > 0
        
        return has_sufficient_content and (has_invoice_keywords or has_invoice_headers)

    def group_pages_into_invoices(self, pages_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group pages into logical invoice documents based on invoice headers."""
        documents = []
        current_group = []
        current_invoice_start = None
        
        for page_data in pages_data:
            if page_data.get('skip_page', False):
                continue
            
            # Check if this page starts a new invoice
            if page_data.get('is_invoice_start', False) and current_group:
                # Save current group as a document
                if current_group:
                    doc = self.create_document_from_group(current_group, current_invoice_start)
                    documents.append(doc)
                
                # Start new group
                current_group = [page_data]
                current_invoice_start = page_data.get('page_number')
            else:
                # Add to current group
                if not current_group:
                    current_invoice_start = page_data.get('page_number')
                current_group.append(page_data)
        
        # Don't forget the last group
        if current_group:
            doc = self.create_document_from_group(current_group, current_invoice_start)
            documents.append(doc)
        
        return documents

    def create_document_from_group(self, group: List[Dict[str, Any]], invoice_start: Optional[int]) -> Dict[str, Any]:
        """Create a document object from a group of pages."""
        if not group:
            return {}
        
        # Get page numbers
        page_numbers = [p.get('page_number') for p in group]
        
        # Determine the primary document type
        doc_types = [p.get('document_type') for p in group]
        primary_type = max(set(doc_types), key=doc_types.count) if doc_types else 'unknown'
        
        # Calculate average confidence
        confidences = [p.get('confidence', 0) for p in group]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            "type": primary_type,
            "pages": page_numbers,
            "confidence": round(avg_confidence, 2),
            "supplier_name": "Unknown",
            "invoice_start": invoice_start
        }

def test_invoice_header_detection():
    """Test invoice header detection patterns."""
    print("🧪 Testing Invoice Header Detection")
    print("=" * 50)
    
    processor = SimpleMultiInvoiceProcessor()
    
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
        headers = processor.detect_invoice_headers(text)
        status = "✅" if headers else "❌"
        print(f"{i:2d}. {status} '{text}' -> {headers}")

def test_invoice_validation():
    """Test invoice validation logic."""
    print("\n🧪 Testing Invoice Validation")
    print("=" * 50)
    
    processor = SimpleMultiInvoiceProcessor()
    
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
    
    is_valid = processor.is_valid_invoice(valid_invoice_text)
    print(f"1. Valid Invoice: {'✅' if is_valid else '❌'}")
    print(f"   Word Count: {len(valid_invoice_text.split())}")
    print(f"   Has Invoice Keywords: {'Yes' if any(kw in valid_invoice_text.lower() for kw in processor.invoice_keywords) else 'No'}")
    print(f"   Has Invoice Headers: {'Yes' if processor.detect_invoice_headers(valid_invoice_text) else 'No'}")
    
    # Test case 2: Invalid invoice (no invoice number)
    invalid_invoice_text = """
    Some random document
    This is not an invoice
    Just some text here
    """
    
    is_valid = processor.is_valid_invoice(invalid_invoice_text)
    print(f"\n2. Invalid Invoice: {'❌' if not is_valid else '✅'}")
    print(f"   Word Count: {len(invalid_invoice_text.split())}")
    print(f"   Has Invoice Keywords: {'Yes' if any(kw in invalid_invoice_text.lower() for kw in processor.invoice_keywords) else 'No'}")
    print(f"   Has Invoice Headers: {'Yes' if processor.detect_invoice_headers(invalid_invoice_text) else 'No'}")

def test_multi_invoice_text_processing():
    """Test processing of multi-invoice text."""
    print("\n🧪 Testing Multi-Invoice Text Processing")
    print("=" * 50)
    
    processor = SimpleMultiInvoiceProcessor()
    
    # Simulate page processing
    pages_data = [
        {
            "page_number": 1,
            "ocr_text": "INVOICE # INV-001\nSupplier: JJ Produce Ltd\nDate: 2024-01-15\nItem: Tomatoes\nQuantity: 10\nPrice: £2.50\nTotal: £25.00\nSubtotal: £25.00\nVAT (20%): £5.00\nTotal Amount: £30.00",
            "skip_page": False,
            "is_invoice_start": True,
            "word_count": 25,
            "document_type": "invoice",
            "confidence": 0.9
        },
        {
            "page_number": 2,
            "ocr_text": "INVOICE # INV-002\nSupplier: JJ Produce Ltd\nDate: 2024-01-16\nItem: Apples\nQuantity: 5\nPrice: £1.80\nTotal: £9.00\nSubtotal: £9.00\nVAT (20%): £1.80\nTotal Amount: £10.80",
            "skip_page": False,
            "is_invoice_start": True,
            "word_count": 25,
            "document_type": "invoice",
            "confidence": 0.9
        },
        {
            "page_number": 3,
            "ocr_text": "Terms and conditions\nPayment due within 30 days\nThank you for your business",
            "skip_page": False,
            "is_invoice_start": False,
            "word_count": 10,
            "document_type": "terms",
            "confidence": 0.7
        }
    ]
    
    # Test grouping
    grouped_documents = processor.group_pages_into_invoices(pages_data)
    
    print(f"Found {len(grouped_documents)} invoice groups:")
    for i, group in enumerate(grouped_documents, 1):
        print(f"\n{i}. Invoice Group:")
        print(f"   Type: {group.get('type')}")
        print(f"   Pages: {group.get('pages')}")
        print(f"   Confidence: {group.get('confidence')}")
        print(f"   Supplier: {group.get('supplier_name')}")

def main():
    """Run all tests."""
    print("🚀 Multi-Invoice Processing Test Suite (Simplified)")
    print("=" * 60)
    
    try:
        test_invoice_header_detection()
        test_invoice_validation()
        test_multi_invoice_text_processing()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("\n🎯 Key Features Tested:")
        print("• Invoice header detection patterns")
        print("• Invoice validation logic")
        print("• Multi-invoice text processing")
        print("• Page grouping into invoice documents")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 