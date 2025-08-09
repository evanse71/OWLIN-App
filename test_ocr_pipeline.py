#!/usr/bin/env python3
"""
Comprehensive OCR Pipeline Test Script
Tests the complete OCR pipeline including Tesseract configuration, preprocessing, and data extraction.
"""

import os
import sys
import logging
import numpy as np
import cv2
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from ocr_factory import get_ocr_recognizer, test_tesseract_with_sample_image
from ocr_preprocessing import OCRPreprocessor, create_preprocessing_config
from file_processor import FileProcessor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_invoice_image():
    """Create a test invoice image for OCR testing."""
    # Create a white background
    img = np.ones((800, 600, 3), dtype=np.uint8) * 255
    
    # Add text to simulate an invoice
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.7
    thickness = 2
    color = (0, 0, 0)
    
    # Invoice header
    cv2.putText(img, "INVOICE", (50, 50), font, 1.5, color, thickness)
    cv2.putText(img, "Invoice #: INV-2024-001", (50, 100), font, font_scale, color, thickness)
    cv2.putText(img, "Date: 12/15/2024", (50, 130), font, font_scale, color, thickness)
    
    # Vendor information
    cv2.putText(img, "Vendor: Test Company Inc.", (50, 180), font, font_scale, color, thickness)
    cv2.putText(img, "123 Business St", (50, 210), font, font_scale, color, thickness)
    cv2.putText(img, "City, State 12345", (50, 240), font, font_scale, color, thickness)
    
    # Invoice details
    cv2.putText(img, "Description", (50, 300), font, font_scale, color, thickness)
    cv2.putText(img, "Amount", (400, 300), font, font_scale, color, thickness)
    cv2.putText(img, "Services Rendered", (50, 340), font, font_scale, color, thickness)
    cv2.putText(img, "$1,250.00", (400, 340), font, font_scale, color, thickness)
    
    # Total
    cv2.putText(img, "Total Amount: $1,250.00", (50, 450), font, 1.0, color, thickness)
    cv2.putText(img, "Due Date: 01/15/2025", (50, 480), font, font_scale, color, thickness)
    
    return img

def test_tesseract_configuration():
    """Test Tesseract configuration and availability."""
    logger.info("=== Testing Tesseract Configuration ===")
    
    try:
        # Test Tesseract path detection
        from ocr_factory import get_tesseract_path
        tesseract_path = get_tesseract_path()
        logger.info(f"Tesseract path: {tesseract_path}")
        
        # Test OCR recognizer creation
        recognizer = get_ocr_recognizer()
        if recognizer:
            logger.info(f"OCR recognizer created successfully: {type(recognizer).__name__}")
        else:
            logger.error("Failed to create OCR recognizer")
            return False
        
        # Test with sample image
        test_image = create_test_invoice_image()
        text, confidence = recognizer.recognize(test_image)
        logger.info(f"Sample OCR result: {len(text)} chars, {confidence:.2f} confidence")
        logger.info(f"Sample text preview: {text[:100]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"Tesseract configuration test failed: {e}")
        return False

def test_preprocessing_pipeline():
    """Test the preprocessing pipeline."""
    logger.info("=== Testing Preprocessing Pipeline ===")
    
    try:
        # Create test image
        test_image = create_test_invoice_image()
        
        # Create preprocessor with different configurations
        configs = [
            create_preprocessing_config('bilateral', 'adaptive', 'clahe', True),  # Standard
            create_preprocessing_config('tv_chambolle', 'otsu', 'histogram_equalization', True),  # Enhanced
            create_preprocessing_config('gaussian', 'local', 'gamma', False)  # Minimal
        ]
        
        for i, config in enumerate(configs):
            logger.info(f"Testing config {i+1}: {config['denoising']['method']}")
            
            preprocessor = OCRPreprocessor(config)
            
            # Test quality assessment
            quality_score = preprocessor.assess_image_quality(test_image)
            logger.info(f"Quality score: {quality_score:.3f}")
            
            # Test preprocessing
            processed_image = preprocessor.preprocess_image(test_image)
            
            # Test preprocessing stats
            stats = preprocessor.get_preprocessing_stats(test_image, processed_image)
            logger.info(f"Preprocessing stats: contrast_improvement={stats.get('contrast_improvement', 0):.3f}, noise_reduction={stats.get('noise_reduction', 0):.3f}")
            
            # Save test images
            cv2.imwrite(f"test_original_{i+1}.png", test_image)
            cv2.imwrite(f"test_processed_{i+1}.png", processed_image)
            logger.info(f"Saved test images: test_original_{i+1}.png, test_processed_{i+1}.png")
        
        return True
        
    except Exception as e:
        logger.error(f"Preprocessing pipeline test failed: {e}")
        return False

def test_file_processor():
    """Test the file processor with OCR integration."""
    logger.info("=== Testing File Processor ===")
    
    try:
        # Create file processor
        processor = FileProcessor()
        
        # Initialize OCR
        processor.initialize_ocr()
        
        # Create test image
        test_image = create_test_invoice_image()
        
        # Save test image
        test_file_path = "test_invoice.png"
        cv2.imwrite(test_file_path, test_image)
        
        # Process the test file
        file_id = "test_001"
        result = processor.perform_ocr_with_preprocessing(test_image, file_id)
        
        logger.info("OCR Processing Results:")
        logger.info(f"  Text length: {len(result['text'])}")
        logger.info(f"  Confidence: {result['confidence']:.3f}")
        logger.info(f"  Original confidence: {result['original_confidence']:.3f}")
        logger.info(f"  Confidence improvement: {result['confidence_improvement']:.3f}")
        logger.info(f"  Processing time: {result['processing_time']:.2f}s")
        logger.info(f"  Quality score: {result['quality_score']:.3f}")
        
        # Extract invoice data
        extracted_data = processor.extract_invoice_data(result['text'], file_id)
        logger.info(f"Extracted data: {extracted_data}")
        
        # Clean up
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
        
        return True
        
    except Exception as e:
        logger.error(f"File processor test failed: {e}")
        return False

def test_error_handling():
    """Test error handling in the OCR pipeline."""
    logger.info("=== Testing Error Handling ===")
    
    try:
        # Test with invalid image
        invalid_image = np.zeros((10, 10, 3), dtype=np.uint8)  # Very small image
        
        processor = FileProcessor()
        processor.initialize_ocr()
        
        result = processor.perform_ocr_with_preprocessing(invalid_image, "test_error")
        
        logger.info(f"Error handling test result: {len(result['text'])} chars, {result['confidence']:.3f} confidence")
        
        return True
        
    except Exception as e:
        logger.error(f"Error handling test failed: {e}")
        return False

def main():
    """Run all OCR pipeline tests."""
    logger.info("Starting OCR Pipeline Tests")
    
    tests = [
        ("Tesseract Configuration", test_tesseract_configuration),
        ("Preprocessing Pipeline", test_preprocessing_pipeline),
        ("File Processor", test_file_processor),
        ("Error Handling", test_error_handling)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running {test_name} Test")
        logger.info(f"{'='*50}")
        
        try:
            success = test_func()
            results[test_name] = "PASS" if success else "FAIL"
        except Exception as e:
            logger.error(f"Test {test_name} failed with exception: {e}")
            results[test_name] = "ERROR"
    
    # Print summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    for test_name, result in results.items():
        logger.info(f"{test_name}: {result}")
    
    # Overall result
    passed = sum(1 for result in results.values() if result == "PASS")
    total = len(results)
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! OCR pipeline is working correctly.")
        return 0
    else:
        logger.error("❌ Some tests failed. Please check the logs above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 