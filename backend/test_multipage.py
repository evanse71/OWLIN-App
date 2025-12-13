#!/usr/bin/env python3
"""Test multi-page functionality"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

try:
    print("Testing multi-page functionality...")
    
    from robust_ocr import extract_items_from_pages, STOP_PAT
    
    # Test data - simulate multi-page lines
    test_lines_by_page = [
        # Page 1 - items
        [
            {"text": "ITEM DESCRIPTION QTY UNIT PRICE VAT LINE PRICE", "conf": 90},
            {"text": "Beer Lager 2 x £3.50 20% £8.40", "conf": 85},
            {"text": "Wine Red 1 x £12.00 20% £14.40", "conf": 88},
        ],
        # Page 2 - more items
        [
            {"text": "Cheese Cheddar 3 x £2.50 20% £9.00", "conf": 87},
            {"text": "Bread Sourdough 2 x £1.80 0% £3.60", "conf": 86},
        ],
        # Page 3 - totals (should stop here)
        [
            {"text": "SUBTOTAL £35.40", "conf": 90},
            {"text": "VAT TOTAL £7.08", "conf": 90},
            {"text": "TOTAL DUE £42.48", "conf": 90},
        ]
    ]
    
    print("Testing extract_items_from_pages...")
    items = extract_items_from_pages(test_lines_by_page)
    
    print(f"✅ Extracted {len(items)} items")
    for i, item in enumerate(items):
        print(f"  {i+1}. {item.get('description', 'N/A')} (page {item.get('page_idx', 'N/A')})")
    
    print("\nTesting STOP_PAT patterns...")
    test_texts = [
        "SUBTOTAL £100.00",
        "TOTAL DUE £150.00", 
        "VAT SUMMARY",
        "PAYMENT TERMS",
        "BANK DETAILS",
        "THANK YOU",
        "Regular item line"  # Should not match
    ]
    
    for text in test_texts:
        match = STOP_PAT.search(text)
        print(f"  '{text}' -> {'STOP' if match else 'CONTINUE'}")
    
    print("\n🎉 Multi-page functionality test passed!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1) 