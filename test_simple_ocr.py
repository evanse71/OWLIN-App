#!/usr/bin/env python3
"""
Simple OCR test to debug the processing
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from ocr.unified_ocr_engine import UnifiedOCREngine, OCRResult
from PIL import Image, ImageDraw, ImageFont

def create_simple_test_image():
    """Create a very simple test image"""
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    
    # Use default font
    font = ImageFont.load_default()
    
    # Draw simple text
    draw.text((50, 50), "INVOICE", fill='black', font=font)
    draw.text((50, 80), "Supplier: Test Company", fill='black', font=font)
    draw.text((50, 110), "Total: $100.00", fill='black', font=font)
    
    return img

def test_ocr_step_by_step():
    """Test OCR processing step by step"""
    print("🧪 Testing OCR Step by Step...")
    
    # Create test image
    img = create_simple_test_image()
    print(f"✅ Created test image: {img.size}")
    
    # Initialize OCR engine
    engine = UnifiedOCREngine()
    print("✅ Initialized OCR engine")
    
    # Test Tesseract directly
    print("\n📋 Testing Tesseract directly...")
    try:
        import pytesseract
        text = pytesseract.image_to_string(img)
        print(f"   Tesseract text: '{text.strip()}'")
        
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        print(f"   Tesseract data blocks: {len([t for t in data['text'] if t.strip()])}")
        
    except Exception as e:
        print(f"   ❌ Tesseract failed: {e}")
    
    # Test OCR engine methods
    print("\n📋 Testing OCR engine methods...")
    
    # Test _run_tesseract
    print("   Testing _run_tesseract...")
    try:
        results = engine._run_tesseract(img)
        print(f"   _run_tesseract returned {len(results)} results")
        for i, result in enumerate(results[:3]):  # Show first 3 results
            print(f"     {i+1}: '{result.text}' (confidence: {result.confidence:.2f})")
    except Exception as e:
        print(f"   ❌ _run_tesseract failed: {e}")
    
    # Test _run_intelligent_ocr
    print("\n   Testing _run_intelligent_ocr...")
    try:
        results = engine._run_intelligent_ocr(img)
        print(f"   _run_intelligent_ocr returned {len(results)} results")
        for i, result in enumerate(results[:3]):  # Show first 3 results
            print(f"     {i+1}: '{result.text}' (confidence: {result.confidence:.2f})")
    except Exception as e:
        print(f"   ❌ _run_intelligent_ocr failed: {e}")
    
    # Test _extract_structured_data
    print("\n   Testing _extract_structured_data...")
    try:
        results = engine._run_tesseract(img)
        if results:
            structured_data = engine._extract_structured_data(results)
            print(f"   Structured data: {structured_data}")
        else:
            print("   No OCR results to process")
    except Exception as e:
        print(f"   ❌ _extract_structured_data failed: {e}")

def main():
    """Run simple OCR test"""
    print("🚀 Simple OCR Test...")
    print("=" * 50)
    
    test_ocr_step_by_step()
    
    print("\n" + "=" * 50)
    print("📋 Test Complete")

if __name__ == "__main__":
    main() 