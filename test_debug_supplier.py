#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.advanced_ocr_processor_simple import AdvancedOCRProcessorSimple

def test_supplier_debug():
    """Debug supplier extraction issues"""
    print("🔍 Debugging Supplier Extraction...")
    
    processor = AdvancedOCRProcessorSimple()
    
    # Test the problematic section
    test_text = """
    INVOICE 1
    
    Red Dragon Dispense Limited
    Invoice Date: 30/06/2025
    Invoice Number: INV-001
    
    QTY CODE ITEM UNIT PRICE TOTAL
    2 ABC123 Beer Keg £10.50 £21.00
    1 DEF456 Wine Bottle £15.75 £15.75
    
    TOTAL DUE: £36.75
    """
    
    print(f"📄 Test text: {test_text}")
    
    # Test supplier extraction
    supplier = processor.extract_supplier_name_advanced(test_text, [])
    print(f"✅ Supplier extracted: {supplier}")
    
    # Test individual strategies
    print("\n🔍 Testing Individual Strategies:")
    
    # Test header candidates
    header_candidates = processor.extract_header_candidates(test_text, [])
    print(f"   - Header candidates: {len(header_candidates)}")
    for candidate in header_candidates[:3]:
        print(f"     * {candidate['name']} (confidence: {candidate['confidence']})")
    
    # Test pattern candidates
    pattern_candidates = processor.extract_by_patterns(test_text)
    print(f"   - Pattern candidates: {len(pattern_candidates)}")
    for candidate in pattern_candidates[:3]:
        print(f"     * {candidate['name']} (confidence: {candidate['confidence']})")
    
    # Test fuzzy candidates
    fuzzy_candidates = processor.fuzzy_match_suppliers(test_text)
    print(f"   - Fuzzy candidates: {len(fuzzy_candidates)}")
    for candidate in fuzzy_candidates[:3]:
        print(f"     * {candidate['name']} (confidence: {candidate['confidence']})")
    
    # Test validation
    test_names = ["Red Dragon Dispense Limited", "QTY CO", "ABC123", "TOTAL DUE: £36.75"]
    print(f"\n🔍 Testing Name Validation:")
    for name in test_names:
        is_valid = processor.is_valid_supplier_name(name)
        print(f"   - '{name}': {is_valid}")

if __name__ == "__main__":
    test_supplier_debug() 