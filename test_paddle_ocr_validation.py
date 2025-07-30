#!/usr/bin/env python3
"""
Test script to validate PaddleOCR functionality in Owlin.
This script tests the PaddleOCR initialization, image processing, and text extraction.
"""

import sys
import os
import logging
import time
from PIL import Image
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_paddle_ocr_import():
    """Test PaddleOCR import and basic functionality."""
    print("🧪 Testing PaddleOCR Import and Initialization")
    print("=" * 50)
    
    try:
        from paddleocr import PaddleOCR
        print("✅ PaddleOCR imported successfully")
        
        # Test initialization with correct parameters
        print("🔄 Initializing PaddleOCR model...")
        start_time = time.time()
        
        ocr = PaddleOCR(use_textline_orientation=True, lang='en')
        
        init_time = time.time() - start_time
        print(f"✅ PaddleOCR initialized successfully in {init_time:.2f} seconds")
        
        return ocr
        
    except ImportError as e:
        print(f"❌ PaddleOCR import failed: {e}")
        print("🔧 Solution: Install PaddleOCR with: pip install paddleocr paddlepaddle")
        return None
    except Exception as e:
        print(f"❌ PaddleOCR initialization failed: {e}")
        return None

def test_ocr_on_sample_image(ocr_model):
    """Test OCR on a sample image."""
    print("\n🧪 Testing OCR on Sample Image")
    print("=" * 50)
    
    if ocr_model is None:
        print("❌ No OCR model available")
        return False
    
    # Create a simple test image with text
    try:
        # Create a test image with text
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a white image
        img = Image.new('RGB', (400, 200), color='white')
        draw = ImageDraw.Draw(img)
        
        # Add some text
        try:
            # Try to use a default font
            font = ImageFont.load_default()
        except:
            font = None
        
        draw.text((20, 20), "INVOICE # INV-001", fill='black', font=font)
        draw.text((20, 50), "Supplier: Test Company Ltd", fill='black', font=font)
        draw.text((20, 80), "Date: 2024-01-15", fill='black', font=font)
        draw.text((20, 110), "Total: £150.00", fill='black', font=font)
        
        # Save test image
        test_image_path = "data/debug/test_invoice.png"
        os.makedirs(os.path.dirname(test_image_path), exist_ok=True)
        img.save(test_image_path)
        print(f"✅ Created test image: {test_image_path}")
        
        # Run OCR
        print("🔄 Running OCR on test image...")
        start_time = time.time()
        
        result = ocr_model.predict(np.array(img))
        
        ocr_time = time.time() - start_time
        print(f"✅ OCR completed in {ocr_time:.2f} seconds")
        
        # Extract and display results
        text = ""
        confidence_scores = []
        
        if result and len(result) > 0:
            print(f"📊 Found {len(result)} result groups")
            
            for i, line in enumerate(result):
                if line and len(line) > 0:
                    print(f"   Group {i+1}: {len(line)} text items")
                    for j, item in enumerate(line):
                        if len(item) >= 2:
                            extracted_text = item[1]
                            confidence = item[2] if len(item) > 2 else 0.0
                            text += extracted_text + " "
                            confidence_scores.append(confidence)
                            print(f"     Item {j+1}: '{extracted_text}' (confidence: {confidence:.2f})")
        else:
            print("⚠️ No OCR results found")
        
        text = text.strip()
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        print(f"\n📝 Extracted Text: '{text}'")
        print(f"📊 Average Confidence: {avg_confidence:.2f}")
        print(f"📊 Word Count: {len(text.split())}")
        
        return len(text) > 0
        
    except Exception as e:
        print(f"❌ OCR test failed: {e}")
        return False

