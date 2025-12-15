"""Debug OCR processing for the failed upload."""
import sys
from pathlib import Path

sys.path.insert(0, '.')

# The file that failed
file_path = "data/uploads/af61d52b-71bc-4bf5-a646-2d16c5cc9fb7__processed-4C99F607-686C-42FF-9166-84631324B347.jpeg"

print(f"Checking file: {file_path}")
print()

# Check if file exists
if not Path(file_path).exists():
    print(f"✗ File not found!")
    sys.exit(1)

print(f"✓ File exists: {Path(file_path).stat().st_size / 1024:.1f} KB")
print()

# Try to process with OCR pipeline
print("Testing OCR pipeline...")
try:
    from backend.ocr.owlin_scan_pipeline import process_document
    
    print("Calling process_document...")
    result = process_document(file_path)
    
    print(f"✓ Processing complete")
    print(f"  Status: {result.get('status')}")
    print(f"  Confidence: {result.get('overall_confidence')}")
    print(f"  Pages: {len(result.get('pages', []))}")
    
    if result.get('pages'):
        page = result['pages'][0]
        print(f"\n  Page 1:")
        print(f"    Blocks: {len(page.get('blocks', []))}")
        
        for idx, block in enumerate(page.get('blocks', [])):
            ocr_text = block.get('ocr_text', '')
            print(f"    Block {idx}: type={block.get('type')}, text_len={len(ocr_text)}, conf={block.get('confidence'):.3f}")
            if len(ocr_text) > 0:
                print(f"      Text preview: {ocr_text[:100]}...")
            else:
                print(f"      ✗ NO TEXT EXTRACTED!")
                
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

