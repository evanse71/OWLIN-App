#!/usr/bin/env python3
"""
Test script for the enhanced OCR pipeline.

This script tests the complete OCR pipeline including:
- OCR engine with page-by-page processing
- Table extraction from word boxes
- Line item extraction from text
- Invoice metadata parsing
- Confidence calculation
"""

import sys
import os
import logging
from datetime import datetime

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_ocr_engine():
    """Test the enhanced OCR engine."""
    logger.info("Testing OCR Engine...")
    
    try:
        from ocr.ocr_engine import run_ocr, preprocess_image
        
        # Test preprocessing function
        from PIL import Image
        import numpy as np
        
        # Create a simple test image
        test_img = Image.new('RGB', (100, 100), color='white')
        processed = preprocess_image(test_img)
        
        assert isinstance(processed, np.ndarray), "Preprocessing should return numpy array"
        logger.info("✓ Preprocessing function works")
        
        # Test OCR function (without actual PDF)
        logger.info("✓ OCR engine functions imported successfully")
        
    except Exception as e:
        logger.error(f"✗ OCR engine test failed: {str(e)}")
        return False
    
    return True

def test_table_extractor():
    """Test the table extractor module."""
    logger.info("Testing Table Extractor...")
    
    try:
        from ocr.table_extractor import (
            extract_table_data, 
            extract_line_items_from_text,
            find_line_item_section,
            parse_line_from_text
        )
        
        # Test with sample word boxes
        sample_words = [
            {'text': 'Item', 'left': 10, 'top': 10, 'width': 50, 'height': 20, 'conf': 90.0, 'page': 1},
            {'text': 'Qty', 'left': 100, 'top': 10, 'width': 30, 'height': 20, 'conf': 95.0, 'page': 1},
            {'text': 'Price', 'left': 200, 'top': 10, 'width': 60, 'height': 20, 'conf': 88.0, 'page': 1},
            {'text': 'Coffee', 'left': 10, 'top': 40, 'width': 80, 'height': 20, 'conf': 85.0, 'page': 1},
            {'text': '2', 'left': 100, 'top': 40, 'width': 20, 'height': 20, 'conf': 92.0, 'page': 1},
            {'text': '£3.50', 'left': 200, 'top': 40, 'width': 50, 'height': 20, 'conf': 87.0, 'page': 1},
        ]
        
        table_data = extract_table_data(sample_words)
        assert isinstance(table_data, list), "Table data should be a list"
        logger.info(f"✓ Table extraction works: {len(table_data)} rows extracted")
        
        # Test line item extraction from text
        sample_text = """
        Description Qty Unit Price Total
        Coffee 2 £3.50 £7.00
        Tea 1 £2.50 £2.50
        """
        
        line_items = extract_line_items_from_text(sample_text)
        assert isinstance(line_items, list), "Line items should be a list"
        logger.info(f"✓ Line item extraction from text works: {len(line_items)} items extracted")
        
        # Test section finding
        lines = sample_text.split('\n')
        section = find_line_item_section(lines)
        assert isinstance(section, list), "Section should be a list"
        logger.info(f"✓ Line item section finding works: {len(section)} lines found")
        
        # Test line parsing
        if section:
            line_item = parse_line_from_text(section[0])
            assert line_item is None or isinstance(line_item, dict), "Line item should be dict or None"
            logger.info("✓ Line parsing works")
        
    except Exception as e:
        logger.error(f"✗ Table extractor test failed: {str(e)}")
        return False
    
    return True

