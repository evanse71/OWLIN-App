#!/usr/bin/env python3
"""
Test script for invoice validation pipeline.
Tests the full OCR → LLM → validation pipeline on a sample invoice.

Usage:
    python backend/scripts/test_invoice_validation.py path/to/invoice.pdf
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.ocr.owlin_scan_pipeline import process_document
from backend.llm.invoice_parser import create_invoice_parser

def test_invoice_validation(file_path: str, output_file: str = None):
    """Test invoice validation on a file."""
    import sys
    if output_file:
        f = open(output_file, 'w', encoding='utf-8')
        original_stdout = sys.stdout
        sys.stdout = f
    else:
        f = None
        original_stdout = None
    
    try:
        print(f"Testing invoice validation on: {file_path}")
        print("=" * 80)
        
        # Step 1: Run OCR pipeline
        print("\n[1/3] Running OCR pipeline...")
        ocr_result = process_document(file_path)
        
        if ocr_result.get("status") != "ok":
            print(f"❌ OCR failed: {ocr_result.get('error')}")
            return
        
        pages = ocr_result.get("pages", [])
        if not pages:
            print("❌ No pages extracted")
            return
        
        print(f"✓ OCR complete: {len(pages)} page(s), confidence={ocr_result.get('overall_confidence', 0):.3f}")
        
        # Step 2: Extract full-page text and run LLM
        print("\n[2/3] Running LLM extraction...")
        first_page = pages[0]
        
        # Assemble full-page text
        full_text_parts = []
        for block in first_page.get("blocks", []):
            text = block.get("ocr_text", "")
            if text:
                full_text_parts.append(text)
        full_text = "\n".join(full_text_parts)
        
        print(f"✓ Assembled {len(full_text)} chars of OCR text")
        
        # Run LLM parser
        parser = create_invoice_parser()
        llm_result = parser.parse_document(full_text, page_number=1)
        
        if not llm_result.success:
            print(f"❌ LLM extraction failed: {llm_result.error_message}")
            return
        
        print(f"✓ LLM extraction complete")
        
        # Step 3: Display results
        print("\n[3/3] Validation Results:")
        print("=" * 80)
        print(f"Supplier Name:     {llm_result.supplier_name}")
        print(f"Invoice Number:    {llm_result.invoice_number}")
        print(f"Invoice Date:      {llm_result.invoice_date}")
        print(f"Currency:          {llm_result.currency}")
        print(f"\nLine Items:        {len(llm_result.line_items)}")
        for idx, item in enumerate(llm_result.line_items[:5], 1):  # Show first 5
            print(f"  {idx}. {item.description[:50]:<50} Qty={item.qty} × {item.unit_price:.2f} = {item.total:.2f}")
        if len(llm_result.line_items) > 5:
            print(f"  ... and {len(llm_result.line_items) - 5} more")
        
        print(f"\nSubtotal:          £{llm_result.subtotal:.2f}")
        print(f"VAT Amount:        £{llm_result.vat_amount:.2f}")
        print(f"Grand Total:       £{llm_result.grand_total:.2f}")
        
        # Calculate validation
        calculated_subtotal = sum(item.total for item in llm_result.line_items)
        calculated_grand = calculated_subtotal + llm_result.vat_amount
        
        print(f"\nValidation:")
        print(f"  Calculated Subtotal:  £{calculated_subtotal:.2f}")
        print(f"  Extracted Subtotal:   £{llm_result.subtotal:.2f}")
        if llm_result.subtotal > 0:
            subtotal_error = abs(calculated_subtotal - llm_result.subtotal) / llm_result.subtotal * 100
            print(f"  Subtotal Error:       {subtotal_error:.2f}%")
        
        print(f"  Calculated Grand:     £{calculated_grand:.2f}")
        print(f"  Extracted Grand:      £{llm_result.grand_total:.2f}")
        if llm_result.grand_total > 0:
            grand_error = abs(calculated_grand - llm_result.grand_total) / llm_result.grand_total * 100
            print(f"  Grand Total Error:    {grand_error:.2f}%")
        
        print(f"\nConfidence:        {llm_result.confidence:.3f}")
        print(f"Needs Review:      {getattr(llm_result, 'needs_review', False)}")
        
        if llm_result.metadata.get("validation_errors"):
            print(f"\n⚠ Validation Errors:")
            for error in llm_result.metadata["validation_errors"]:
                print(f"  - {error}")
        
        if getattr(llm_result, 'needs_review', False):
            print(f"\n🔴 INVOICE MARKED FOR REVIEW")
            print(f"   Reason: {llm_result.metadata.get('review_reason', 'Unknown')}")
        else:
            print(f"\n✅ Invoice passed validation")
        
        print("=" * 80)
    finally:
        if output_file and f:
            sys.stdout = original_stdout
            f.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python test_invoice_validation.py <invoice_file> [output_file]")
        sys.exit(1)
    
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    test_invoice_validation(sys.argv[1], output_file)
