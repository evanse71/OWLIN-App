#!/usr/bin/env python3
"""Test runner with progress updates written to status file."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def write_status(msg):
    """Write status message to both console and status file."""
    print(msg)
    with open("test_status.txt", "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%H:%M:%S')} - {msg}\n")
        f.flush()

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_test_with_progress.py <invoice_file> [output_file]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "test_results.txt"
    
    # Clear status file
    with open("test_status.txt", "w", encoding="utf-8") as f:
        f.write(f"Test started at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Testing: {file_path}\n\n")
    
    write_status("=" * 80)
    write_status("INVOICE VALIDATION TEST")
    write_status("=" * 80)
    write_status(f"\nTesting: {file_path}")
    
    try:
        from backend.ocr.owlin_scan_pipeline import process_document
        from backend.llm.invoice_parser import create_invoice_parser
        
        # Step 1: OCR
        write_status("\n[1/3] Running OCR pipeline...")
        ocr_result = process_document(file_path)
        
        if ocr_result.get("status") != "ok":
            write_status(f"❌ OCR failed: {ocr_result.get('error')}")
            return
        
        pages = ocr_result.get("pages", [])
        if not pages:
            write_status("❌ No pages extracted")
            return
        
        write_status(f"✓ OCR complete: {len(pages)} page(s), confidence={ocr_result.get('overall_confidence', 0):.3f}")
        
        # Step 2: LLM
        write_status("\n[2/3] Running LLM extraction (this may take 30-120 seconds)...")
        first_page = pages[0]
        
        full_text_parts = []
        for block in first_page.get("blocks", []):
            text = block.get("ocr_text", "")
            if text:
                full_text_parts.append(text)
        full_text = "\n".join(full_text_parts)
        
        write_status(f"✓ Assembled {len(full_text)} chars of OCR text")
        write_status("Calling LLM parser...")
        
        parser = create_invoice_parser()
        llm_result = parser.parse_document(full_text, page_number=1)
        
        if not llm_result.success:
            write_status(f"❌ LLM extraction failed: {llm_result.error_message}")
            return
        
        write_status("✓ LLM extraction complete")
        
        # Step 3: Results
        write_status("\n[3/3] Validation Results:")
        write_status("=" * 80)
        
        results = []
        results.append(f"Supplier Name:     {llm_result.supplier_name}")
        results.append(f"Invoice Number:    {llm_result.invoice_number}")
        results.append(f"Invoice Date:      {llm_result.invoice_date}")
        results.append(f"Currency:          {llm_result.currency}")
        results.append(f"\nLine Items:        {len(llm_result.line_items)}")
        
        for idx, item in enumerate(llm_result.line_items[:5], 1):
            results.append(f"  {idx}. {item.description[:50]:<50} Qty={item.qty} × {item.unit_price:.2f} = {item.total:.2f}")
        if len(llm_result.line_items) > 5:
            results.append(f"  ... and {len(llm_result.line_items) - 5} more")
        
        results.append(f"\nSubtotal:          £{llm_result.subtotal:.2f}")
        results.append(f"VAT Amount:        £{llm_result.vat_amount:.2f}")
        results.append(f"Grand Total:       £{llm_result.grand_total:.2f}")
        
        # Validation
        calculated_subtotal = sum(item.total for item in llm_result.line_items)
        calculated_grand = calculated_subtotal + llm_result.vat_amount
        
        results.append(f"\nValidation:")
        results.append(f"  Calculated Subtotal:  £{calculated_subtotal:.2f}")
        results.append(f"  Extracted Subtotal:   £{llm_result.subtotal:.2f}")
        if llm_result.subtotal > 0:
            subtotal_error = abs(calculated_subtotal - llm_result.subtotal) / llm_result.subtotal * 100
            results.append(f"  Subtotal Error:       {subtotal_error:.2f}%")
        
        results.append(f"  Calculated Grand:     £{calculated_grand:.2f}")
        results.append(f"  Extracted Grand:      £{llm_result.grand_total:.2f}")
        if llm_result.grand_total > 0:
            grand_error = abs(calculated_grand - llm_result.grand_total) / llm_result.grand_total * 100
            results.append(f"  Grand Total Error:    {grand_error:.2f}%")
        
        results.append(f"\nConfidence:        {llm_result.confidence:.3f}")
        results.append(f"Needs Review:      {getattr(llm_result, 'needs_review', False)}")
        
        if llm_result.metadata.get("validation_errors"):
            results.append(f"\n⚠ Validation Errors:")
            for error in llm_result.metadata["validation_errors"]:
                results.append(f"  - {error}")
        
        if getattr(llm_result, 'needs_review', False):
            results.append(f"\n🔴 INVOICE MARKED FOR REVIEW")
            results.append(f"   Reason: {llm_result.metadata.get('review_reason', 'Unknown')}")
        else:
            results.append(f"\n✅ Invoice passed validation")
        
        results.append("=" * 80)
        
        # Write all results
        for line in results:
            write_status(line)
        
        # Also write to output file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(results))
            f.write('\n')
        
        write_status(f"\nResults also written to: {output_file}")
        write_status("Test completed successfully!")
        
    except Exception as e:
        error_msg = f"❌ Test failed with error: {e}"
        write_status(error_msg)
        import traceback
        write_status(traceback.format_exc())
        raise

if __name__ == "__main__":
    main()
