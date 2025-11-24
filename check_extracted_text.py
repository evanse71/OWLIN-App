#!/usr/bin/env python3
"""Check what text was actually extracted"""
import sys
from pathlib import Path

pdf_path = Path("data/uploads/4f3314c6-fc96-4302-9c04-ec52725918a8__Storiinvoiceonly1.pdf")

from backend.ocr.owlin_scan_pipeline import process_document

result = process_document(pdf_path)
if result.get('pages'):
    page1 = result['pages'][0]
    print(f"Page 1 blocks: {len(page1.get('blocks', []))}")
    print("\nAll extracted text:")
    print("=" * 60)
    for i, block in enumerate(page1.get('blocks', []), 1):
        text = block.get('ocr_text', block.get('text', ''))
        conf = block.get('confidence', 0.0)
        print(f"\nBlock {i} (conf: {conf:.2f}):")
        print(f"  {text[:200]}..." if len(text) > 200 else f"  {text}")
    
    # Try STORI extraction
    full_text = "\n".join([b.get('ocr_text', b.get('text', '')) for b in page1.get('blocks', [])])
    print("\n" + "=" * 60)
    print("Full text for STORI extraction:")
    print(full_text)
    
    if 'Stori' in full_text or 'STORI' in full_text:
        print("\n[OK] STORI keyword found in text")
        from backend.ocr.vendors.stori_extractor import extract as extract_stori
        stori_result = extract_stori(full_text)
        print(f"\nSTORI extraction result:")
        print(f"  Items: {len(stori_result.get('items', []))}")
        print(f"  Date: {stori_result.get('date', 'Not found')}")
        print(f"  Total: {stori_result.get('total_pence', 0) / 100.0 if stori_result.get('total_pence') else 0}")
        if stori_result.get('items'):
            for item in stori_result['items']:
                print(f"    - {item.get('name')}: qty={item.get('qty')}, unit={item.get('unit_price_pence', 0)/100.0}, total={item.get('line_total_pence', 0)/100.0}")
    else:
        print("\n[WARNING] STORI keyword NOT found - OCR may not have extracted enough text")

