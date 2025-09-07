#!/usr/bin/env python3
"""
Step-by-Step OCR Test

This script tests OCR processing in small steps to identify where it's getting stuck.
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test basic imports"""
    print("🔍 Step 1: Testing imports...")
    try:
        from backend.ocr.ocr_engine import OCRResult
        print("✅ OCRResult imported")
        
        from backend.upload.multi_page_processor import DocumentResult
        print("✅ DocumentResult imported")
        
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_ocr_engine_creation():
    """Test creating OCR engine without loading models"""
    print("\n🔍 Step 2: Testing OCR engine creation...")
    try:
        from backend.ocr.enhanced_ocr_engine import EnhancedOCREngine
        
        print("🔄 Creating OCR engine...")
        engine = EnhancedOCREngine()
        print("✅ OCR engine created successfully")
        
        print(f"   Tesseract available: {engine.tesseract_available}")
        print(f"   PaddleOCR loaded: {engine.paddle_ocr is not None}")
        
        return True
    except Exception as e:
        print(f"❌ OCR engine creation failed: {e}")
        return False

def test_tesseract_only():
    """Test Tesseract OCR without PaddleOCR"""
    print("\n🔍 Step 3: Testing Tesseract OCR...")
    try:
        from backend.ocr.enhanced_ocr_engine import EnhancedOCREngine
        from PIL import Image
        
        engine = EnhancedOCREngine()
        
        # Create a simple test image with text
        test_image = Image.new('RGB', (200, 100), color='white')
        
        print("🔄 Testing Tesseract OCR...")
        results = engine._run_tesseract_raw(test_image, 1)
        
        print(f"   Tesseract Results: {len(results)} text blocks found")
        return True
    except Exception as e:
        print(f"❌ Tesseract test failed: {e}")
        return False

def test_file_conversion():
    """Test converting PDF to images"""
    print("\n🔍 Step 4: Testing file conversion...")
    
    test_file = Path("data/uploads/435413ea-91fa-43f7-8c24-cc1cc9dacc10_20250804_213536.pdf")
    if not test_file.exists():
        print("❌ No test file found")
        return False
    
    try:
        from backend.upload.multi_page_processor import MultiPageProcessor
        
        processor = MultiPageProcessor()
        
        print("🔄 Converting PDF to images...")
        images = processor._convert_to_images(str(test_file))
        
        print(f"   Converted {len(images)} images")
        return True
    except Exception as e:
        print(f"❌ File conversion failed: {e}")
        return False

def test_single_page_processing():
    """Test processing a single page"""
    print("\n🔍 Step 5: Testing single page processing...")
    
    test_file = Path("data/uploads/435413ea-91fa-43f7-8c24-cc1cc9dacc10_20250804_213536.pdf")
    if not test_file.exists():
        print("❌ No test file found")
        return False
    
    try:
        from backend.upload.multi_page_processor import MultiPageProcessor
        
        processor = MultiPageProcessor()
        
        print("🔄 Converting PDF to images...")
        images = processor._convert_to_images(str(test_file))
        
        if not images:
            print("❌ No images extracted")
            return False
        
        print(f"   Processing first page...")
        page_result = processor._process_single_page(images[0], 1)
        
        print(f"   Page confidence: {page_result.confidence}")
        print(f"   OCR results: {len(page_result.ocr_results)}")
        print(f"   Line items: {len(page_result.line_items)}")
        
        return True
    except Exception as e:
        print(f"❌ Single page processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run step-by-step tests"""
    print("🔬 Step-by-Step OCR Test")
    print("=" * 40)
    
    # Step 1: Imports
    if not test_imports():
        print("❌ Import test failed")
        return
    
    # Step 2: OCR engine creation
    if not test_ocr_engine_creation():
        print("❌ OCR engine creation failed")
        return
    
    # Step 3: Tesseract only
    if not test_tesseract_only():
        print("❌ Tesseract test failed")
        return
    
    # Step 4: File conversion
    if not test_file_conversion():
        print("❌ File conversion failed")
        return
    
    # Step 5: Single page processing
    if not test_single_page_processing():
        print("❌ Single page processing failed")
        return
    
    print("\n✅ All step-by-step tests completed!")

if __name__ == "__main__":
    main() 