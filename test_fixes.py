#!/usr/bin/env python3

import sys
import os
import asyncio
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.advanced_ocr_processor_simple import AdvancedOCRProcessorSimple

async def test_fixes():
    """Test the fixes for total extraction, date extraction, and multi-invoice processing"""
    print("🧪 Testing Fixes...")
    
    # Initialize the processor
    processor = AdvancedOCRProcessorSimple()
    
    # Test 1: Individual invoice with correct total and date
    print("\n📋 Test 1: Individual Invoice")
    test_invoice = """
    INVOICE
    
    Red Dragon Dispense Limited
    123 Main Street
    Cardiff, CF1 1AA
    
    Invoice Date: 30/06/2025
    Invoice Number: INV-001
    
    QTY CODE ITEM UNIT PRICE TOTAL
    2 ABC123 Beer Keg £10.50 £21.00
    1 DEF456 Wine Bottle £15.75 £15.75
    
    TOTAL DUE: £36.75
    """
    
    # Test total extraction
    total = processor.extract_total_amount_advanced(test_invoice)
    print(f"   - Total extracted: £{total}")
    
    # Test date extraction
    date = processor.extract_invoice_date_advanced(test_invoice)
    print(f"   - Date extracted: {date}")
    
    # Test supplier extraction
    supplier = processor.extract_supplier_name_advanced(test_invoice, [])
    print(f"   - Supplier extracted: {supplier}")
    
    # Test 2: Multi-invoice file
    print("\n📄 Test 2: Multi-Invoice File")
    multi_invoice = """
    INVOICE 1
    
    Red Dragon Dispense Limited
    Invoice Date: 30/06/2025
    Invoice Number: INV-001
    
    QTY CODE ITEM UNIT PRICE TOTAL
    2 ABC123 Beer Keg £10.50 £21.00
    1 DEF456 Wine Bottle £15.75 £15.75
    
    TOTAL DUE: £36.75
    
    ==========================================
    
    INVOICE 2
    
    Wild Horse Brewery
    Invoice Date: 01/07/2025
    Invoice Number: INV-002
    
    QTY CODE ITEM UNIT PRICE TOTAL
    3 GHI789 Ale Barrel £25.00 £75.00
    2 JKL012 Cider Bottle £8.50 £17.00
    
    TOTAL DUE: £92.00
    """
    
    # Test multi-invoice processing
    lines = multi_invoice.split('\n')
    text_items = []
    for i, line in enumerate(lines):
        if line.strip():
            text_item = {
                "text": line.strip(),
                "confidence": 0.9,
                "bbox": [0, i * 20, 100, (i + 1) * 20],
                "type": "multi_invoice"
            }
            text_items.append(text_item)
    
    # Test segmentation
    sections = processor.segment_document(text_items)
    print(f"   - Sections detected: {len(sections)}")
    
    # Test each section
    for i, section in enumerate(sections):
        section_text = " ".join([t.get('text', '') for t in section.get('texts', [])])
        total = processor.extract_total_amount_advanced(section_text)
        date = processor.extract_invoice_date_advanced(section_text)
        supplier = processor.extract_supplier_name_advanced(section_text, section.get('texts', []))
        print(f"   - Section {i+1}: Total=£{total}, Date={date}, Supplier={supplier}")
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(test_fixes()) 