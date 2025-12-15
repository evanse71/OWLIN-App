#!/usr/bin/env python3
"""
Quick test script to validate spatial clustering improvements.

This script tests the table extraction with mock OCR blocks to verify
that spatial clustering correctly identifies columns.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from ocr.table_extractor import TableExtractor
import numpy as np

def test_spatial_clustering():
    """Test spatial clustering with mock OCR blocks."""
    
    print("=" * 80)
    print("SPATIAL CLUSTERING TEST")
    print("=" * 80)
    
    # Create mock OCR blocks simulating an invoice table
    # Layout: [Description] [Qty] [Unit Price] [Total]
    # X-positions: 0-200, 220-280, 300-380, 400-480
    
    mock_ocr_blocks = [
        # Header row (should be skipped)
        {'text': 'Product', 'bbox': [10, 50, 100, 20]},
        {'text': 'Qty', 'bbox': [230, 50, 40, 20]},
        {'text': 'Price', 'bbox': [310, 50, 50, 20]},
        {'text': 'Total', 'bbox': [410, 50, 50, 20]},
        
        # Line item 1: "Storage Unit" - 5 - 24.99 - 124.95
        {'text': 'Storage', 'bbox': [10, 80, 80, 20]},
        {'text': 'Unit', 'bbox': [95, 80, 40, 20]},  # "Unit" in product name!
        {'text': '5', 'bbox': [240, 80, 20, 20]},
        {'text': '24.99', 'bbox': [315, 80, 50, 20]},
        {'text': '124.95', 'bbox': [410, 80, 60, 20]},
        
        # Line item 2: "Rate Card Display" - 10.5 - 15.00 - 157.50
        {'text': 'Rate', 'bbox': [10, 110, 40, 20]},  # "Rate" in product name!
        {'text': 'Card', 'bbox': [55, 110, 40, 20]},
        {'text': 'Display', 'bbox': [100, 110, 60, 20]},
        {'text': '10.5', 'bbox': [235, 110, 35, 20]},  # Decimal quantity
        {'text': '15.00', 'bbox': [315, 110, 50, 20]},
        {'text': '157.50', 'bbox': [410, 110, 60, 20]},
        
        # Line item 3: "Flat Fee Service" - 1 - 100 - 100
        {'text': 'Flat', 'bbox': [10, 140, 40, 20]},
        {'text': 'Fee', 'bbox': [55, 140, 30, 20]},
        {'text': 'Service', 'bbox': [90, 140, 60, 20]},
        {'text': '1', 'bbox': [245, 140, 15, 20]},
        {'text': '100', 'bbox': [320, 140, 35, 20]},  # Integer price
        {'text': '100', 'bbox': [420, 140, 35, 20]},
    ]
    
    # Create extractor
    extractor = TableExtractor()
    
    # Create mock image (not used for spatial clustering)
    mock_image = np.ones((200, 500, 3), dtype=np.uint8) * 255
    
    # Test spatial clustering
    print("\n1. Testing spatial clustering method...")
    try:
        line_items = extractor._fallback_line_grouping_spatial(
            mock_image, 
            mock_ocr_blocks
        )
        
        print(f"\n✓ Extracted {len(line_items)} line items")
        
        # Validate results
        expected_items = [
            ("Storage Unit", "5", "24.99", "124.95"),
            ("Rate Card Display", "10.5", "15.00", "157.50"),
            ("Flat Fee Service", "1", "100", "100"),
        ]
        
        success = True
        for i, (expected, actual) in enumerate(zip(expected_items, line_items)):
            exp_desc, exp_qty, exp_unit, exp_total = expected
            
            print(f"\nLine Item {i+1}:")
            print(f"  Description: {actual.description}")
            print(f"  Quantity: {actual.quantity}")
            print(f"  Unit Price: {actual.unit_price}")
            print(f"  Total: {actual.total_price}")
            print(f"  Confidence: {actual.confidence:.2f}")
            
            # Check if description contains expected words (may have extra spaces)
            if exp_desc.replace(" ", "").lower() not in actual.description.replace(" ", "").lower():
                print(f"  ✗ FAIL: Expected description to contain '{exp_desc}'")
                success = False
            else:
                print(f"  ✓ Description correct")
            
            # Check quantity
            if actual.quantity != exp_qty:
                print(f"  ✗ FAIL: Expected quantity '{exp_qty}', got '{actual.quantity}'")
                success = False
            else:
                print(f"  ✓ Quantity correct")
            
            # Check unit price
            if actual.unit_price != exp_unit:
                print(f"  ✗ FAIL: Expected unit price '{exp_unit}', got '{actual.unit_price}'")
                success = False
            else:
                print(f"  ✓ Unit price correct")
            
            # Check total
            if actual.total_price != exp_total:
                print(f"  ✗ FAIL: Expected total '{exp_total}', got '{actual.total_price}'")
                success = False
            else:
                print(f"  ✓ Total correct")
        
        print("\n" + "=" * 80)
        if success and len(line_items) == len(expected_items):
            print("✓ ALL TESTS PASSED")
            print("=" * 80)
            return True
        else:
            print("✗ SOME TESTS FAILED")
            print("=" * 80)
            return False
            
    except Exception as e:
        print(f"\n✗ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 80)
        return False

def test_column_clustering():
    """Test column clustering algorithm."""
    
    print("\n" + "=" * 80)
    print("COLUMN CLUSTERING TEST")
    print("=" * 80)
    
    extractor = TableExtractor()
    
    # Mock words with X-positions simulating 4 columns
    words_with_positions = [
        # Description column (X: 0-200)
        ("Storage", 50, 80),
        ("Unit", 100, 80),
        ("Rate", 40, 110),
        ("Card", 80, 110),
        
        # Qty column (X: 220-280)
        ("5", 240, 80),
        ("10.5", 245, 110),
        ("1", 245, 140),
        
        # Unit Price column (X: 300-380)
        ("24.99", 330, 80),
        ("15.00", 330, 110),
        ("100", 335, 140),
        
        # Total column (X: 400-480)
        ("124.95", 430, 80),
        ("157.50", 430, 110),
        ("100", 435, 140),
    ]
    
    print("\nTesting column clustering...")
    column_ranges = extractor._cluster_columns_by_x_position(words_with_positions)
    
    print(f"\n✓ Detected {len(column_ranges)} columns:")
    for col_name, (x_min, x_max) in column_ranges.items():
        print(f"  {col_name}: X range [{x_min}, {x_max})")
    
    # Validate we got the expected columns
    if len(column_ranges) >= 3:
        print("\n✓ Column clustering successful")
        print("=" * 80)
        return True
    else:
        print("\n✗ Expected at least 3 columns")
        print("=" * 80)
        return False

if __name__ == "__main__":
    print("\nTesting OCR Architectural Improvements")
    print("Testing spatial clustering and column detection\n")
    
    test1 = test_column_clustering()
    test2 = test_spatial_clustering()
    
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    print(f"Column Clustering: {'PASS' if test1 else 'FAIL'}")
    print(f"Spatial Extraction: {'PASS' if test2 else 'FAIL'}")
    print("=" * 80)
    
    sys.exit(0 if (test1 and test2) else 1)

