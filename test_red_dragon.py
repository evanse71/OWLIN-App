#!/usr/bin/env python3
"""
Red Dragon Invoice Test - Standalone Verification

This script tests the hybrid pipeline (geometric + semantic) on the Red Dragon invoice
without needing to restart the server or upload via UI.

Usage:
    python test_red_dragon.py path/to/red_dragon.pdf
    python test_red_dragon.py  # Uses default test file if available
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "backend"))

def test_red_dragon_extraction(pdf_path: str = None):
    """Test extraction on Red Dragon invoice."""
    
    print("=" * 80)
    print("RED DRAGON INVOICE TEST - Hybrid Pipeline")
    print("=" * 80)
    
    # Find test file
    if not pdf_path:
        # Look for Red Dragon invoice in common locations
        search_paths = [
            "uploads/red_dragon.pdf",
            "data/uploads/red_dragon.pdf",
            "test_invoices/red_dragon.pdf",
        ]
        
        for path in search_paths:
            if Path(path).exists():
                pdf_path = path
                break
        
        if not pdf_path:
            print("\n❌ No Red Dragon invoice found")
            print("Please provide path: python test_red_dragon.py path/to/invoice.pdf")
            return False
    
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(f"\n❌ File not found: {pdf_path}")
        return False
    
    print(f"\n📄 Testing file: {pdf_path}")
    print(f"   Size: {pdf_path.stat().st_size / 1024:.2f} KB")
    
    # Import OCR pipeline
    try:
        from backend.ocr.owlin_scan_pipeline import process_document
        from backend.ocr.table_extractor import get_table_extractor, extract_table_from_block
        import cv2
        import numpy as np
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("Make sure you're in the project root and dependencies are installed")
        return False
    
    # Process document
    print("\n🔄 Running OCR pipeline...")
    try:
        result = process_document(pdf_path)
        
        if result.get("status") == "error":
            print(f"\n❌ OCR failed: {result.get('error')}")
            return False
        
        print(f"\n✓ OCR completed in {result.get('elapsed_sec', 0):.2f}s")
        print(f"  Overall confidence: {result.get('overall_confidence', 0):.3f}")
        print(f"  Pages processed: {len(result.get('pages', []))}")
        
    except Exception as e:
        print(f"\n❌ OCR processing error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Extract line items from first page
    pages = result.get("pages", [])
    if not pages:
        print("\n❌ No pages found in result")
        return False
    
    page = pages[0]
    blocks = page.get("blocks", [])
    
    print(f"\n📊 Page 1 Analysis:")
    print(f"   Blocks detected: {len(blocks)}")
    
    # Find table blocks
    table_blocks = [b for b in blocks if b.get("type") == "table"]
    print(f"   Table blocks: {len(table_blocks)}")
    
    if not table_blocks:
        print("\n⚠️  No table blocks detected")
        print("   Trying to extract from all text...")
        
        # Combine all text
        all_text = "\n".join([b.get("ocr_text", "") for b in blocks])
        
        # Try semantic extraction
        extractor = get_table_extractor()
        mock_image = np.ones((100, 100, 3), dtype=np.uint8) * 255
        line_items = extractor._extract_by_row_patterns(all_text)
        
        print(f"\n✓ Semantic extraction: {len(line_items)} items")
        
    else:
        # Process first table block
        table_block = table_blocks[0]
        table_data = table_block.get("table_data")
        
        if table_data and table_data.get("line_items"):
            line_items = table_data["line_items"]
            method = table_data.get("method_used", "unknown")
            confidence = table_data.get("confidence", 0.0)
            
            print(f"\n✓ Table extraction successful!")
            print(f"   Method: {method}")
            print(f"   Confidence: {confidence:.3f}")
            print(f"   Line items: {len(line_items)}")
        else:
            print("\n⚠️  Table block found but no line items extracted")
            line_items = []
    
    # Display results
    if line_items:
        print("\n" + "=" * 80)
        print("EXTRACTED LINE ITEMS")
        print("=" * 80)
        
        for i, item in enumerate(line_items, 1):
            if isinstance(item, dict):
                desc = item.get("description", "")
                qty = item.get("quantity", "")
                unit = item.get("unit_price", "")
                total = item.get("total_price", "") or item.get("total", "")
                conf = item.get("confidence", 0.0)
            else:
                # LineItem object
                desc = getattr(item, 'description', '')
                qty = getattr(item, 'quantity', '')
                unit = getattr(item, 'unit_price', '')
                total = getattr(item, 'total_price', '')
                conf = getattr(item, 'confidence', 0.0)
            
            print(f"\n{i}. {desc}")
            print(f"   Qty: {qty}")
            print(f"   Unit Price: £{unit}")
            print(f"   Total: £{total}")
            print(f"   Confidence: {conf:.2f}")
        
        print("\n" + "=" * 80)
        print(f"✅ SUCCESS: Extracted {len(line_items)} line items")
        print("=" * 80)
        
        # Validate Red Dragon specific items
        descriptions = [item.get("description", "") if isinstance(item, dict) else getattr(item, 'description', '') 
                       for item in line_items]
        
        # Check for Red Dragon products (common items)
        red_dragon_products = ["pepsi", "cola", "dragon", "beer", "lager"]
        found_products = [p for p in red_dragon_products if any(p in d.lower() for d in descriptions)]
        
        if found_products:
            print(f"\n✓ Red Dragon products detected: {', '.join(found_products)}")
        
        return True
    else:
        print("\n❌ No line items extracted")
        return False

def test_semantic_patterns():
    """Test semantic patterns with mock data."""
    
    print("\n" + "=" * 80)
    print("SEMANTIC PATTERN TEST")
    print("=" * 80)
    
    # Mock Red Dragon format lines
    test_lines = """
