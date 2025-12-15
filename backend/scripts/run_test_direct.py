#!/usr/bin/env python3
"""Direct test runner that writes all output to a file immediately."""

import sys
import os
import time
from pathlib import Path

# Set debug mode
os.environ["OWLIN_DEBUG_OCR"] = "1"

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_test_direct.py <invoice_file> [output_file]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "test_results.txt"
    
    # Open output file immediately
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("INVOICE VALIDATION TEST\n")
        f.write("=" * 80 + "\n")
        f.write(f"Test started at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Testing: {file_path}\n")
        f.write(f"Debug OCR: {os.environ.get('OWLIN_DEBUG_OCR', '0')}\n\n")
        f.flush()
        
        try:
            f.write("\n[1/3] Running OCR pipeline...\n")
            f.flush()
            
            from backend.ocr.owlin_scan_pipeline import process_document
            from backend.llm.invoice_parser import create_invoice_parser
            
            ocr_result = process_document(file_path)
            
            if ocr_result.get("status") != "ok":
                f.write(f"❌ OCR failed: {ocr_result.get('error')}\n")
                f.flush()
                return
            
            pages = ocr_result.get("pages", [])
            if not pages:
                f.write("❌ No pages extracted\n")
                f.flush()
                return
            
            f.write(f"✓ OCR complete: {len(pages)} page(s), confidence={ocr_result.get('overall_confidence', 0):.3f}\n")
            f.flush()
            
            # Step 2: LLM
            f.write("\n[2/3] Running LLM extraction (this may take 30-120 seconds)...\n")
            f.flush()
            
            first_page = pages[0]
            
            full_text_parts = []
            for block in first_page.get("blocks", []):
                text = block.get("ocr_text", "")
                if text:
                    full_text_parts.append(text)
            full_text = "\n".join(full_text_parts)
            
            f.write(f"✓ Assembled {len(full_text)} chars of OCR text\n")
            f.write("Calling LLM parser...\n")
            f.flush()
            
            parser = create_invoice_parser()
            llm_result = parser.parse_document(full_text, page_number=1)
            
            if not llm_result.success:
                f.write(f"❌ LLM extraction failed: {llm_result.error_message}\n")
                f.flush()
                return
            
            f.write("✓ LLM extraction complete\n")
            f.flush()
            
            # Step 3: Results
            f.write("\n[3/3] Validation Results:\n")
            f.write("=" * 80 + "\n")
            
            f.write(f"Supplier Name:     {llm_result.supplier_name}\n")
            f.write(f"Invoice Number:    {llm_result.invoice_number}\n")
            f.write(f"Invoice Date:      {llm_result.invoice_date}\n")
            f.write(f"Currency:          {llm_result.currency}\n")
            f.write(f"\nLine Items:        {len(llm_result.line_items)}\n")
            
            for idx, item in enumerate(llm_result.line_items[:5], 1):
                f.write(f"  {idx}. {item.description[:50]:<50} Qty={item.qty} × {item.unit_price:.2f} = {item.total:.2f}\n")
            if len(llm_result.line_items) > 5:
                f.write(f"  ... and {len(llm_result.line_items) - 5} more\n")
            
            f.write(f"\nSubtotal:          £{llm_result.subtotal:.2f}\n")
            f.write(f"VAT Amount:        £{llm_result.vat_amount:.2f}\n")
            f.write(f"Grand Total:       £{llm_result.grand_total:.2f}\n")
            
            # Validation
            calculated_subtotal = sum(item.total for item in llm_result.line_items)
            calculated_grand = calculated_subtotal + llm_result.vat_amount
            
            f.write(f"\nValidation:\n")
            f.write(f"  Calculated Subtotal:  £{calculated_subtotal:.2f}\n")
            f.write(f"  Extracted Subtotal:   £{llm_result.subtotal:.2f}\n")
            if llm_result.subtotal > 0:
                subtotal_error = abs(calculated_subtotal - llm_result.subtotal) / llm_result.subtotal * 100
                f.write(f"  Subtotal Error:       {subtotal_error:.2f}%\n")
            
            f.write(f"  Calculated Grand:     £{calculated_grand:.2f}\n")
            f.write(f"  Extracted Grand:      £{llm_result.grand_total:.2f}\n")
            if llm_result.grand_total > 0:
                grand_error = abs(calculated_grand - llm_result.grand_total) / llm_result.grand_total * 100
                f.write(f"  Grand Total Error:    {grand_error:.2f}%\n")
            
            f.write(f"\nConfidence:        {llm_result.confidence:.3f}\n")
            f.write(f"Needs Review:      {getattr(llm_result, 'needs_review', False)}\n")
            
            if llm_result.metadata.get("validation_errors"):
                f.write(f"\n⚠ Validation Errors:\n")
                for error in llm_result.metadata["validation_errors"]:
                    f.write(f"  - {error}\n")
            
            if getattr(llm_result, 'needs_review', False):
                f.write(f"\n🔴 INVOICE MARKED FOR REVIEW\n")
                f.write(f"   Reason: {llm_result.metadata.get('review_reason', 'Unknown')}\n")
            else:
                f.write(f"\n✅ Invoice passed validation\n")
            
            f.write("=" * 80 + "\n")
            f.write(f"Test completed at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.flush()
            
        except Exception as e:
            import traceback
            f.write(f"\n❌ Test failed with error: {e}\n")
            f.write(f"Traceback:\n{traceback.format_exc()}\n")
            f.flush()
            raise

if __name__ == "__main__":
    main()
