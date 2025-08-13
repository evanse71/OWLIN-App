#!/usr/bin/env python3
"""
Test Tesseract-Only OCR

This script tests the upload flow using only Tesseract OCR.
"""

import sys
import os
import time
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_tesseract_ocr():
    """Test Tesseract OCR functionality"""
    print("🔍 Testing Tesseract OCR...")
    try:
        from backend.ocr.enhanced_ocr_engine import EnhancedOCREngine
        from PIL import Image
        
        engine = EnhancedOCREngine()
        test_image = Image.new('RGB', (200, 100), color='white')
        
        print("🔄 Running Tesseract OCR...")
        results = engine._run_tesseract_raw(test_image, 1)
        
        print(f"✅ Tesseract OCR completed - {len(results)} results")
        return True
    except Exception as e:
        print(f"❌ Tesseract test failed: {e}")
        return False

def test_document_processing():
    """Test document processing with Tesseract only"""
    print("\n🔍 Testing document processing...")
    try:
        from backend.upload.adaptive_processor import AdaptiveProcessor
        
        processor = AdaptiveProcessor()
        test_file = Path("data/uploads/435413ea-91fa-43f7-8c24-cc1cc9dacc10_20250804_213536.pdf")
        
        if not test_file.exists():
            print("❌ Test file not found")
            return False
        
        print("🔄 Processing document with Tesseract...")
        start_time = time.time()
        result = processor.process_with_recovery(str(test_file))
        processing_time = time.time() - start_time
        
        print(f"✅ Document processing completed in {processing_time:.1f} seconds!")
        print(f"   Document Type: {result.document_type}")
        print(f"   Confidence: {result.overall_confidence}")
        print(f"   Line Items: {len(result.line_items)}")
        print(f"   Pages Processed: {result.pages_processed}")
        
        # Check if we got meaningful results
        if result.overall_confidence > 0 or len(result.line_items) > 0:
            print("✅ Processing successful with meaningful results")
            return True
        else:
            print("⚠️ Processing completed but no meaningful results")
            return False
        
    except Exception as e:
        print(f"❌ Document processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_upload_endpoint():
    """Test the upload endpoint"""
    print("\n🔍 Testing upload endpoint...")
    try:
        import requests
        
        # Test the minimal backend
        response = requests.get("http://localhost:8001/api/upload/test", timeout=10)
        if response.status_code == 200:
            result = response.json()
            print("✅ Upload endpoint working")
            print(f"   Success: {result.get('success', False)}")
            return True
        else:
            print(f"❌ Upload endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Upload endpoint test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🔬 Tesseract-Only OCR Test")
    print("=" * 30)
    
    # Test 1: Tesseract OCR
    if not test_tesseract_ocr():
        print("❌ Tesseract OCR test failed")
        return
    
    # Test 2: Document processing
    if not test_document_processing():
        print("❌ Document processing test failed")
        return
    
    # Test 3: Upload endpoint
    if not test_upload_endpoint():
        print("❌ Upload endpoint test failed")
        return
    
    print("\n🎉 All tests passed!")
    print("The upload flow should now work with Tesseract OCR.")

if __name__ == "__main__":
    main() 