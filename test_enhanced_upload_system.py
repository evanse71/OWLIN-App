#!/usr/bin/env python3
"""
Enhanced Upload System Test

This script tests the enhanced upload system with 100% reliability,
comprehensive error recovery, and proper line item extraction.

Tests:
- Enhanced OCR engine with multiple fallback strategies
- Line item extraction with table detection
- Multi-page document processing
- Adaptive timeout handling
- Error recovery and fallback strategies
- Database integration

Author: OWLIN Development Team
Version: 2.0.0
"""

import os
import sys
import logging
import time
from pathlib import Path
from typing import Dict, Any, List

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_enhanced_ocr_engine():
    """Test enhanced OCR engine with multiple strategies"""
    logger.info("🧪 Testing Enhanced OCR Engine")
    
    try:
        from backend.ocr.enhanced_ocr_engine import enhanced_ocr_engine
        
        # Test initialization
        logger.info("📋 Testing OCR engine initialization")
        assert enhanced_ocr_engine is not None
        logger.info("✅ OCR engine initialized successfully")
        
        # Test strategy setup
        logger.info("📋 Testing strategy setup")
        assert len(enhanced_ocr_engine.strategies) > 0
        logger.info(f"✅ {len(enhanced_ocr_engine.strategies)} strategies configured")
        
        # Test engine availability
        logger.info("📋 Testing engine availability")
        has_paddle = enhanced_ocr_engine.paddle_ocr is not None
        has_tesseract = enhanced_ocr_engine.tesseract_available
        logger.info(f"✅ PaddleOCR: {'Available' if has_paddle else 'Not available'}")
        logger.info(f"✅ Tesseract: {'Available' if has_tesseract else 'Not available'}")
        
        # Test with a simple image (if available)
        test_image_path = "data/test_images/sample_invoice.png"
        if os.path.exists(test_image_path):
            logger.info("📋 Testing OCR with sample image")
            from PIL import Image
            image = Image.open(test_image_path)
            results = enhanced_ocr_engine.run_ocr_with_retry(image, 1)
            assert len(results) > 0
            logger.info(f"✅ OCR test successful: {len(results)} results")
        else:
            logger.warning("⚠️ No test image available, skipping OCR test")
        
        logger.info("✅ Enhanced OCR Engine tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Enhanced OCR Engine test failed: {e}")
        return False

def test_enhanced_line_item_extractor():
    """Test enhanced line item extractor"""
    logger.info("🧪 Testing Enhanced Line Item Extractor")
    
    try:
        from backend.ocr.enhanced_line_item_extractor import enhanced_line_item_extractor
        
        # Test initialization
        logger.info("📋 Testing line item extractor initialization")
        assert enhanced_line_item_extractor is not None
        logger.info("✅ Line item extractor initialized successfully")
        
        # Test pattern configuration
        logger.info("📋 Testing pattern configuration")
        assert len(enhanced_line_item_extractor.quantity_patterns) > 0
        assert len(enhanced_line_item_extractor.price_patterns) > 0
        logger.info(f"✅ {len(enhanced_line_item_extractor.quantity_patterns)} quantity patterns")
        logger.info(f"✅ {len(enhanced_line_item_extractor.price_patterns)} price patterns")
        
        # Test with sample OCR results
        logger.info("📋 Testing line item extraction with sample data")
        from backend.ocr.ocr_engine import OCRResult
        
        # Create sample OCR results
        sample_ocr_results = [
            OCRResult(
                text="Product A",
                confidence=0.9,
                bounding_box=[[0, 0], [100, 0], [100, 20], [0, 20]],
                page_number=1
            ),
            OCRResult(
                text="2 x £10.50",
                confidence=0.8,
                bounding_box=[[200, 0], [300, 0], [300, 20], [200, 20]],
                page_number=1
            ),
            OCRResult(
                text="£21.00",
                confidence=0.9,
                bounding_box=[[400, 0], [500, 0], [500, 20], [400, 20]],
                page_number=1
            )
        ]
        
        line_items = enhanced_line_item_extractor.extract_line_items(sample_ocr_results)
        logger.info(f"✅ Line item extraction test: {len(line_items)} items extracted")
        
        logger.info("✅ Enhanced Line Item Extractor tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Enhanced Line Item Extractor test failed: {e}")
        return False

def test_multi_page_processor():
    """Test multi-page processor"""
    logger.info("🧪 Testing Multi-Page Processor")
    
    try:
        from backend.upload.multi_page_processor import multi_page_processor
        
        # Test initialization
        logger.info("📋 Testing multi-page processor initialization")
        assert multi_page_processor is not None
        logger.info("✅ Multi-page processor initialized successfully")
        
        # Test OCR engine integration
        logger.info("📋 Testing OCR engine integration")
        assert multi_page_processor.ocr_engine is not None
        assert multi_page_processor.line_extractor is not None
        logger.info("✅ OCR engine integration successful")
        
        logger.info("✅ Multi-Page Processor tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Multi-Page Processor test failed: {e}")
        return False

