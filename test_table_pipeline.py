#!/usr/bin/env python3
"""
Diagnostic script to test table extraction pipeline.

Usage:
    python test_table_pipeline.py <path_to_test_file>
    
This script will:
1. Check layout detection
2. Check table extraction
3. Show extracted line items
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    print("WARNING: OpenCV not available. Some features may not work.")
    CV2_AVAILABLE = False

from backend.ocr.owlin_scan_pipeline import process_document_ocr, detect_layout
from backend.ocr.table_extractor import extract_table_from_block

def test_layout_detection(file_path: Path):
    """Test Step 1: Layout Detection"""
    print("=" * 60)
    print("Step 1: Layout Detection")
    print("=" * 60)
    
    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        return None
    
    try:
        layout_result = detect_layout(file_path)
        print(f"✓ Found {len(layout_result.blocks)} blocks")
        
        table_blocks = [b for b in layout_result.blocks if b.type == "table"]
        print(f"✓ Found {len(table_blocks)} table blocks")
        
        for i, block in enumerate(layout_result.blocks):
            print(f"  Block {i}: type='{block.type}', bbox={block.bbox}, ocr_text_len={len(block.ocr_text)}")
        
        return layout_result
    except Exception as e:
        print(f"ERROR: Layout detection failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_table_extraction(file_path: Path, layout_result):
    """Test Step 2: Table Extraction"""
    print("\n" + "=" * 60)
    print("Step 2: Table Extraction")
    print("=" * 60)
    
    if not CV2_AVAILABLE:
        print("ERROR: OpenCV required for table extraction")
        return
    
    if not layout_result:
        print("ERROR: No layout result available")
        return
    
    try:
        image = cv2.imread(str(file_path))
        if image is None:
            print(f"ERROR: Could not load image from {file_path}")
            return
        
        print(f"✓ Loaded image: {image.shape}")
        
        table_blocks = [b for b in layout_result.blocks if b.type == "table"]
        
        if not table_blocks:
            print("⚠ No table blocks found in layout detection")
            return
        
        for i, block in enumerate(table_blocks):
            print(f"\nExtracting table from block {i}...")
            block_info = {"type": block.type, "bbox": list(block.bbox)}
            
            try:
                result = extract_table_from_block(image, block_info, block.ocr_text)
                print(f"  ✓ Extracted {len(result.line_items)} line items")
                print(f"  ✓ Method: {result.method_used}")
                print(f"  ✓ Confidence: {result.confidence:.3f}")
                print(f"  ✓ Processing time: {result.processing_time:.3f}s")
                print(f"  ✓ Fallback used: {result.fallback_used}")
                print(f"  ✓ Cell count: {result.cell_count}, Row count: {result.row_count}")
                
                if result.line_items:
                    print(f"\n  First item details:")
                    first_item = result.line_items[0]
                    if hasattr(first_item, 'to_dict'):
                        item_dict = first_item.to_dict()
                        for key, value in item_dict.items():
                            print(f"    {key}: {value}")
                    else:
                        print(f"    {first_item}")
                    
                    if len(result.line_items) > 1:
                        print(f"\n  ... and {len(result.line_items) - 1} more items")
                else:
                    print("  ⚠ No line items extracted")
                    
            except Exception as e:
                print(f"  ✗ Table extraction failed: {e}")
                import traceback
                traceback.print_exc()
                
    except Exception as e:
        print(f"ERROR: Table extraction test failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_table_pipeline.py <path_to_test_file>")
        print("\nExample:")
        print("  python test_table_pipeline.py data/uploads/test_invoice.pdf")
        sys.exit(1)
    
    file_path = Path(sys.argv[1])
    
    print(f"Testing table extraction pipeline for: {file_path}")
    print()
    
    # Step 1: Layout Detection
    layout_result = test_layout_detection(file_path)
    
    # Step 2: Table Extraction
    test_table_extraction(file_path, layout_result)
    
    print("\n" + "=" * 60)
    print("Diagnostic Complete")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Check backend logs for [LAYOUT] and [TABLE_EXTRACT] messages")
    print("2. Run SQL query to check database storage:")
    print("   SELECT i.id, i.doc_id, i.supplier, i.date, i.value,")
    print("          (SELECT COUNT(*) FROM invoice_line_items WHERE doc_id = i.doc_id) as line_item_count")
    print("   FROM invoices i ORDER BY i.id DESC LIMIT 1;")
    print("3. Check API response: curl 'http://localhost:8000/api/upload/status?doc_id=YOUR_DOC_ID'")

if __name__ == "__main__":
    main()

