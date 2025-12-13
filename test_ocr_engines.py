#!/usr/bin/env python3
"""
Test OCR engines directly
"""

import pytesseract
from PIL import Image, ImageDraw, ImageFont
import io

def create_test_image():
    """Create a simple test image with text"""
    # Create a white image
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    
    # Use a default font
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    # Draw simple text
    draw.text((50, 50), "INVOICE", fill='black', font=font)
    draw.text((50, 80), "Supplier: Test Company", fill='black', font=font)
    draw.text((50, 110), "Total: $100.00", fill='black', font=font)
    
    return img

def test_tesseract():
    """Test Tesseract OCR directly"""
    print("🧪 Testing Tesseract OCR...")
    
    try:
        # Create test image
        img = create_test_image()
        
        # Test basic OCR
        text = pytesseract.image_to_string(img)
        print(f"   Tesseract extracted text: '{text.strip()}'")
        
        # Test detailed OCR
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        print(f"   Tesseract found {len([t for t in data['text'] if t.strip()])} text blocks")
        
        if text.strip():
            print("✅ Tesseract is working!")
            return True
        else:
            print("❌ Tesseract extracted no text")
            return False
            
    except Exception as e:
        print(f"❌ Tesseract test failed: {e}")
        return False

def test_paddle_ocr():
    """Test PaddleOCR directly"""
    print("🧪 Testing PaddleOCR...")
    
    try:
        from paddleocr import PaddleOCR
        import numpy as np
        
        # Create test image
        img = create_test_image()
        img_array = np.array(img)
        
        # Initialize PaddleOCR
        ocr = PaddleOCR(use_angle_cls=True, lang='en')
        
        # Test OCR
        results = ocr.ocr(img_array)
        print(f"   PaddleOCR found {len(results[0]) if results and results[0] else 0} text blocks")
        
        if results and results[0]:
            for result in results[0]:
                if result and len(result) >= 2:
                    bbox, (text, confidence) = result
                    print(f"   Text: '{text}', Confidence: {confidence:.2f}")
        
        if results and results[0] and len(results[0]) > 0:
            print("✅ PaddleOCR is working!")
            return True
        else:
            print("❌ PaddleOCR extracted no text")
            return False
            
    except Exception as e:
        print(f"❌ PaddleOCR test failed: {e}")
        return False

def main():
    """Test OCR engines"""
    print("🚀 Testing OCR Engines...")
    print("=" * 50)
    
    # Test Tesseract
    tesseract_ok = test_tesseract()
    
    print("\n" + "=" * 50)
    
    # Test PaddleOCR
    paddle_ok = test_paddle_ocr()
    
    print("\n" + "=" * 50)
    print("📋 OCR Engine Test Summary:")
    print(f"   Tesseract: {'✅' if tesseract_ok else '❌'}")
    print(f"   PaddleOCR: {'✅' if paddle_ok else '❌'}")
    
    if tesseract_ok or paddle_ok:
        print("\n✅ At least one OCR engine is working!")
        print("   The issue may be in the backend integration")
    else:
        print("\n❌ Both OCR engines are failing!")
        print("   This indicates a system-level OCR issue")

if __name__ == "__main__":
    main() 