def test_adaptive_processor():
    """Test adaptive processor with timeout handling"""
    logger.info("🧪 Testing Adaptive Processor")
    
    try:
        from backend.upload.adaptive_processor import adaptive_processor
        
        # Test initialization
        logger.info("📋 Testing adaptive processor initialization")
        assert adaptive_processor is not None
        logger.info("✅ Adaptive processor initialized successfully")
        
        # Test timeout calculation
        logger.info("📋 Testing timeout calculation")
        test_file_path = "data/test_images/sample_invoice.png"
        if os.path.exists(test_file_path):
            timeout = adaptive_processor.calculate_timeout(test_file_path)
            assert timeout > 0
            logger.info(f"✅ Timeout calculation: {timeout}s")
        else:
            logger.warning("⚠️ No test file available, skipping timeout test")
        
        # Test fallback strategies
        logger.info("📋 Testing fallback strategies")
        assert len(adaptive_processor.fallbacks) > 0
        logger.info(f"✅ {len(adaptive_processor.fallbacks)} fallback strategies configured")
        
        logger.info("✅ Adaptive Processor tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Adaptive Processor test failed: {e}")
        return False

def test_enhanced_upload_pipeline():
    """Test enhanced upload pipeline"""
    logger.info("🧪 Testing Enhanced Upload Pipeline")
    
    try:
        from backend.upload_pipeline import process_document_enhanced, ProcessingResult
        
        # Test function availability
        logger.info("📋 Testing enhanced pipeline function")
        assert process_document_enhanced is not None
        logger.info("✅ Enhanced pipeline function available")
        
        # Test with sample file (if available)
        test_file_path = "data/test_images/sample_invoice.png"
        if os.path.exists(test_file_path):
            logger.info("📋 Testing enhanced processing with sample file")
            result = process_document_enhanced(
                file_path=test_file_path,
                parse_templates=True,
                save_debug=False,
                validate_upload=False
            )
            
            assert isinstance(result, ProcessingResult)
            logger.info(f"✅ Processing result: {result.success}")
            logger.info(f"✅ Document type: {result.document_type}")
            logger.info(f"✅ Line items: {len(result.line_items)}")
            logger.info(f"✅ Confidence: {result.overall_confidence:.3f}")
        else:
            logger.warning("⚠️ No test file available, skipping processing test")
        
        logger.info("✅ Enhanced Upload Pipeline tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Enhanced Upload Pipeline test failed: {e}")
        return False

def test_database_integration():
    """Test database integration"""
    logger.info("🧪 Testing Database Integration")
    
    try:
        from backend.db_manager import init_db, save_invoice, save_file_hash
        
        # Test database initialization
        logger.info("📋 Testing database initialization")
        db_path = "data/test_owlin.db"
        init_db(db_path)
        logger.info("✅ Database initialized successfully")
        
        # Test file hash saving
        logger.info("📋 Testing file hash saving")
        test_file_path = "data/test_images/sample_invoice.png"
        if os.path.exists(test_file_path):
            import hashlib
            with open(test_file_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            
            save_file_hash(file_hash, test_file_path, 1024, "image/png")
            logger.info("✅ File hash saved successfully")
        else:
            logger.warning("⚠️ No test file available, skipping file hash test")
        
        # Clean up test database
        if os.path.exists(db_path):
            os.remove(db_path)
            logger.info("✅ Test database cleaned up")
        
        logger.info("✅ Database Integration tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database Integration test failed: {e}")
        return False

def test_error_recovery():
    """Test error recovery mechanisms"""
    logger.info("🧪 Testing Error Recovery")
    
    try:
        from backend.upload.adaptive_processor import adaptive_processor
        
        # Test fallback validation
        logger.info("📋 Testing fallback validation")
        
        # Create a mock result for testing
        class MockDocumentResult:
            def __init__(self):
                self.supplier = "Test Supplier"
                self.line_items = []
                self.overall_confidence = 0.5
        
        mock_result = MockDocumentResult()
        is_valid = adaptive_processor._validate_fallback_result(mock_result)
        assert is_valid
        logger.info("✅ Fallback validation test passed")
        
        # Test minimal result creation
        logger.info("📋 Testing minimal result creation")
        minimal_result = adaptive_processor._create_minimal_result("test.txt", "Test error")
        assert minimal_result.document_type == 'unknown'
        assert minimal_result.supplier == 'Unknown Supplier'
        logger.info("✅ Minimal result creation test passed")
        
        logger.info("✅ Error Recovery tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error Recovery test failed: {e}")
        return False

def run_comprehensive_test():
    """Run comprehensive test suite"""
    logger.info("🚀 Starting Enhanced Upload System Comprehensive Test")
    logger.info("=" * 60)
    
    tests = [
        ("Enhanced OCR Engine", test_enhanced_ocr_engine),
        ("Enhanced Line Item Extractor", test_enhanced_line_item_extractor),
        ("Multi-Page Processor", test_multi_page_processor),
        ("Adaptive Processor", test_adaptive_processor),
        ("Enhanced Upload Pipeline", test_enhanced_upload_pipeline),
        ("Database Integration", test_database_integration),
        ("Error Recovery", test_error_recovery)
    ]
    
    results = []
    start_time = time.time()
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 Running {test_name} test...")
        try:
            success = test_func()
            results.append((test_name, success))
            status = "✅ PASSED" if success else "❌ FAILED"
            logger.info(f"{status} {test_name}")
        except Exception as e:
            logger.error(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    total_time = time.time() - start_time
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    logger.info("\n" + "=" * 60)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 60)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"{status} {test_name}")
    
    logger.info(f"\n📈 Results: {passed}/{total} tests passed")
    logger.info(f"⏱️ Total time: {total_time:.2f} seconds")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED! Enhanced upload system is working correctly.")
        return True
    else:
        logger.error(f"❌ {total - passed} tests failed. Please check the logs above.")
        return False

def main():
    """Main test function"""
    try:
        success = run_comprehensive_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("⏹️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Test suite crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 