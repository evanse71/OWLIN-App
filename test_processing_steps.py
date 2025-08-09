#!/usr/bin/env python3
"""
Processing Steps Tests

This script tests the actual processing steps with timeouts to prevent hanging.
"""

import sys
import os
import signal
import time
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Function timed out")

def run_with_timeout(func, timeout_seconds=30):
    """Run a function with a timeout"""
    def wrapper(*args, **kwargs):
        # Set the signal handler
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)
        
        try:
            result = func(*args, **kwargs)
            signal.alarm(0)  # Cancel the alarm
            return result
        except TimeoutError:
            print(f"⏰ Function timed out after {timeout_seconds} seconds")
            return False
        except Exception as e:
            signal.alarm(0)  # Cancel the alarm
            print(f"❌ Function failed: {e}")
            return False
    
    return wrapper

def test_1_convert_pdf():
    """Test 1: Convert PDF to images"""
    print("Test 1: Convert PDF to images")
    try:
        from backend.upload.multi_page_processor import MultiPageProcessor
        
        processor = MultiPageProcessor()
        test_file = Path("data/uploads/435413ea-91fa-43f7-8c24-cc1cc9dacc10_20250804_213536.pdf")
        
        print("🔄 Converting PDF to images...")
        images = processor._convert_to_images(str(test_file))
        
        print(f"✅ Converted {len(images)} images")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def test_2_process_single_page():
    """Test 2: Process single page"""
    print("Test 2: Process single page")
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
        print(f"❌ Failed: {e}")
        return False

def test_3_ocr_engine_call():
    """Test 3: OCR engine call"""
    print("Test 3: OCR engine call")
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
        print(f"❌ Failed: {e}")
        return False

def test_4_adaptive_processor():
    """Test 4: Adaptive processor"""
    print("Test 4: Adaptive processor")
    try:
        from backend.upload.adaptive_processor import AdaptiveProcessor
        
        processor = AdaptiveProcessor()
        print("✅ Adaptive processor created")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def test_5_full_processing_with_timeout():
    """Test 5: Full processing with timeout"""
    print("Test 5: Full processing with timeout")
    
    def full_processing():
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
            return False
    
    # Run with 60 second timeout
    return run_with_timeout(full_processing, 60)()

def main():
    """Run all processing tests"""
    print("🔬 Processing Steps Tests")
    print("=" * 30)
    
    tests = [
        test_1_convert_pdf,
        test_2_process_single_page,
        test_3_ocr_engine_call,
        test_4_adaptive_processor,
        test_5_full_processing_with_timeout,
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
        print("🎉 All processing tests passed!")
    else:
        print("⚠️ Some processing tests failed")

if __name__ == "__main__":
    main() 