def test_backend_ocr_integration():
    """Test the backend OCR integration."""
    print("\n🧪 Testing Backend OCR Integration")
    print("=" * 50)
    
    try:
        # Import backend OCR functions
        sys.path.append('backend')
        from ocr.ocr_engine import run_paddle_ocr, PADDLEOCR_AVAILABLE, ocr_model
        
        print(f"✅ Backend OCR available: {PADDLEOCR_AVAILABLE}")
        print(f"✅ OCR model initialized: {ocr_model is not None}")
        
        if ocr_model is None:
            print("❌ OCR model not initialized in backend")
            return False
        
        # Test with a simple image
        from PIL import Image, ImageDraw
        
        # Create test image
        img = Image.new('RGB', (300, 150), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((20, 20), "Test Invoice", fill='black')
        draw.text((20, 50), "Amount: £100.00", fill='black')
        
        # Save test image
        test_path = "data/debug/test_backend.png"
        os.makedirs(os.path.dirname(test_path), exist_ok=True)
        img.save(test_path)
        
        print(f"✅ Created test image: {test_path}")
        
        # Test backend OCR
        print("🔄 Testing backend OCR function...")
        result = run_paddle_ocr(test_path)
        
        print(f"✅ Backend OCR completed")
        print(f"📊 Pages processed: {result.get('total_pages', 0)}")
        print(f"📊 Total words: {result.get('total_words', 0)}")
        print(f"📊 Overall confidence: {result.get('overall_confidence', 0):.2f}")
        print(f"📊 Text length: {len(result.get('raw_ocr_text', ''))}")
        
        return result.get('total_words', 0) > 0
        
    except Exception as e:
        print(f"❌ Backend OCR test failed: {e}")
        return False

def test_smart_upload_processor():
    """Test the SmartUploadProcessor OCR integration."""
    print("\n🧪 Testing SmartUploadProcessor OCR")
    print("=" * 50)
    
    try:
        from backend.ocr.smart_upload_processor import SmartUploadProcessor
        
        processor = SmartUploadProcessor()
        print("✅ SmartUploadProcessor initialized")
        
        # Create test image
        from PIL import Image, ImageDraw
        
        img = Image.new('RGB', (400, 200), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((20, 20), "INVOICE # INV-002", fill='black')
        draw.text((20, 50), "Supplier: Test Supplier", fill='black')
        draw.text((20, 80), "Date: 2024-01-16", fill='black')
        draw.text((20, 110), "Total: £200.00", fill='black')
        
        # Test OCR
        print("🔄 Testing SmartUploadProcessor OCR...")
        ocr_text = processor._run_ocr(img)
        
        print(f"✅ OCR completed")
        print(f"📝 Extracted text: '{ocr_text}'")
        print(f"📊 Word count: {len(ocr_text.split())}")
        
        return len(ocr_text) > 0
        
    except Exception as e:
        print(f"❌ SmartUploadProcessor test failed: {e}")
        return False

def test_image_quality_validation():
    """Test image quality validation and preprocessing."""
    print("\n🧪 Testing Image Quality Validation")
    print("=" * 50)
    
    try:
        from backend.ocr.ocr_engine import preprocess_image
        
        # Create test image
        from PIL import Image, ImageDraw
        
        img = Image.new('RGB', (400, 200), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((20, 20), "Quality Test Invoice", fill='black')
        draw.text((20, 50), "Testing image preprocessing", fill='black')
        
        print("🔄 Testing image preprocessing...")
        processed_img = preprocess_image(img)
        
        print(f"✅ Image preprocessing completed")
        print(f"📊 Original size: {img.size}")
        print(f"📊 Processed size: {processed_img.size}")
        
        # Test OCR on both original and processed
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(use_textline_orientation=True, lang='en')
        
        # Test original
        result_original = ocr.predict(np.array(img))
        text_original = ""
        if result_original and len(result_original) > 0:
            for line in result_original:
                if line and len(line) > 0:
                    for item in line:
                        if len(item) >= 2:
                            text_original += item[1] + " "
        
        # Test processed
        result_processed = ocr.predict(np.array(processed_img))
        text_processed = ""
        if result_processed and len(result_processed) > 0:
            for line in result_processed:
                if line and len(line) > 0:
                    for item in line:
                        if len(item) >= 2:
                            text_processed += item[1] + " "
        
        print(f"📝 Original text: '{text_original.strip()}'")
        print(f"📝 Processed text: '{text_processed.strip()}'")
        
        return len(text_original) > 0 or len(text_processed) > 0
        
    except Exception as e:
        print(f"❌ Image quality test failed: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 PaddleOCR Validation Test")
    print("=" * 50)
    
    # Test 1: Import and initialization
    ocr_model = test_paddle_ocr_import()
    
    # Test 2: Basic OCR functionality
    if ocr_model:
        ocr_working = test_ocr_on_sample_image(ocr_model)
    else:
        ocr_working = False
    
    # Test 3: Backend integration
    backend_working = test_backend_ocr_integration()
    
    # Test 4: Smart upload processor
    smart_upload_working = test_smart_upload_processor()
    
    # Test 5: Image quality validation
    quality_working = test_image_quality_validation()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"✅ PaddleOCR Import: {'PASS' if ocr_model else 'FAIL'}")
    print(f"✅ Basic OCR: {'PASS' if ocr_working else 'FAIL'}")
    print(f"✅ Backend Integration: {'PASS' if backend_working else 'FAIL'}")
    print(f"✅ Smart Upload: {'PASS' if smart_upload_working else 'FAIL'}")
    print(f"✅ Image Quality: {'PASS' if quality_working else 'FAIL'}")
    
    if all([ocr_model, ocr_working, backend_working, smart_upload_working, quality_working]):
        print("\n🎉 ALL TESTS PASSED - PaddleOCR is working correctly!")
    else:
        print("\n⚠️ Some tests failed - check the issues above")
    
    return all([ocr_model, ocr_working, backend_working, smart_upload_working, quality_working])

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 