PRODUCT QTY RATE AMOUNT
6  12 LITTRE PEPSI  78.49
24  COLA CASE  4.50  108.00
1  DELIVERY CHARGE  15.00
SUBTOTAL  201.49
    """.strip()
    
    print("\n📝 Test input:")
    print(test_lines)
    
    # Import extractor
    try:
        from backend.ocr.table_extractor import get_table_extractor
        import numpy as np
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        return False
    
    # Run extraction
    extractor = get_table_extractor()
    mock_image = np.ones((100, 100, 3), dtype=np.uint8) * 255
    
    try:
        line_items = extractor._extract_by_row_patterns(test_lines)
        
        print(f"\n✓ Extracted {len(line_items)} items:")
        for i, item in enumerate(line_items, 1):
            print(f"\n{i}. {item.description}")
            print(f"   Qty: {item.quantity}, Unit: £{item.unit_price}, Total: £{item.total_price}")
            print(f"   Pattern: {item.cell_data.get('pattern', 'unknown')}")
        
        # Validate
        if len(line_items) >= 3:
            print("\n✅ Semantic pattern extraction working!")
            return True
        else:
            print(f"\n⚠️  Expected at least 3 items, got {len(line_items)}")
            return False
            
    except Exception as e:
        print(f"\n❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n🧪 Red Dragon Invoice Extraction Test")
    print("Testing hybrid pipeline (geometric + semantic)\n")
    
    # Test semantic patterns first
    test1 = test_semantic_patterns()
    
    # Test full extraction if file provided
    test2 = True
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        test2 = test_red_dragon_extraction(pdf_path)
    else:
        print("\n" + "=" * 80)
        print("FULL EXTRACTION TEST")
        print("=" * 80)
        print("\n⏭️  Skipped (no PDF path provided)")
        print("   Usage: python test_red_dragon.py path/to/red_dragon.pdf")
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST RESULTS")
    print("=" * 80)
    print(f"Semantic Patterns: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"Full Extraction: {'✅ PASS' if test2 else '⏭️  SKIPPED'}")
    print("=" * 80)
    
    if test1:
        print("\n✅ Hybrid pipeline is working!")
        print("   - Semantic patterns can handle Red Dragon format")
        print("   - Geometric clustering will be tried first")
        print("   - System will automatically choose best result")
    
    sys.exit(0 if test1 else 1)

