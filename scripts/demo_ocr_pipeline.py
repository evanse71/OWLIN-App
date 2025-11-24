#!/usr/bin/env python3
"""
Demo script for the OCR pipeline scaffolding.
Creates a simple PDF and processes it through the pipeline.
"""

import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.ocr.owlin_scan_pipeline import process_document

def create_demo_pdf():
    """Create a simple demo PDF for testing."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("ERROR: PyMuPDF not installed. Install with: pip install PyMuPDF")
        return None
    
    pdf_path = Path("demo_invoice.pdf")
    doc = fitz.open()
    page = doc.new_page()
    
    # Add some text to simulate an invoice
    page.insert_text((72, 72), "INVOICE", fontsize=20)
    page.insert_text((72, 100), "Supplier: Demo Company Ltd", fontsize=12)
    page.insert_text((72, 120), "Invoice #: INV-2025-001", fontsize=12)
    page.insert_text((72, 140), "Date: 2025-10-19", fontsize=12)
    page.insert_text((72, 180), "Item 1: Test Product", fontsize=10)
    page.insert_text((72, 200), "Qty: 10, Price: £5.00, Total: £50.00", fontsize=10)
    page.insert_text((72, 240), "Total Amount: £50.00", fontsize=14)
    
    doc.save(str(pdf_path))
    doc.close()
    print(f"SUCCESS: Created demo PDF: {pdf_path}")
    return pdf_path

def main():
    """Run the OCR pipeline demo."""
    print("OWLIN OCR Pipeline Demo")
    print("=" * 40)
    
    # Create demo PDF
    pdf_path = create_demo_pdf()
    if not pdf_path:
        return
    
    # Process through pipeline
    print(f"\nProcessing: {pdf_path}")
    result = process_document(pdf_path)
    
    # Display results
    print(f"\nResults:")
    print(f"  Status: {result['status']}")
    print(f"  Pages: {len(result['pages'])}")
    print(f"  Overall Confidence: {result['overall_confidence']:.2f}")
    print(f"  Artifact Dir: {result['artifact_dir']}")
    print(f"  Elapsed: {result['elapsed_sec']}s")
    
    # Show page details
    for page in result['pages']:
        print(f"\n  Page {page['page_num']}:")
        print(f"    Confidence: {page['confidence']:.2f}")
        print(f"    Blocks: {len(page['blocks'])}")
        for block in page['blocks']:
            if block['ocr_text'].strip():
                print(f"      {block['type']}: {block['ocr_text'][:50]}...")
    
    print(f"\nCheck artifacts in: {result['artifact_dir']}")
    print("   - original.pdf: Original document")
    print("   - pages/: Rendered page images")
    print("   - ocr_output.json: Full OCR results")

if __name__ == "__main__":
    main()
