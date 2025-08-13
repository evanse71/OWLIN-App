#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.advanced_ocr_processor_simple import AdvancedOCRProcessorSimple
import asyncio

async def test_improvements():
    """Test the improvements to the OCR system"""
    print("🧪 Testing OCR Improvements...")
    
    # Initialize the processor
    processor = AdvancedOCRProcessorSimple()
    
    # Test supplier extraction
    print("\n📋 Testing Supplier Extraction...")
    test_text = """
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
    
    # Test supplier extraction
    supplier = processor.extract_supplier_name_advanced(test_text, [])
    print(f"✅ Supplier extracted: {supplier}")
    
    # Test date extraction
    print("\n📅 Testing Date Extraction...")
    date = processor.extract_invoice_date_advanced(test_text)
    print(f"✅ Date extracted: {date}")
    
    # Test total extraction
    print("\n💰 Testing Total Extraction...")
    total = processor.extract_total_amount_advanced(test_text)
    print(f"✅ Total extracted: £{total}")
    
    # Test fuzzy matching
    print("\n🔍 Testing Fuzzy Matching...")
    candidates = processor.fuzzy_match_suppliers(test_text)
    print(f"✅ Fuzzy matches found: {len(candidates)}")
    for candidate in candidates[:3]:
        print(f"   - {candidate['name']} (confidence: {candidate['confidence']:.2f})")
    
    print("\n✅ All tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_improvements()) 