#!/usr/bin/env python3
"""
Simple test to understand PaddleOCR result structure and fix processing issues.
"""

import sys
import os
import logging
from PIL import Image, ImageDraw
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_paddle_ocr_structure():
    """Test PaddleOCR result structure to understand the format."""
    print("🧪 Testing PaddleOCR Result Structure")
    print("=" * 50)
    
    try:
        from paddleocr import PaddleOCR
        
        # Initialize PaddleOCR
        print("🔄 Initializing PaddleOCR...")
        ocr = PaddleOCR(use_textline_orientation=True, lang='en')
        print("✅ PaddleOCR initialized")
        
        # Create a simple test image
        img = Image.new('RGB', (300, 150), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((20, 20), "Test Invoice", fill='black')
        draw.text((20, 50), "Amount: £100.00", fill='black')
        
        # Run OCR
        print("🔄 Running OCR...")
        result = ocr.predict(np.array(img))
        
        print(f"📊 Result type: {type(result)}")
        print(f"📊 Result length: {len(result) if hasattr(result, '__len__') else 'No length'}")
        
        if result:
            print(f"📊 First element type: {type(result[0]) if len(result) > 0 else 'No elements'}")
            
            if len(result) > 0:
                first_result = result[0]
                print(f"📊 First result type: {type(first_result)}")
                print(f"📊 First result attributes: {dir(first_result)}")
                
                # Try to access common attributes
                if hasattr(first_result, 'rec_texts'):
                    print(f"📊 rec_texts: {first_result.rec_texts}")
                if hasattr(first_result, 'rec_scores'):
                    print(f"📊 rec_scores: {first_result.rec_scores}")
                if hasattr(first_result, 'rec_boxes'):
                    print(f"📊 rec_boxes: {first_result.rec_boxes}")
                
                # Try to iterate through the result
                print("\n📊 Iterating through result:")
                for i, item in enumerate(first_result):
                    print(f"   Item {i}: {type(item)} - {item}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_ocr_extraction():
    """Test simple OCR text extraction."""
    print("\n🧪 Testing Simple OCR Extraction")
    print("=" * 50)
    
    try:
        from paddleocr import PaddleOCR
        
        # Initialize PaddleOCR
        ocr = PaddleOCR(use_textline_orientation=True, lang='en')
        
        # Create a simple test image
        img = Image.new('RGB', (300, 150), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((20, 20), "Test Invoice", fill='black')
        draw.text((20, 50), "Amount: £100.00", fill='black')
        
        # Run OCR
        result = ocr.predict(np.array(img))
        
        # Extract text safely
        text = ""
        confidence_scores = []
        
        print(f"📊 Processing result of type: {type(result)}")
        
        if result and len(result) > 0:
            print(f"📊 Found {len(result)} result groups")
            
            for i, line in enumerate(result):
                print(f"   Group {i}: {type(line)} - {line}")
                
                if line and len(line) > 0:
                    print(f"     Group {i} has {len(line)} items")
                    
                    for j, item in enumerate(line):
                        print(f"       Item {j}: {type(item)} - {item}")
                        
                        if isinstance(item, (list, tuple)) and len(item) >= 2:
                            extracted_text = str(item[1])
                            confidence = float(item[2]) if len(item) > 2 else 0.0
                            
                            text += extracted_text + " "
                            confidence_scores.append(confidence)
                            
                            print(f"         → Extracted: '{extracted_text}' (confidence: {confidence:.2f})")
                        else:
                            print(f"         → Skipping item (not a valid OCR result)")
        
        text = text.strip()
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        print(f"\n📝 Final text: '{text}'")
        print(f"📊 Average confidence: {avg_confidence:.2f}")
        print(f"📊 Word count: {len(text.split())}")
        
        return len(text) > 0
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    print("🚀 PaddleOCR Structure Test")
    print("=" * 50)
    
    # Test 1: Understand result structure
    structure_ok = test_paddle_ocr_structure()
    
    # Test 2: Simple extraction
    extraction_ok = test_simple_ocr_extraction()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"✅ Structure Test: {'PASS' if structure_ok else 'FAIL'}")
    print(f"✅ Extraction Test: {'PASS' if extraction_ok else 'FAIL'}")
    
    if structure_ok and extraction_ok:
        print("\n🎉 ALL TESTS PASSED - PaddleOCR structure understood!")
    else:
        print("\n⚠️ Some tests failed - check the issues above")
    
    return structure_ok and extraction_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 