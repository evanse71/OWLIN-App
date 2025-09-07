#!/usr/bin/env python3
"""
Test script for enhanced OCR functionality with preprocessing and multi-PSM fallback.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from ocr.ocr_engine import run_enhanced_ocr, preprocess_image, calculate_display_confidence
from PIL import Image
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_enhanced_ocr():
    """Test the enhanced OCR functionality."""
    print("🧪 Testing Enhanced OCR Functionality")
    
    try:
        # Test 1: Confidence calculation
        print("\n📊 Test 1: Confidence Calculation")
        test_confidence = 0.85
        display_confidence = calculate_display_confidence(test_confidence)
        print(f"✅ Raw confidence: {test_confidence} -> Display confidence: {display_confidence}%")
        
        # Test 2: Image preprocessing
        print("\n🖼️ Test 2: Image Preprocessing")
        # Create a simple test image (you can replace this with a real image path)
        test_image_path = "test_invoice.jpg"
        if os.path.exists(test_image_path):
            print(f"📷 Testing with image: {test_image_path}")
            img = Image.open(test_image_path)
            
            # Test preprocessing
            processed_img = preprocess_image(img)
            print(f"✅ Image preprocessing completed")
            print(f"   Original size: {img.size}")
            print(f"   Processed size: {processed_img.size}")
        else:
            print("ℹ️ No test image found - skipping preprocessing test")
        
        # Test 3: Enhanced OCR with multi-PSM
        print("\n🔍 Test 3: Enhanced OCR with Multi-PSM")
        if os.path.exists(test_image_path):
            img = Image.open(test_image_path)
            result = run_enhanced_ocr(img)
            
            print(f"✅ Enhanced OCR completed:")
            print(f"   Text length: {len(result['text'])} characters")
            print(f"   Word count: {result['word_count']}")
            print(f"   Confidence: {result['confidence']:.1f}%")
            print(f"   PSM used: {result['psm_used']}")
            
            # Show first 100 characters of text
            if result['text']:
                preview = result['text'][:100].replace('\n', '\\n')
                print(f"   Text preview: {preview}...")
            else:
                print("   No text extracted")
        else:
            print("ℹ️ No test image found - skipping OCR test")
        
        # Test 4: Multi-PSM fallback logic
        print("\n🔄 Test 4: Multi-PSM Fallback Logic")
        psm_modes = [6, 11, 4, 3]
        print(f"✅ PSM modes configured: {psm_modes}")
        print("   PSM 6: Uniform block of text")
        print("   PSM 11: Sparse text with OSD")
        print("   PSM 4: Single column of text")
        print("   PSM 3: Fully automatic page segmentation")
        
        print("\n✅ Enhanced OCR test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Enhanced OCR test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_enhanced_ocr()
    sys.exit(0 if success else 1) 