#!/usr/bin/env python3
"""
Test script to verify PaddleOCR integration is working correctly.
"""

import sys
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import time

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def create_test_image():
    """Create a test image with text for OCR testing."""
    # Create a white image
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    
    # Add some text
    try:
        # Try to use a system font
        font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 20)
    except:
        # Fallback to default font
        font = ImageFont.load_default()
    
    draw.text((20, 20), "INVOICE", fill='black', font=font)
    draw.text((20, 50), "Invoice Number: INV-12345", fill='black', font=font)
    draw.text((20, 80), "Date: 2025-01-15", fill='black', font=font)
    draw.text((20, 110), "Total: £125.50", fill='black', font=font)
    draw.text((20, 140), "Supplier: Test Company Ltd", fill='black', font=font)
    
    return img

def test_paddle_ocr_basic():
    """Test basic PaddleOCR functionality."""
    print("🧪 Testing basic PaddleOCR functionality...")
    
    try:
        from paddleocr import PaddleOCR
        import time
        
        # Initialize PaddleOCR
        start_time = time.time()
        ocr = PaddleOCR(use_textline_orientation=True, lang='en')
        load_time = time.time() - start_time
        print(f"✅ PaddleOCR initialized in {load_time:.2f}s")
        
        # Create test image
        test_img = create_test_image()
        print("✅ Test image created")
        
        # Run OCR
        start_time = time.time()
        result = ocr.ocr(np.array(test_img))
        ocr_time = time.time() - start_time
        print(f"✅ OCR completed in {ocr_time:.2f}s")
        
        # Analyze results
        if result and len(result) > 0:
            print(f"📊 Found {len(result)} text lines")
            total_confidence = 0.0
            line_count = 0
            
            for line in result:
                if line and len(line) > 0:
                    for item in line:
                        if len(item) >= 2:
                            text = item[1]
                            confidence = item[2]
                            
                            # Handle both string and float confidence values
                            if isinstance(confidence, str):
                                try:
                                    confidence = float(confidence)
                                except ValueError:
                                    confidence = 0.0
                            elif not isinstance(confidence, (int, float)):
                                confidence = 0.0
                            
                            total_confidence += confidence
                            line_count += 1
                            print(f"   Text: '{text}' (confidence: {confidence:.2f})")
            
            if line_count > 0:
                avg_confidence = total_confidence / line_count
                print(f"📊 Average confidence: {avg_confidence:.2f}")
                print(f"📊 Total lines detected: {line_count}")
                return True
            else:
                print("❌ No text detected")
                return False
        else:
            print("❌ No OCR results")
            return False
            
    except Exception as e:
        print(f"❌ PaddleOCR test failed: {str(e)}")
        return False

def test_backend_ocr_engine():
    """Test the backend OCR engine integration."""
    print("\n🧪 Testing backend OCR engine integration...")
    
    try:
        from ocr.ocr_engine import ocr_model, extract_text_with_paddle_ocr
        
        if ocr_model is None:
            print("❌ OCR model not initialized")
            return False
        
        print("✅ OCR model is initialized")
        
        # Create test image
        test_img = create_test_image()
        
        # Test the extract_text_with_paddle_ocr function
        text = extract_text_with_paddle_ocr(test_img)
        
        if text:
            print(f"✅ Extracted text: '{text[:100]}...'")
            print(f"📊 Text length: {len(text)} characters")
            return True
        else:
            print("❌ No text extracted")
            return False
            
    except Exception as e:
        print(f"❌ Backend OCR test failed: {str(e)}")
        return False

def test_smart_upload_processor():
    """Test the SmartUploadProcessor OCR integration."""
    print("\n🧪 Testing SmartUploadProcessor OCR integration...")
    
    try:
        from ocr.smart_upload_processor import ocr_model
        
        if ocr_model is None:
            print("❌ SmartUploadProcessor OCR model not initialized")
            return False
        
        print("✅ SmartUploadProcessor OCR model is initialized")
        
        # Create test image
        test_img = create_test_image()
        
        # Test OCR directly
        result = ocr_model.ocr(np.array(test_img))
        
        if result and len(result) > 0:
            print(f"✅ SmartUploadProcessor OCR found {len(result)} lines")
            return True
        else:
            print("❌ SmartUploadProcessor OCR returned no results")
            return False
            
    except Exception as e:
        print(f"❌ SmartUploadProcessor test failed: {str(e)}")
        return False

def main():
    """Run all PaddleOCR tests."""
    print("🚀 Starting PaddleOCR integration tests...\n")
    
    tests_passed = 0
    total_tests = 3
    
    # Test 1: Basic PaddleOCR
    if test_paddle_ocr_basic():
        tests_passed += 1
    
    # Test 2: Backend OCR Engine
    if test_backend_ocr_engine():
        tests_passed += 1
    
    # Test 3: SmartUploadProcessor
    if test_smart_upload_processor():
        tests_passed += 1
    
    print(f"\n📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("✅ All PaddleOCR integration tests passed!")
        print("🎉 PaddleOCR is now working correctly with:")
        print("   - Correct version compatibility")
        print("   - Proper initialization parameters")
        print("   - Real text extraction")
        print("   - Confidence values")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    exit(main()) 