def test_parse_invoice():
    """Test the invoice parsing module."""
    logger.info("Testing Invoice Parser...")
    
    try:
        from ocr.parse_invoice import (
            extract_invoice_metadata,
            extract_line_items,
            calculate_confidence,
            create_line_item_dict
        )
        
        # Test metadata extraction
        sample_text = """
        INVOICE #12345
        Date: 15/12/2023
        From: Coffee Shop Ltd
        Total: £25.50
        VAT: £4.25
        Subtotal: £21.25
        """
        
        metadata = extract_invoice_metadata(sample_text)
        assert isinstance(metadata, dict), "Metadata should be a dictionary"
        assert 'invoice_number' in metadata, "Should extract invoice number"
        assert 'supplier_name' in metadata, "Should extract supplier name"
        assert 'total_amount' in metadata, "Should extract total amount"
        logger.info("✓ Metadata extraction works")
        
        # Test line item creation
        line_item = create_line_item_dict(
            item="Test Item",
            quantity=2.0,
            unit_price_excl_vat=10.0,
            line_total_excl_vat=20.0,
            vat_rate=0.2
        )
        assert isinstance(line_item, dict), "Line item should be a dictionary"
        assert line_item['item'] == "Test Item", "Should set item name"
        assert line_item['quantity'] == 2.0, "Should set quantity"
        logger.info("✓ Line item creation works")
        
        # Test confidence calculation
        parsed_data = {
            'invoice_number': '12345',
            'supplier_name': 'Test Supplier',
            'invoice_date': '2023-12-15',
            'total_amount': 25.50,
            'line_items': [line_item]
        }
        
        confidence = calculate_confidence(parsed_data)
        assert 0.0 <= confidence <= 1.0, "Confidence should be between 0 and 1"
        logger.info(f"✓ Confidence calculation works: {confidence:.3f}")
        
    except Exception as e:
        logger.error(f"✗ Invoice parser test failed: {str(e)}")
        return False
    
    return True

def test_upload_fixed():
    """Test the upload_fixed module imports."""
    logger.info("Testing Upload Fixed Module...")
    
    try:
        from upload_fixed import router, log_ocr_debug
        
        # Test that the module can be imported
        assert router is not None, "Router should be available"
        assert log_ocr_debug is not None, "Log function should be available"
        logger.info("✓ Upload fixed module imports work")
        
    except Exception as e:
        logger.error(f"✗ Upload fixed test failed: {str(e)}")
        return False
    
    return True

def test_integration():
    """Test integration between modules."""
    logger.info("Testing Module Integration...")
    
    try:
        from ocr.ocr_engine import run_ocr
        from ocr.table_extractor import extract_table_data, extract_line_items_from_text
        from ocr.parse_invoice import extract_invoice_metadata, calculate_confidence
        
        # Test that all modules can work together
        logger.info("✓ All OCR modules can be imported together")
        
        # Test the complete pipeline flow
        sample_text = """
        INVOICE #TEST123
        Date: 20/12/2023
        From: Test Company Ltd
        
        Description Qty Unit Price Total
        Item 1 2 £10.00 £20.00
        Item 2 1 £15.00 £15.00
        
        Subtotal: £35.00
        VAT: £7.00
        Total: £42.00
        """
        
        # Test metadata extraction
        metadata = extract_invoice_metadata(sample_text)
        
        # Test line item extraction
        line_items = extract_line_items_from_text(sample_text)
        
        # Test confidence calculation
        parsed_data = {
            **metadata,
            'line_items': line_items,
            'ocr_text': sample_text
        }
        confidence = calculate_confidence(parsed_data)
        
        logger.info(f"✓ Integration test passed: {len(line_items)} line items, confidence: {confidence:.3f}")
        
    except Exception as e:
        logger.error(f"✗ Integration test failed: {str(e)}")
        return False
    
    return True

def main():
    """Run all tests."""
    logger.info("Starting Enhanced OCR Pipeline Tests")
    logger.info("=" * 50)
    
    tests = [
        ("OCR Engine", test_ocr_engine),
        ("Table Extractor", test_table_extractor),
        ("Invoice Parser", test_parse_invoice),
        ("Upload Fixed", test_upload_fixed),
        ("Integration", test_integration),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\nRunning {test_name} test...")
        if test_func():
            passed += 1
            logger.info(f"✓ {test_name} test PASSED")
        else:
            logger.error(f"✗ {test_name} test FAILED")
    
    logger.info("\n" + "=" * 50)
    logger.info(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Enhanced OCR pipeline is working correctly.")
        return True
    else:
        logger.error("❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 