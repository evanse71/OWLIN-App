#!/usr/bin/env python3
"""
Tiny Steps OCR Test

This script tests OCR processing in incredibly small steps to identify where it's getting stuck.
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_step1_imports():
    """Step 1: Test basic imports"""
    print("🔍 Step 1: Testing basic imports...")
    try:
        from backend.ocr.ocr_engine import OCRResult
        print("✅ OCRResult imported")
        return True
    except Exception as e:
        print(f"❌ OCRResult import failed: {e}")
        return False

def test_step2_document_result():
    """Step 2: Test DocumentResult import"""
    print("\n🔍 Step 2: Testing DocumentResult import...")
    try:
        from backend.upload.multi_page_processor import DocumentResult
        print("✅ DocumentResult imported")
        return True
    except Exception as e:
        print(f"❌ DocumentResult import failed: {e}")
        return False

def test_step3_ocr_engine_import():
    """Step 3: Test OCR engine import"""
    print("\n🔍 Step 3: Testing OCR engine import...")
    try:
        from backend.ocr.enhanced_ocr_engine import EnhancedOCREngine
        print("✅ EnhancedOCREngine imported")
        return True
    except Exception as e:
        print(f"❌ EnhancedOCREngine import failed: {e}")
        return False

def test_step4_ocr_engine_creation():
    """Step 4: Test OCR engine creation"""
    print("\n🔍 Step 4: Testing OCR engine creation...")
    try:
        from backend.ocr.enhanced_ocr_engine import EnhancedOCREngine
        engine = EnhancedOCREngine()
        print("✅ OCR engine created")
        return True
    except Exception as e:
        print(f"❌ OCR engine creation failed: {e}")
        return False

def test_step5_tesseract_check():
    """Step 5: Test Tesseract availability"""
    print("\n🔍 Step 5: Testing Tesseract availability...")
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract available: {version}")
        return True
    except Exception as e:
        print(f"❌ Tesseract check failed: {e}")
        return False

def test_step6_pil_import():
    """Step 6: Test PIL import"""
    print("\n🔍 Step 6: Testing PIL import...")
    try:
        from PIL import Image
        print("✅ PIL imported")
        return True
    except Exception as e:
        print(f"❌ PIL import failed: {e}")
        return False

def test_step7_create_test_image():
    """Step 7: Test creating test image"""
    print("\n🔍 Step 7: Testing test image creation...")
    try:
        from PIL import Image
        test_image = Image.new('RGB', (100, 50), color='white')
        print("✅ Test image created")
        return True
    except Exception as e:
        print(f"❌ Test image creation failed: {e}")
        return False

def test_step8_file_check():
    """Step 8: Test file existence"""
    print("\n🔍 Step 8: Testing file existence...")
    test_file = Path("data/uploads/435413ea-91fa-43f7-8c24-cc1cc9dacc10_20250804_213536.pdf")
    if test_file.exists():
        print(f"✅ Test file exists: {test_file}")
        return True
    else:
        print(f"❌ Test file not found: {test_file}")
        return False

def test_step9_multi_page_processor_import():
    """Step 9: Test MultiPageProcessor import"""
    print("\n🔍 Step 9: Testing MultiPageProcessor import...")
    try:
        from backend.upload.multi_page_processor import MultiPageProcessor
        print("✅ MultiPageProcessor imported")
        return True
    except Exception as e:
        print(f"❌ MultiPageProcessor import failed: {e}")
        return False

def test_step10_processor_creation():
    """Step 10: Test processor creation"""
    print("\n🔍 Step 10: Testing processor creation...")
    try:
        from backend.upload.multi_page_processor import MultiPageProcessor
        processor = MultiPageProcessor()
        print("✅ Processor created")
        return True
    except Exception as e:
        print(f"❌ Processor creation failed: {e}")
        return False

def test_step11_convert_images():
    """Step 11: Test converting PDF to images"""
    print("\n🔍 Step 11: Testing PDF to images conversion...")
    try:
        from backend.upload.multi_page_processor import MultiPageProcessor
        processor = MultiPageProcessor()
        
        test_file = Path("data/uploads/435413ea-91fa-43f7-8c24-cc1cc9dacc10_20250804_213536.pdf")
        print("🔄 Converting PDF to images...")
        images = processor._convert_to_images(str(test_file))
        
        print(f"✅ Converted {len(images)} images")
        return True
    except Exception as e:
        print(f"❌ PDF conversion failed: {e}")
        return False

def test_step12_process_first_page():
    """Step 12: Test processing first page"""
    print("\n🔍 Step 12: Testing first page processing...")
    try:
        from backend.upload.multi_page_processor import MultiPageProcessor
        
        processor = MultiPageProcessor()
        test_file = Path("data/uploads/435413ea-91fa-43f7-8c24-cc1cc9dacc10_20250804_213536.pdf")
        
        print("🔄 Converting PDF to images...")
        images = processor._convert_to_images(str(test_file))
        
        if not images:
            print("❌ No images extracted")
            return False
        
        print("🔄 Processing first page...")
        page_result = processor._process_single_page(images[0], 1)
        
        print(f"✅ Page processed - Confidence: {page_result.confidence}")
        return True
    except Exception as e:
        print(f"❌ First page processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_step13_ocr_engine_call():
    """Step 13: Test calling OCR engine directly"""
    print("\n🔍 Step 13: Testing OCR engine call...")
    try:
        from backend.ocr.enhanced_ocr_engine import EnhancedOCREngine
        from PIL import Image
        
        engine = EnhancedOCREngine()
        test_image = Image.new('RGB', (100, 50), color='white')
        
        print("🔄 Calling Tesseract OCR...")
        results = engine._run_tesseract_raw(test_image, 1)
        
        print(f"✅ OCR completed - {len(results)} results")
        return True
    except Exception as e:
        print(f"❌ OCR engine call failed: {e}")
        return False

def test_step14_adaptive_processor():
    """Step 14: Test adaptive processor"""
    print("\n🔍 Step 14: Testing adaptive processor...")
    try:
        from backend.upload.adaptive_processor import AdaptiveProcessor
        
        processor = AdaptiveProcessor()
        print("✅ Adaptive processor created")
        return True
    except Exception as e:
        print(f"❌ Adaptive processor creation failed: {e}")
        return False

def test_step15_full_processing():
    """Step 15: Test full processing (this is where it was getting stuck)"""
    print("\n🔍 Step 15: Testing full processing...")
    try:
        from backend.upload.adaptive_processor import AdaptiveProcessor
        
        processor = AdaptiveProcessor()
        test_file = Path("data/uploads/435413ea-91fa-43f7-8c24-cc1cc9dacc10_20250804_213536.pdf")
        
        print("🔄 Starting full processing...")
        result = processor.process_with_recovery(str(test_file))
        
        print(f"✅ Full processing completed!")
        print(f"   Document Type: {result.document_type}")
        print(f"   Confidence: {result.overall_confidence}")
        print(f"   Line Items: {len(result.line_items)}")
        
        return True
    except Exception as e:
        print(f"❌ Full processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run tiny step tests"""
    print("🔬 Tiny Steps OCR Test")
    print("=" * 40)
    
    steps = [
        test_step1_imports,
        test_step2_document_result,
        test_step3_ocr_engine_import,
        test_step4_ocr_engine_creation,
        test_step5_tesseract_check,
        test_step6_pil_import,
        test_step7_create_test_image,
        test_step8_file_check,
        test_step9_multi_page_processor_import,
        test_step10_processor_creation,
        test_step11_convert_images,
        test_step12_process_first_page,
        test_step13_ocr_engine_call,
        test_step14_adaptive_processor,
        test_step15_full_processing,
    ]
    
    for i, step in enumerate(steps, 1):
        print(f"\n--- Step {i} ---")
        if not step():
            print(f"❌ Failed at step {i}")
            return
        print(f"✅ Step {i} completed")
    
    print("\n✅ All tiny steps completed!")

if __name__ == "__main__":
    main() 