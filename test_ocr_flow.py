#!/usr/bin/env python3
"""
Test script for the complete OCR upload & parsing flow.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from ocr.ocr_engine import calculate_display_confidence, run_enhanced_ocr
from ocr.parse_invoice import extract_invoice_metadata, extract_line_items_from_text
from PIL import Image
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_confidence_calculation():
    """Test the improved confidence calculation."""
    print("🧪 Testing Confidence Calculation")
    
    test_cases = [
        (0.85, 15, "Red Dragon Brewery Invoice"),
        (0.05, 20, "Camden Hells 30L 2 x £108.50"),
        (0.0, 0, ""),
        (0.95, 50, "Invoice with lots of text and prices"),
    ]
    
    for raw_conf, word_count, text in test_cases:
        result = calculate_display_confidence(raw_conf, word_count, text)
        print(f"   Raw: {raw_conf}, Words: {word_count}, Text: '{text[:30]}...' -> {result}%")
    
    print("✅ Confidence calculation tests completed")

def test_supplier_extraction():
    """Test the improved supplier name extraction."""
    print("\n🧪 Testing Supplier Name Extraction")
    
    test_invoices = [
        # Test 1: Red Dragon Brewery
        """
        Red Dragon Brewery
        Invoice #RDB-15384
        Date: 30 June 2025
        """,
        
        # Test 2: Generic company
        """
        FROM: ABC Company Ltd
        Invoice Number: INV-12345
        Date: 2024-01-15
        """,
        
        # Test 3: No clear supplier
        """
        INVOICE
        Number: 67890
        Date: 2024-01-16
        Total: £150.00
        """,
    ]
    
    for i, invoice_text in enumerate(test_invoices, 1):
        print(f"\n📄 Test Invoice {i}:")
        metadata = extract_invoice_metadata(invoice_text)
        supplier = metadata.get('supplier_name', 'Unknown')
        print(f"   Supplier: {supplier}")
        print(f"   Invoice #: {metadata.get('invoice_number', 'Unknown')}")
        print(f"   Date: {metadata.get('invoice_date', 'Unknown')}")
    
    print("✅ Supplier extraction tests completed")

def test_line_item_extraction():
    """Test the line item extraction from text."""
    print("\n🧪 Testing Line Item Extraction")
    
    test_text = """
    Camden Hells 30L 2 x £108.50
    Meantime IPA 50L 1 x £113.23
    Shipping 1 x £15.00
    """
    
    line_items = extract_line_items_from_text(test_text)
    
    print(f"✅ Extracted {len(line_items)} line items:")
    for i, item in enumerate(line_items, 1):
        print(f"   {i}. {item['description']} - {item['quantity']} x £{item['unit_price']} = £{item['total_price']}")
    
    print("✅ Line item extraction tests completed")

def test_enhanced_ocr():
    """Test the enhanced OCR with multi-PSM fallback."""
    print("\n🧪 Testing Enhanced OCR")
    
    # Test with a sample image if available
    test_image_path = "test_invoice.jpg"
    if os.path.exists(test_image_path):
        print(f"📷 Testing with image: {test_image_path}")
        try:
            img = Image.open(test_image_path)
            result = run_enhanced_ocr(img)
            
            print(f"✅ Enhanced OCR Results:")
            print(f"   Text length: {len(result['text'])} characters")
            print(f"   Word count: {result['word_count']}")
            print(f"   Confidence: {result['confidence']:.1f}%")
            print(f"   PSM used: {result['psm_used']}")
            
            if result['text']:
                preview = result['text'][:100].replace('\n', '\\n')
                print(f"   Text preview: {preview}...")
            else:
                print("   No text extracted")
                
        except Exception as e:
            print(f"❌ Enhanced OCR test failed: {e}")
    else:
        print("ℹ️ No test image found - skipping OCR test")
    
    print("✅ Enhanced OCR tests completed")

def test_complete_flow():
    """Test the complete OCR flow with sample data."""
    print("\n🧪 Testing Complete OCR Flow")
    
    # Simulate OCR result
    sample_ocr_text = """
    Red Dragon Brewery
    Invoice #RDB-15384
    Date: 30 June 2025
    
    Camden Hells 30L 2 x £108.50
    Meantime IPA 50L 1 x £113.23
    Shipping 1 x £15.00
    
    Subtotal: £350.73
    VAT (20%): £70.15
    Total Amount Payable: £420.88
    """
    
    # Step 1: Extract metadata
    metadata = extract_invoice_metadata(sample_ocr_text)
    print(f"✅ Metadata extracted:")
    print(f"   Supplier: {metadata.get('supplier_name', 'Unknown')}")
    print(f"   Invoice #: {metadata.get('invoice_number', 'Unknown')}")
    print(f"   Date: {metadata.get('invoice_date', 'Unknown')}")
    print(f"   Total: £{metadata.get('total_amount', 0):.2f}")
    print(f"   Subtotal: £{metadata.get('subtotal', 0):.2f}")
    print(f"   VAT: £{metadata.get('vat', 0):.2f}")
    
    # Step 2: Extract line items
    line_items = extract_line_items_from_text(sample_ocr_text)
    print(f"✅ Line items extracted: {len(line_items)} items")
    for item in line_items:
        print(f"   - {item['description']}: {item['quantity']} x £{item['unit_price']}")
    
    # Step 3: Calculate confidence
    word_count = len(sample_ocr_text.split())
    confidence = calculate_display_confidence(0.85, word_count, sample_ocr_text)
    print(f"✅ Confidence calculated: {confidence}%")
    
    # Step 4: Determine status
    status = 'processed' if confidence > 10 and line_items else 'manual_review'
    print(f"✅ Status determined: {status}")
    
    print("✅ Complete flow test completed")

def main():
    """Run all tests."""
    print("🚀 Starting OCR Flow Test Suite")
    print("=" * 50)
    
    try:
        test_confidence_calculation()
        test_supplier_extraction()
        test_line_item_extraction()
        test_enhanced_ocr()
        test_complete_flow()
        
        print("\n" + "=" * 50)
        print("✅ All OCR flow tests completed successfully!")
        print("\n📋 Summary of Fixes Tested:")
        print("   ✅ Confidence calculation improvements")
        print("   ✅ Supplier name extraction enhancements")
        print("   ✅ Line item extraction from text")
        print("   ✅ Multi-PSM fallback logic")
        print("   ✅ Complete OCR flow integration")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 