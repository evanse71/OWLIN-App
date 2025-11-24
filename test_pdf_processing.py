#!/usr/bin/env python3
"""Test PDF processing to diagnose the issue"""
import sys
from pathlib import Path

pdf_path = Path("data/uploads/4f3314c6-fc96-4302-9c04-ec52725918a8__Storiinvoiceonly1.pdf")

print(f"Testing PDF: {pdf_path}")
print(f"File exists: {pdf_path.exists()}")
print(f"File size: {pdf_path.stat().st_size if pdf_path.exists() else 0} bytes")

# Test PyMuPDF
try:
    import fitz
    print("\n[OK] PyMuPDF (fitz) is installed")
    
    try:
        doc = fitz.open(str(pdf_path))
        print(f"[OK] PDF opened successfully: {doc.page_count} page(s)")
        
        if doc.page_count > 0:
            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=200)
            print(f"[OK] Page 0 rendered: {pix.width}x{pix.height}")
        
        doc.close()
    except Exception as e:
        print(f"[ERROR] Error opening PDF: {e}")
        import traceback
        traceback.print_exc()
        
except ImportError:
    print("\n[ERROR] PyMuPDF (fitz) is NOT installed")
    print("   Install with: pip install PyMuPDF")

# Test OCR pipeline
print("\n" + "="*50)
print("Testing OCR Pipeline Import")
try:
    from backend.ocr.owlin_scan_pipeline import process_document
    print("[OK] OCR pipeline imports successfully")
    
    print("\nTesting document processing...")
    result = process_document(pdf_path)
    print(f"Status: {result.get('status')}")
    print(f"Pages: {len(result.get('pages', []))}")
    print(f"Confidence: {result.get('overall_confidence', 0.0)}")
    
    if result.get('status') == 'error':
        print(f"[ERROR] Error: {result.get('error')}")
    elif len(result.get('pages', [])) == 0:
        print("[ERROR] No pages extracted")
    else:
        print(f"[OK] Successfully extracted {len(result['pages'])} page(s)")
        page1 = result['pages'][0]
        print(f"   Page 1 blocks: {len(page1.get('blocks', []))}")
        if page1.get('blocks'):
            total_text = " ".join([b.get('ocr_text', '') for b in page1['blocks']])
            print(f"   Total text length: {len(total_text)} chars")
            if 'Stori' in total_text:
                print("   [OK] STORI text detected in OCR output")
    
except Exception as e:
    print(f"[ERROR] Error testing pipeline: {e}")
    import traceback
    traceback.print_exc()

