#!/usr/bin/env python3
"""
Test script to understand PaddleOCR result structure.
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont

def create_simple_test_image():
    """Create a simple test image."""
    img = Image.new('RGB', (200, 100), 'white')
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), 'TEST', fill='black')
    return img

def test_paddle_ocr_structure():
    """Test PaddleOCR result structure."""
    print("🧪 Testing PaddleOCR result structure...")
    
    try:
        from paddleocr import PaddleOCR
        
        # Initialize PaddleOCR
        ocr = PaddleOCR(use_textline_orientation=True, lang='en')
        print("✅ PaddleOCR initialized")
        
        # Create test image
        test_img = create_simple_test_image()
        print("✅ Test image created")
        
        # Run OCR
        result = ocr.ocr(np.array(test_img))
        print(f"✅ OCR completed")
        print(f"📊 Result type: {type(result)}")
        
        if isinstance(result, dict):
            print(f"📊 Result keys: {list(result.keys())}")
            for key, value in result.items():
                print(f"   {key}: {type(value)} - {value}")
        elif isinstance(result, (list, tuple)):
            print(f"📊 Result length: {len(result)}")
            for i, item in enumerate(result):
                print(f"   Item {i}: {type(item)} - {item}")
        else:
            print(f"📊 Unexpected result type: {type(result)}")
            print(f"📊 Result: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_paddle_ocr_structure() 