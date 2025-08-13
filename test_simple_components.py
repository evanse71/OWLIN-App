#!/usr/bin/env python3
"""
Simple Component Tests

This script tests each component independently to identify issues.
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_1_basic_imports():
    """Test 1: Basic imports only"""
    print("Test 1: Basic imports")
    try:
        from backend.ocr.ocr_engine import OCRResult
        print("✅ OCRResult imported")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def test_2_document_result():
    """Test 2: DocumentResult import"""
    print("Test 2: DocumentResult import")
    try:
        from backend.upload.multi_page_processor import DocumentResult
        print("✅ DocumentResult imported")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def test_3_ocr_engine_import():
    """Test 3: OCR engine import"""
    print("Test 3: OCR engine import")
    try:
        from backend.ocr.enhanced_ocr_engine import EnhancedOCREngine
        print("✅ EnhancedOCREngine imported")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def test_4_ocr_engine_creation():
    """Test 4: OCR engine creation"""
    print("Test 4: OCR engine creation")
    try:
        from backend.ocr.enhanced_ocr_engine import EnhancedOCREngine
        engine = EnhancedOCREngine()
        print("✅ OCR engine created")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def test_5_tesseract_check():
    """Test 5: Tesseract availability"""
    print("Test 5: Tesseract check")
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract available: {version}")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def test_6_pil_import():
    """Test 6: PIL import"""
    print("Test 6: PIL import")
    try:
        from PIL import Image
        print("✅ PIL imported")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def test_7_create_image():
    """Test 7: Create test image"""
    print("Test 7: Create test image")
    try:
        from PIL import Image
        test_image = Image.new('RGB', (100, 50), color='white')
        print("✅ Test image created")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def test_8_file_check():
    """Test 8: Check test file exists"""
    print("Test 8: File check")
    try:
        test_file = Path("data/uploads/435413ea-91fa-43f7-8c24-cc1cc9dacc10_20250804_213536.pdf")
        if test_file.exists():
            print(f"✅ Test file exists")
            return True
        else:
            print(f"❌ Test file not found")
            return False
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def test_9_processor_import():
    """Test 9: Processor import"""
    print("Test 9: Processor import")
    try:
        from backend.upload.multi_page_processor import MultiPageProcessor
        print("✅ MultiPageProcessor imported")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def test_10_processor_creation():
    """Test 10: Processor creation"""
    print("Test 10: Processor creation")
    try:
        from backend.upload.multi_page_processor import MultiPageProcessor
        processor = MultiPageProcessor()
        print("✅ Processor created")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🔬 Simple Component Tests")
    print("=" * 30)
    
    tests = [
        test_1_basic_imports,
        test_2_document_result,
        test_3_ocr_engine_import,
        test_4_ocr_engine_creation,
        test_5_tesseract_check,
        test_6_pil_import,
        test_7_create_image,
        test_8_file_check,
        test_9_processor_import,
        test_10_processor_creation,
    ]
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(tests, 1):
        print(f"\n--- Test {i} ---")
        if test():
            passed += 1
            print(f"✅ Test {i} passed")
        else:
            failed += 1
            print(f"❌ Test {i} failed")
    
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed!")
    else:
        print("⚠️ Some tests failed")

if __name__ == "__main__":
    main() 