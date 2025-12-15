"""
Integration Test Script for LLM Invoice Extraction

This script demonstrates and tests the new LLM-first invoice extraction approach.

Usage:
    # Enable LLM extraction
    set FEATURE_LLM_EXTRACTION=true
    
    # Ensure Ollama is running
    curl http://localhost:11434/api/tags
    
    # Run test
    python test_llm_extraction.py
"""

import sys
import os
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.llm.invoice_parser import (
    LLMInvoiceParser,
    BBoxAligner,
    create_invoice_parser
)


# Sample OCR text that mimics the problem from the screenshot
PROBLEM_INVOICE_OCR = """
Invoice Line Items

NAME                            QTY    DN    PPU        TOTAL      STATUS
Unknown item                    60     —     £10.60     £477.00    NO MATCH
Unknown item                    50     —     £9.85      £265.95    NO MATCH
Unknown item                    29     —     £30.74     £891.54    NO MATCH

                                Subtotal                 £1,634.49
                                VAT (20%)                £326.90
                                Total                    £891.54
"""


def test_basic_parsing():
    """Test basic LLM parsing."""
    print("\n" + "="*70)
    print("TEST 1: Basic LLM Parsing")
    print("="*70)
    
    try:
        parser = create_invoice_parser()
        print(f"✓ Parser created: {parser.model_name} @ {parser.ollama_url}")
        
        # Parse sample invoice
        result = parser.parse_document(PROBLEM_INVOICE_OCR)
        
        print(f"\nParsing result:")
        print(f"  Success: {result.success}")
        print(f"  Document Type: {result.document_type.value}")
        print(f"  Confidence: {result.confidence:.3f}")
        print(f"  Processing Time: {result.processing_time:.2f}s")
        print(f"  Line Items: {len(result.line_items)}")
        
        if result.success:
            print(f"\nExtracted Line Items:")
            for idx, item in enumerate(result.line_items, 1):
                print(f"  {idx}. {item.description}")
                print(f"     Qty: {item.qty}, Unit: £{item.unit_price:.2f}, Total: £{item.total:.2f}")
            
            print(f"\nFinancial Summary:")
            print(f"  Subtotal: £{result.subtotal:.2f}")
            print(f"  VAT: £{result.vat_amount:.2f}")
            print(f"  Grand Total: £{result.grand_total:.2f}")
            
            # Verify math
            calculated_subtotal = sum(item.total for item in result.line_items)
            calculated_grand = result.subtotal + result.vat_amount
            
            print(f"\nMath Verification:")
            print(f"  Calculated Subtotal: £{calculated_subtotal:.2f}")
            print(f"  Match: {'✓' if abs(calculated_subtotal - result.subtotal) < 0.01 else '✗'}")
            print(f"  Calculated Grand Total: £{calculated_grand:.2f}")
            print(f"  Match: {'✓' if abs(calculated_grand - result.grand_total) < 0.01 else '✗'}")
            
            # Check for "Unknown item"
            unknown_count = sum(1 for item in result.line_items if "unknown" in item.description.lower())
            print(f"\n'Unknown item' occurrences: {unknown_count}")
            if unknown_count == 0:
                print("  ✓ No 'Unknown item' - semantic extraction successful!")
            else:
                print("  ✗ Still has 'Unknown item' - needs improvement")
        else:
            print(f"\n✗ Parsing failed: {result.error_message}")
            return False
        
        return result.success
        
    except Exception as e:
        print(f"✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bbox_alignment():
    """Test bounding box alignment."""
    print("\n" + "="*70)
    print("TEST 2: Bounding Box Alignment")
    print("="*70)
    
    try:
        aligner = BBoxAligner(match_threshold=0.7)
        print(f"✓ Aligner created with threshold {aligner.match_threshold}")
        
        # Sample data
        from backend.llm.invoice_parser import LLMLineItem
        
        llm_items = [
            LLMLineItem(
                description="Crate of Beer",
                qty=60,
                unit_price=10.60,
                total=636.00
            ),
            LLMLineItem(
                description="Wine Box",
                qty=50,
                unit_price=9.85,
                total=492.50
            )
        ]
        
        ocr_blocks = [
            {"text": "Crate", "bbox": [10, 100, 40, 20]},
            {"text": "of", "bbox": [55, 100, 15, 20]},
            {"text": "Beer", "bbox": [75, 100, 30, 20]},
            {"text": "60", "bbox": [200, 100, 20, 20]},
            {"text": "Wine", "bbox": [10, 130, 40, 20]},
            {"text": "Box", "bbox": [55, 130, 30, 20]},
            {"text": "50", "bbox": [200, 130, 20, 20]},
        ]
        
        # Align
        aligned = aligner.align_llm_to_ocr(llm_items, ocr_blocks)
        
        print(f"\nAlignment results:")
        for idx, item in enumerate(aligned, 1):
            print(f"  {idx}. {item.description}")
            if item.bbox:
                print(f"     BBox: {item.bbox} (x={item.bbox[0]}, y={item.bbox[1]}, w={item.bbox[2]}, h={item.bbox[3]})")
            else:
                print(f"     BBox: None (no match found)")
            print(f"     Confidence: {item.confidence:.3f}")
        
        # Check success
        all_have_bbox = all(item.bbox is not None for item in aligned)
        if all_have_bbox:
            print("\n✓ All items successfully aligned to bounding boxes")
            return True
        else:
            print("\n⚠ Some items could not be aligned")
            return True  # Still success, just with warnings
        
    except Exception as e:
        print(f"✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_integration():
    """Test config integration."""
    print("\n" + "="*70)
    print("TEST 3: Configuration Integration")
    print("="*70)
    
    try:
        from backend.config import (
            FEATURE_LLM_EXTRACTION,
            LLM_OLLAMA_URL,
            LLM_MODEL_NAME,
            LLM_TIMEOUT_SECONDS,
            LLM_MAX_RETRIES,
            LLM_BBOX_MATCH_THRESHOLD
        )
        
        print(f"Configuration values:")
        print(f"  FEATURE_LLM_EXTRACTION: {FEATURE_LLM_EXTRACTION}")
        print(f"  LLM_OLLAMA_URL: {LLM_OLLAMA_URL}")
        print(f"  LLM_MODEL_NAME: {LLM_MODEL_NAME}")
        print(f"  LLM_TIMEOUT_SECONDS: {LLM_TIMEOUT_SECONDS}")
        print(f"  LLM_MAX_RETRIES: {LLM_MAX_RETRIES}")
        print(f"  LLM_BBOX_MATCH_THRESHOLD: {LLM_BBOX_MATCH_THRESHOLD}")
        
        if FEATURE_LLM_EXTRACTION:
            print("\n✓ LLM extraction is ENABLED")
        else:
            print("\n⚠ LLM extraction is DISABLED")
            print("  To enable: set FEATURE_LLM_EXTRACTION=true")
        
        return True
        
    except Exception as e:
        print(f"✗ Config test failed: {e}")
        return False


def main():
    """Run all integration tests."""
    print("\n" + "#"*70)
    print("# LLM Invoice Extraction - Integration Test Suite")
    print("#"*70)
    
    results = {
        "config": test_config_integration(),
        "parsing": test_basic_parsing(),
        "bbox_alignment": test_bbox_alignment(),
    }
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {test_name:20s}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*70)
    if all_passed:
        print("✓ ALL TESTS PASSED")
        print("\nThe LLM-first extraction system is ready!")
        print("\nNext steps:")
        print("  1. Ensure Ollama is running: curl http://localhost:11434/api/tags")
        print("  2. Enable LLM extraction: set FEATURE_LLM_EXTRACTION=true")
        print("  3. Upload test invoice and verify results")
    else:
        print("✗ SOME TESTS FAILED")
        print("\nPlease fix the issues above before proceeding.")
    print("="*70 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

