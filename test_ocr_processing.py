#!/usr/bin/env python3
"""
Test script for OCR processing module integration

This script tests the new OCR processing module with fallback functionality,
including PaddleOCR primary and Tesseract fallback support.
"""

import os
import sys
import tempfile
import logging
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_ocr_processing_imports():
    """Test that all OCR processing modules can be imported"""
    try:
        from backend.ocr.ocr_processing import (
            run_ocr,
            run_ocr_with_fallback,
            validate_ocr_results,
            get_ocr_summary,
            TESSERACT_AVAILABLE
        )
        logger.info("✅ OCR processing imports successful")
        return True
    except ImportError as e:
        logger.error(f"❌ OCR processing import failed: {e}")
        return False

def test_ocr_fallback_availability():
    """Test OCR fallback availability"""
    try:
        from backend.ocr.ocr_processing import TESSERACT_AVAILABLE
        logger.info(f"📊 Tesseract available: {TESSERACT_AVAILABLE}")
        return TESSERACT_AVAILABLE
    except Exception as e:
        logger.error(f"❌ Error checking Tesseract availability: {e}")
        return False

def test_ocr_summary_functions():
    """Test OCR summary functions with mock data"""
    try:
        from backend.ocr.ocr_processing import get_ocr_summary, validate_ocr_results
        
        # Test with empty results
        empty_results = []
        summary = get_ocr_summary(empty_results)
        logger.info(f"📊 Empty results summary: {summary}")
        
        # Test with mock results
        mock_results = [
            {"text": "Invoice", "confidence": 85.5, "page_num": 1},
            {"text": "Number", "confidence": 92.3, "page_num": 1},
            {"text": "12345", "confidence": 78.9, "page_num": 1}
        ]
        summary = get_ocr_summary(mock_results)
        logger.info(f"📊 Mock results summary: {summary}")
        
        # Test validation
        is_valid = validate_ocr_results(mock_results)
        logger.info(f"✅ Mock results validation: {is_valid}")
        
        return True
    except Exception as e:
        logger.error(f"❌ OCR summary test failed: {e}")
        return False

def test_upload_pipeline_integration():
    """Test that the upload pipeline can use the new OCR processing"""
    try:
        from backend.upload_pipeline import process_document
        
        logger.info("✅ Upload pipeline integration successful")
        return True
    except Exception as e:
        logger.error(f"❌ Upload pipeline integration failed: {e}")
        return False

def test_ocr_module_exports():
    """Test that the OCR module exports the new functions"""
    try:
        from backend.ocr import (
            run_ocr,
            run_ocr_with_fallback,
            validate_ocr_results,
            get_ocr_summary,
            TESSERACT_AVAILABLE
        )
        logger.info("✅ OCR module exports successful")
        return True
    except ImportError as e:
        logger.error(f"❌ OCR module exports failed: {e}")
        return False

def test_fallback_strategy():
    """Test the fallback strategy logic"""
    try:
        from backend.ocr.ocr_processing import run_ocr_with_fallback
        
        # Test with a non-existent file (should return empty results)
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp_file:
            tmp_file.write(b"test")
            tmp_file.flush()
            
            # This should return empty results since it's a text file
            results = run_ocr_with_fallback(tmp_file.name, use_paddle_first=False)
            logger.info(f"📊 Fallback test results: {len(results)} items")
            
            os.unlink(tmp_file.name)
        
        return True
    except Exception as e:
        logger.error(f"❌ Fallback strategy test failed: {e}")
        return False

def test_backend_imports():
    """Test that the backend can import with the new OCR processing"""
    try:
        from backend.main import app
        logger.info("✅ Backend imports successful with new OCR processing")
        return True
    except Exception as e:
        logger.error(f"❌ Backend import failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🧪 Starting OCR processing integration tests...")
    
    tests = [
        ("OCR Processing Imports", test_ocr_processing_imports),
        ("OCR Fallback Availability", test_ocr_fallback_availability),
        ("OCR Summary Functions", test_ocr_summary_functions),
        ("Upload Pipeline Integration", test_upload_pipeline_integration),
        ("OCR Module Exports", test_ocr_module_exports),
        ("Fallback Strategy", test_fallback_strategy),
        ("Backend Imports", test_backend_imports)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n🔍 Running test: {test_name}")
        try:
            if test_func():
                logger.info(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                logger.error(f"❌ {test_name}: FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name}: ERROR - {e}")
    
    logger.info(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! OCR processing integration is working correctly.")
        return True
    else:
        logger.error("⚠️ Some tests failed. Please check the logs above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 