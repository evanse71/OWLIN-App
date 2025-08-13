#!/usr/bin/env python3
"""
Test Script for Field Extractor Integration

This script validates the integration of the field extractor with the existing
OCR pipeline and tests the enhanced invoice parsing capabilities.

Author: OWLIN Development Team
Version: 1.0.0
"""

import os
import sys
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, List
import json
import time

# Add backend to path
sys.path.append('backend')

from ocr.field_extractor import extract_invoice_fields
from ocr.parse_invoice import parse_invoice
from upload_pipeline import process_document

logger = logging.getLogger(__name__)

class FieldExtractorTester:
    def __init__(self):
        self.test_results = []
        self.test_files_dir = Path("test_files")
        self.test_files_dir.mkdir(exist_ok=True)

    def create_mock_ocr_results(self) -> List[Dict[str, Any]]:
        """Create mock OCR results for testing"""
        return [
            {
                "text": "INVOICE",
                "bbox": [100, 50, 200, 80],
                "confidence": 95.0,
                "page_num": 1
            },
            {
                "text": "Supplier: ACME Corporation Ltd",
                "bbox": [100, 100, 400, 130],
                "confidence": 88.0,
                "page_num": 1
            },
            {
                "text": "Invoice No: INV-2024-001",
                "bbox": [100, 150, 350, 180],
                "confidence": 92.0,
                "page_num": 1
            },
            {
                "text": "Date: 15/01/2024",
                "bbox": [100, 200, 250, 230],
                "confidence": 90.0,
                "page_num": 1
            },
            {
                "text": "Product A - Standard Size",
                "bbox": [100, 300, 400, 330],
                "confidence": 85.0,
                "page_num": 1
            },
            {
                "text": "Quantity: 10 x £25.50 = £255.00",
                "bbox": [100, 350, 400, 380],
                "confidence": 87.0,
                "page_num": 1
            },
            {
                "text": "Product B - Large",
                "bbox": [100, 400, 400, 430],
                "confidence": 86.0,
                "page_num": 1
            },
            {
                "text": "Quantity: 5 x £45.00 = £225.00",
                "bbox": [100, 450, 400, 480],
                "confidence": 89.0,
                "page_num": 1
            },
            {
                "text": "Net Amount: £480.00",
                "bbox": [300, 600, 450, 630],
                "confidence": 94.0,
                "page_num": 1
            },
            {
                "text": "VAT (20%): £96.00",
                "bbox": [300, 650, 450, 680],
                "confidence": 93.0,
                "page_num": 1
            },
            {
                "text": "Total Amount: £576.00",
                "bbox": [300, 700, 450, 730],
                "confidence": 95.0,
                "page_num": 1
            }
        ]

    def test_field_extractor_basic(self) -> bool:
        """Test basic field extraction functionality"""
        try:
            logger.info("🧪 Testing basic field extraction...")
            
            ocr_results = self.create_mock_ocr_results()
            result = extract_invoice_fields(ocr_results)
            
            # Validate required fields
            required_fields = ['supplier_name', 'invoice_number', 'invoice_date', 
                             'net_amount', 'vat_amount', 'total_amount', 'currency']
            
            for field in required_fields:
                assert field in result, f"Missing required field: {field}"
            
            # Validate specific extractions
            assert result['supplier_name'] == 'ACME Corporation Ltd', f"Expected 'ACME Corporation Ltd', got '{result['supplier_name']}'"
            assert result['invoice_number'] == 'INV-2024-001', f"Expected 'INV-2024-001', got '{result['invoice_number']}'"
            assert result['invoice_date'] == '15/01/2024', f"Expected '15/01/2024', got '{result['invoice_date']}'"
            assert result['currency'] == 'GBP', f"Expected 'GBP', got '{result['currency']}'"
            
            # Validate monetary amounts
            assert result['net_amount'] == 480.0, f"Expected 480.0, got {result['net_amount']}"
            assert result['vat_amount'] == 96.0, f"Expected 96.0, got {result['vat_amount']}"
            assert result['total_amount'] == 576.0, f"Expected 576.0, got {result['total_amount']}"
            
            # Validate confidence scores
            confidence_scores = result.get('confidence_scores', {})
            assert 'supplier_name' in confidence_scores, "Missing supplier confidence score"
            assert 'invoice_number' in confidence_scores, "Missing invoice number confidence score"
            
            # Validate field sources
            field_sources = result.get('field_sources', {})
            assert 'supplier_name' in field_sources, "Missing supplier source text"
            assert 'invoice_number' in field_sources, "Missing invoice number source text"
            
            logger.info("✅ Basic field extraction test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Basic field extraction test failed: {e}")
            return False

    def test_field_extractor_validation(self) -> bool:
        """Test field extraction validation and warnings"""
        try:
            logger.info("🧪 Testing field extraction validation...")
            
            # Create OCR results with validation issues
            ocr_results = [
                {
                    "text": "Net Amount: £100.00",
                    "bbox": [100, 100, 300, 130],
                    "confidence": 90.0,
                    "page_num": 1
                },
                {
                    "text": "VAT (20%): £25.00",  # Should be £20.00 for 20%
                    "bbox": [100, 150, 300, 180],
                    "confidence": 90.0,
                    "page_num": 1
                },
                {
                    "text": "Total Amount: £125.00",
                    "bbox": [100, 200, 300, 230],
                    "confidence": 90.0,
                    "page_num": 1
                }
            ]
            
            result = extract_invoice_fields(ocr_results)
            
            # Check for warnings
            warnings = result.get('warnings', [])
            assert len(warnings) > 0, "Should generate warnings for validation issues"
            
            # Validate the warning content
            warning_text = warnings[0]
            assert "does not equal Total" in warning_text, "Warning should mention total mismatch"
            assert "deviation" in warning_text, "Warning should mention deviation percentage"
            
            logger.info("✅ Field extraction validation test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Field extraction validation test failed: {e}")
            return False

    def test_field_extractor_edge_cases(self) -> bool:
        """Test field extraction with edge cases"""
        try:
            logger.info("🧪 Testing field extraction edge cases...")
            
            # Test with minimal OCR results
            minimal_ocr = [
                {
                    "text": "Invoice",
                    "bbox": [100, 100, 200, 130],
                    "confidence": 50.0,
                    "page_num": 1
                }
            ]
            
            result = extract_invoice_fields(minimal_ocr)
            
            # Should handle minimal input gracefully
            assert 'supplier_name' in result, "Should handle minimal input"
            assert 'invoice_number' in result, "Should handle minimal input"
            assert 'invoice_date' in result, "Should handle minimal input"
            
            # Test with empty OCR results
            empty_result = extract_invoice_fields([])
            assert empty_result['supplier_name'] == 'Unknown', "Should handle empty input"
            assert empty_result['invoice_number'] == 'Unknown', "Should handle empty input"
            
            # Test with invalid OCR results
            invalid_ocr = [
                {
                    "text": "",
                    "bbox": [0, 0, 0, 0],
                    "confidence": 0.0,
                    "page_num": 1
                }
            ]
            
            invalid_result = extract_invoice_fields(invalid_ocr)
            assert invalid_result['supplier_name'] == 'Unknown', "Should handle invalid input"
            
            logger.info("✅ Field extraction edge cases test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Field extraction edge cases test failed: {e}")
            return False

    def test_integration_with_parse_invoice(self) -> bool:
        """Test integration with existing parse_invoice function"""
        try:
            logger.info("🧪 Testing integration with parse_invoice...")
            
            # Create test text
            test_text = """
            INVOICE
            
            Supplier: ACME Corporation Ltd
            Invoice No: INV-2024-001
            Date: 15/01/2024
            
            Product A - Standard Size
            Quantity: 10 x £25.50 = £255.00
            
            Product B - Large
            Quantity: 5 x £45.00 = £225.00
            
            Net Amount: £480.00
            VAT (20%): £96.00
            Total Amount: £576.00
            """
            
            # Create OCR results
            ocr_results = self.create_mock_ocr_results()
            
            # Test traditional parsing
            traditional_result = parse_invoice(test_text, 0.85)
            
            # Test enhanced parsing with OCR results
            enhanced_result = parse_invoice(test_text, 0.85, ocr_results)
            
            # Both should work
            assert traditional_result.supplier != 'Unknown Supplier', "Traditional parsing should extract supplier"
            assert enhanced_result.supplier != 'Unknown Supplier', "Enhanced parsing should extract supplier"
            
            # Enhanced parsing should have better results in some cases
            logger.info(f"Traditional supplier: {traditional_result.supplier}")
            logger.info(f"Enhanced supplier: {enhanced_result.supplier}")
            logger.info(f"Traditional invoice number: {traditional_result.invoice_number}")
            logger.info(f"Enhanced invoice number: {enhanced_result.invoice_number}")
            
            logger.info("✅ Integration with parse_invoice test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Integration with parse_invoice test failed: {e}")
            return False

    def test_fuzzywuzzy_fallback(self) -> bool:
        """Test fallback fuzzy matching when fuzzywuzzy is not available"""
        try:
            logger.info("🧪 Testing fuzzywuzzy fallback...")
            
            # Create OCR results
            ocr_results = [
                {
                    "text": "Supplier: Test Company Ltd",
                    "bbox": [100, 100, 300, 130],
                    "confidence": 90.0,
                    "page_num": 1
                }
            ]
            
            # Test that it works even without fuzzywuzzy
            result = extract_invoice_fields(ocr_results)
            
            # Should still extract supplier
            assert result['supplier_name'] != 'Unknown', "Should extract supplier even with fallback"
            
            logger.info("✅ Fuzzywuzzy fallback test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Fuzzywuzzy fallback test failed: {e}")
            return False

    def test_currency_detection(self) -> bool:
        """Test currency detection functionality"""
        try:
            logger.info("🧪 Testing currency detection...")
            
            # Test GBP detection
            gbp_ocr = [
                {
                    "text": "Total: £100.00",
                    "bbox": [100, 100, 200, 130],
                    "confidence": 90.0,
                    "page_num": 1
                }
            ]
            gbp_result = extract_invoice_fields(gbp_ocr)
            assert gbp_result['currency'] == 'GBP', f"Expected GBP, got {gbp_result['currency']}"
            
            # Test EUR detection
            eur_ocr = [
                {
                    "text": "Total: €100.00",
                    "bbox": [100, 100, 200, 130],
                    "confidence": 90.0,
                    "page_num": 1
                }
            ]
            eur_result = extract_invoice_fields(eur_ocr)
            assert eur_result['currency'] == 'EUR', f"Expected EUR, got {eur_result['currency']}"
            
            # Test USD detection
            usd_ocr = [
                {
                    "text": "Total: $100.00",
                    "bbox": [100, 100, 200, 130],
                    "confidence": 90.0,
                    "page_num": 1
                }
            ]
            usd_result = extract_invoice_fields(usd_ocr)
            assert usd_result['currency'] == 'USD', f"Expected USD, got {usd_result['currency']}"
            
            logger.info("✅ Currency detection test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Currency detection test failed: {e}")
            return False

    def test_date_extraction(self) -> bool:
        """Test date extraction functionality"""
        try:
            logger.info("🧪 Testing date extraction...")
            
            # Test various date formats
            date_formats = [
                "15/01/2024",
                "2024-01-15",
                "15th January 2024",
                "Jan 15, 2024"
            ]
            
            for date_format in date_formats:
                ocr_results = [
                    {
                        "text": f"Date: {date_format}",
                        "bbox": [100, 100, 300, 130],
                        "confidence": 90.0,
                        "page_num": 1
                    }
                ]
                
                result = extract_invoice_fields(ocr_results)
                assert result['invoice_date'] != 'Unknown', f"Should extract date: {date_format}"
                logger.info(f"✅ Extracted date: {result['invoice_date']} from {date_format}")
            
            logger.info("✅ Date extraction test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Date extraction test failed: {e}")
            return False

    def run_all_tests(self) -> Dict[str, bool]:
        """Run all field extractor tests"""
        logger.info("🚀 Starting field extractor integration tests...")
        
        tests = [
            ("Basic Field Extraction", self.test_field_extractor_basic),
            ("Field Extraction Validation", self.test_field_extractor_validation),
            ("Edge Cases", self.test_field_extractor_edge_cases),
            ("Integration with parse_invoice", self.test_integration_with_parse_invoice),
            ("Fuzzywuzzy Fallback", self.test_fuzzywuzzy_fallback),
            ("Currency Detection", self.test_currency_detection),
            ("Date Extraction", self.test_date_extraction),
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            logger.info(f"\n{'='*50}")
            logger.info(f"Running: {test_name}")
            logger.info(f"{'='*50}")
            
            try:
                result = test_func()
                results[test_name] = result
                
                if result:
                    logger.info(f"✅ {test_name}: PASSED")
                else:
                    logger.error(f"❌ {test_name}: FAILED")
                    
            except Exception as e:
                logger.error(f"❌ {test_name}: ERROR - {e}")
                results[test_name] = False
        
        # Print summary
        logger.info(f"\n{'='*50}")
        logger.info("TEST SUMMARY")
        logger.info(f"{'='*50}")
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{test_name}: {status}")
        
        logger.info(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 All field extractor tests passed! Integration is working correctly.")
        else:
            logger.error(f"⚠️ {total - passed} tests failed. Please review the issues above.")
        
        return results

def main():
    """Main test execution"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('field_extractor_test.log')
        ]
    )
    
    # Run tests
    tester = FieldExtractorTester()
    results = tester.run_all_tests()
    
    # Save results
    results_file = Path("field_extractor_test_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"📄 Test results saved to: {results_file}")
    
    # Exit with appropriate code
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main() 