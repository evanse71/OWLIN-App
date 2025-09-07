#!/usr/bin/env python3
"""
Test Actual OCR Processing

This script tests the actual OCR processing to see if the 0% confidence issue is resolved.
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_actual_ocr_processing():
    """Test actual OCR processing with a real file"""
    print("🔍 Testing actual OCR processing...")
    
    # Find a test file
    test_file = Path("data/uploads/435413ea-91fa-43f7-8c24-cc1cc9dacc10_20250804_213536.pdf")
    if not test_file.exists():
        print("❌ No test file found")
        return False
    
    try:
        from backend.upload.adaptive_processor import AdaptiveProcessor
        
        print(f"📄 Testing with file: {test_file}")
        
        # Create adaptive processor
        processor = AdaptiveProcessor()
        
        # Process the document
        print("🔄 Processing document...")
        result = processor.process_with_recovery(str(test_file))
        
        print(f"📊 Processing Results:")
        print(f"   Document Type: {result.document_type}")
        print(f"   Supplier: {result.supplier}")
        print(f"   Invoice Number: {result.invoice_number}")
        print(f"   Overall Confidence: {result.overall_confidence}")
        print(f"   Line Items Count: {len(result.line_items)}")
        print(f"   Pages Processed: {result.pages_processed}")
        print(f"   Pages Failed: {result.pages_failed}")
        print(f"   Total Processing Time: {result.total_processing_time}")
        
        if result.line_items:
            print(f"   First Line Item: {result.line_items[0]}")
        
        # Check if processing was successful
        success = result.overall_confidence > 0.1 or len(result.line_items) > 0
        print(f"   Processing Success: {success}")
        
        if result.overall_confidence == 0.0:
            print("⚠️ Warning: Overall confidence is 0% - this indicates OCR processing failed")
            return False
        
        return success
        
    except Exception as e:
        print(f"❌ OCR processing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ocr_engine_directly():
    """Test OCR engine directly"""
    print("\n🔍 Testing OCR engine directly...")
    
    try:
        from backend.ocr.enhanced_ocr_engine import enhanced_ocr_engine
        from PIL import Image
        import numpy as np
        
        # Create a simple test image
        test_image = Image.new('RGB', (100, 50), color='white')
        
        print("🔄 Testing Tesseract OCR...")
        results = enhanced_ocr_engine._run_tesseract_raw(test_image, 1)
        
        print(f"   Tesseract Results: {len(results)} text blocks found")
        for i, result in enumerate(results[:3]):  # Show first 3 results
            print(f"     {i+1}. Text: '{result.text}', Confidence: {result.confidence:.3f}")
        
        return True
        
    except Exception as e:
        print(f"❌ OCR engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run OCR tests"""
    print("🔬 Actual OCR Processing Test")
    print("=" * 40)
    
    # Test 1: OCR engine directly
    if not test_ocr_engine_directly():
        print("❌ OCR engine test failed")
        return
    
    # Test 2: Actual OCR processing
    if not test_actual_ocr_processing():
        print("❌ Actual OCR processing failed")
        return
    
    print("\n✅ All OCR tests completed!")

if __name__ == "__main__":
    main() 