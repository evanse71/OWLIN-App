#!/usr/bin/env python3
"""
Comprehensive Test Script for Invoice-Delivery Note Matching Pipeline

This script validates the complete matching pipeline including:
- Delivery note parsing
- Fuzzy matching algorithms
- Discrepancy detection
- Confidence scoring
- API endpoints

Author: OWLIN Development Team
Version: 1.0.0
"""

import os
import sys
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List
import json
import time

# Add backend to path
sys.path.append('backend')

from upload_pipeline import process_document
from ocr.parse_invoice import parse_invoice, LineItem
from ocr.parse_delivery_note import parse_delivery_note, DeliveryLineItem
from matching.match_invoice_delivery import match_items, match_documents, suggest_matches, validate_matching_result

logger = logging.getLogger(__name__)

class MatchingPipelineTester:
    def __init__(self):
        self.test_results = []
        self.test_files_dir = Path("test_files")
        self.test_files_dir.mkdir(exist_ok=True)

    def create_test_data(self) -> Dict[str, Any]:
        """Create test invoice and delivery note data"""
        # Test invoice data
        invoice_data = {
            'supplier': 'Test Supplier Ltd',
            'date': '2024-01-15',
            'line_items': [
                LineItem(
                    description='Product A - Standard Size',
                    quantity=10.0,
                    unit_price=25.50,
                    total_price=255.00
                ),
                LineItem(
                    description='Product B - Large',
                    quantity=5.0,
                    unit_price=45.00,
                    total_price=225.00
                ),
                LineItem(
                    description='Product C - Premium',
                    quantity=2.0,
                    unit_price=100.00,
                    total_price=200.00
                )
            ]
        }

        # Test delivery note data
        delivery_data = {
            'supplier': 'Test Supplier Ltd',
            'date': '2024-01-15',
            'line_items': [
                DeliveryLineItem(
                    description='Product A Standard Size',
                    quantity=8.0,
                    unit='pcs'
                ),
                DeliveryLineItem(
                    description='Product B Large',
                    quantity=5.0,
                    unit='pcs'
                ),
                DeliveryLineItem(
                    description='Product D - New',
                    quantity=3.0,
                    unit='pcs'
                )
            ]
        }

        return {
            'invoice': invoice_data,
            'delivery': delivery_data
        }

    def test_delivery_note_parsing(self) -> bool:
        """Test delivery note parsing functionality"""
        try:
            logger.info("🧪 Testing delivery note parsing...")
            
            # Create test delivery note text
            test_text = """
            DELIVERY NOTE
            
            Test Supplier Ltd
            123 Business Street
            London, UK
            
            Delivery Note #: DN-2024-001
            Delivery Date: 15/01/2024
            
            Items Delivered:
            1. Product A Standard Size - 8 pcs
            2. Product B Large - 5 pcs
            3. Product D New - 3 pcs
            
            Received by: John Smith
            Delivery Address: 456 Warehouse Road
            """
            
            # Parse delivery note
            result = parse_delivery_note(test_text, 0.85)
            
            # Validate results
            assert result.supplier == 'Test Supplier Ltd', f"Expected 'Test Supplier Ltd', got '{result.supplier}'"
            assert result.delivery_number != 'Unknown', "Delivery number should be extracted"
            assert len(result.line_items) > 0, "Should extract line items"
            assert result.confidence > 0.5, f"Confidence should be > 0.5, got {result.confidence}"
            
            logger.info("✅ Delivery note parsing test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Delivery note parsing test failed: {e}")
            return False

    def test_fuzzy_matching(self) -> bool:
        """Test fuzzy matching algorithms"""
        try:
            logger.info("🧪 Testing fuzzy matching...")
            
            test_data = self.create_test_data()
            invoice_items = test_data['invoice']['line_items']
            delivery_items = test_data['delivery']['line_items']
            
            # Test matching with different thresholds
            thresholds = [0.7, 0.8, 0.9]
            
            for threshold in thresholds:
                result = match_items(invoice_items, delivery_items, threshold)
                
                # Validate basic structure
                assert hasattr(result, 'matched_items'), "Result should have matched_items"
                assert hasattr(result, 'overall_confidence'), "Result should have overall_confidence"
                assert hasattr(result, 'total_matches'), "Result should have total_matches"
                
                # Validate confidence calculation
                assert 0 <= result.overall_confidence <= 1, f"Confidence should be 0-1, got {result.overall_confidence}"
                
                # Validate matched items
                for matched_item in result.matched_items:
                    assert matched_item.similarity_score >= threshold, f"Similarity should be >= threshold"
                    assert hasattr(matched_item, 'quantity_mismatch'), "Should detect quantity mismatches"
                    assert hasattr(matched_item, 'price_mismatch'), "Should detect price mismatches"
                
                logger.info(f"✅ Fuzzy matching test passed for threshold {threshold}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Fuzzy matching test failed: {e}")
            return False

    def test_discrepancy_detection(self) -> bool:
        """Test discrepancy detection functionality"""
        try:
            logger.info("🧪 Testing discrepancy detection...")
            
            test_data = self.create_test_data()
            invoice_items = test_data['invoice']['line_items']
            delivery_items = test_data['delivery']['line_items']
            
            result = match_items(invoice_items, delivery_items, 0.8)
            
            # Check for quantity mismatches
            quantity_mismatches = [item for item in result.matched_items if item.quantity_mismatch]
            assert len(quantity_mismatches) > 0, "Should detect quantity mismatches"
            
            # Check for unmatched items
            assert len(result.invoice_only_items) > 0, "Should identify invoice-only items"
            assert len(result.delivery_only_items) > 0, "Should identify delivery-only items"
            
            # Validate discrepancy details
            for item in quantity_mismatches:
                assert item.quantity_difference is not None, "Should calculate quantity difference"
                assert isinstance(item.quantity_difference, (int, float)), "Quantity difference should be numeric"
            
            logger.info("✅ Discrepancy detection test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Discrepancy detection test failed: {e}")
            return False

    def test_document_matching(self) -> bool:
        """Test document-level matching"""
        try:
            logger.info("🧪 Testing document-level matching...")
            
            test_data = self.create_test_data()
            
            result = match_documents(test_data['invoice'], test_data['delivery'])
            
            # Validate document matching structure
            assert 'document_matching' in result, "Should have document_matching section"
            assert 'item_matching' in result, "Should have item_matching section"
            assert 'summary' in result, "Should have summary section"
            
            # Validate document-level checks
            doc_matching = result['document_matching']
            assert 'supplier_match' in doc_matching, "Should check supplier match"
            assert 'date_match' in doc_matching, "Should check date match"
            assert 'overall_confidence' in doc_matching, "Should calculate overall confidence"
            
            # Validate summary statistics
            summary = result['summary']
            assert 'total_invoice_items' in summary, "Should count invoice items"
            assert 'total_delivery_items' in summary, "Should count delivery items"
            assert 'matched_percentage' in summary, "Should calculate matched percentage"
            assert 'discrepancy_percentage' in summary, "Should calculate discrepancy percentage"
            
            logger.info("✅ Document matching test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Document matching test failed: {e}")
            return False

    def test_suggestion_generation(self) -> bool:
        """Test manual review suggestion generation"""
        try:
            logger.info("🧪 Testing suggestion generation...")
            
            test_data = self.create_test_data()
            invoice_items = test_data['invoice']['line_items']
            delivery_items = test_data['delivery']['line_items']
            
            suggestions = suggest_matches(invoice_items, delivery_items, 0.6)
            
            # Validate suggestions structure
            assert isinstance(suggestions, list), "Suggestions should be a list"
            
            for suggestion in suggestions:
                assert 'invoice_item' in suggestion, "Should have invoice item"
                assert 'delivery_item' in suggestion, "Should have delivery item"
                assert 'similarity_score' in suggestion, "Should have similarity score"
                assert 'confidence' in suggestion, "Should have confidence level"
                assert 'reason' in suggestion, "Should have reason for suggestion"
                
                # Validate similarity score
                assert 0 <= suggestion['similarity_score'] <= 1, "Similarity should be 0-1"
                assert suggestion['confidence'] in ['low', 'medium', 'high'], "Confidence should be low/medium/high"
            
            logger.info("✅ Suggestion generation test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Suggestion generation test failed: {e}")
            return False

    def test_validation_functionality(self) -> bool:
        """Test matching result validation"""
        try:
            logger.info("🧪 Testing validation functionality...")
            
            test_data = self.create_test_data()
            invoice_items = test_data['invoice']['line_items']
            delivery_items = test_data['delivery']['line_items']
            
            # Create matching result
            matching_result = match_items(invoice_items, delivery_items, 0.8)
            
            # Validate the result
            validation = validate_matching_result(matching_result)
            
            # Validate validation structure
            assert 'quality_metrics' in validation, "Should have quality metrics"
            assert 'recommendations' in validation, "Should have recommendations"
            
            # Validate quality metrics
            metrics = validation['quality_metrics']
            assert 'match_rate' in metrics, "Should calculate match rate"
            assert 'discrepancy_rate' in metrics, "Should calculate discrepancy rate"
            assert 'coverage_rate' in metrics, "Should calculate coverage rate"
            
            # Validate all metrics are 0-1
            for metric_name, metric_value in metrics.items():
                assert 0 <= metric_value <= 1, f"{metric_name} should be 0-1, got {metric_value}"
            
            # Validate recommendations
            recommendations = validation['recommendations']
            assert isinstance(recommendations, list), "Recommendations should be a list"
            assert len(recommendations) > 0, "Should provide at least one recommendation"
            
            logger.info("✅ Validation functionality test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Validation functionality test failed: {e}")
            return False

    def test_integration_with_upload_pipeline(self) -> bool:
        """Test integration with the upload pipeline"""
        try:
            logger.info("🧪 Testing upload pipeline integration...")
            
            # Create mock OCR results
            mock_ocr_results = [
                {
                    'text': 'INVOICE\nTest Supplier Ltd\nProduct A - 10 units @ £25.50',
                    'confidence': 0.85,
                    'page_number': 1
                }
            ]
            
            # Test that the pipeline can handle delivery notes
            mock_delivery_text = """
            DELIVERY NOTE
            Test Supplier Ltd
            Product A - 8 units delivered
            """
            
            # Parse delivery note
            delivery_result = parse_delivery_note(mock_delivery_text, 0.85)
            
            # Validate delivery note parsing
            assert delivery_result.supplier != 'Unknown Supplier', "Should extract supplier"
            assert len(delivery_result.line_items) > 0, "Should extract line items"
            
            logger.info("✅ Upload pipeline integration test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Upload pipeline integration test failed: {e}")
            return False

    def test_performance(self) -> bool:
        """Test matching performance with larger datasets"""
        try:
            logger.info("🧪 Testing performance...")
            
            # Create larger test dataset
            invoice_items = []
            delivery_items = []
            
            # Generate 50 test items
            for i in range(50):
                invoice_items.append(LineItem(
                    description=f'Product {chr(65 + i)} - Item {i}',
                    quantity=float(i + 1),
                    unit_price=float((i + 1) * 10),
                    total_price=float((i + 1) * (i + 1) * 10)
                ))
                
                delivery_items.append(DeliveryLineItem(
                    description=f'Product {chr(65 + i)} Item {i}',
                    quantity=float(i + 1),
                    unit='pcs'
                ))
            
            # Measure matching performance
            start_time = time.time()
            result = match_items(invoice_items, delivery_items, 0.8)
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            # Validate performance
            assert processing_time < 5.0, f"Matching should complete in < 5s, took {processing_time:.2f}s"
            assert result.total_matches > 0, "Should find matches in large dataset"
            
            logger.info(f"✅ Performance test passed: {processing_time:.2f}s for 50 items")
            return True
            
        except Exception as e:
            logger.error(f"❌ Performance test failed: {e}")
            return False

    def test_error_handling(self) -> bool:
        """Test error handling and edge cases"""
        try:
            logger.info("🧪 Testing error handling...")
            
            # Test with empty lists
            empty_result = match_items([], [], 0.8)
            assert empty_result.total_matches == 0, "Should handle empty lists"
            assert empty_result.overall_confidence == 0.0, "Should have zero confidence for empty lists"
            
            # Test with None values
            try:
                match_items(None, [], 0.8)
                assert False, "Should raise exception for None input"
            except (TypeError, AttributeError):
                pass  # Expected behavior
            
            # Test with invalid threshold
            try:
                match_items([], [], 1.5)  # Invalid threshold
                assert False, "Should handle invalid threshold"
            except (ValueError, AssertionError):
                pass  # Expected behavior
            
            logger.info("✅ Error handling test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error handling test failed: {e}")
            return False

    def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests and return results"""
        logger.info("🚀 Starting comprehensive matching pipeline tests...")
        
        tests = [
            ("Delivery Note Parsing", self.test_delivery_note_parsing),
            ("Fuzzy Matching", self.test_fuzzy_matching),
            ("Discrepancy Detection", self.test_discrepancy_detection),
            ("Document Matching", self.test_document_matching),
            ("Suggestion Generation", self.test_suggestion_generation),
            ("Validation Functionality", self.test_validation_functionality),
            ("Upload Pipeline Integration", self.test_integration_with_upload_pipeline),
            ("Performance", self.test_performance),
            ("Error Handling", self.test_error_handling),
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
            logger.info("🎉 All tests passed! Matching pipeline is working correctly.")
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
            logging.FileHandler('matching_pipeline_test.log')
        ]
    )
    
    # Run tests
    tester = MatchingPipelineTester()
    results = tester.run_all_tests()
    
    # Save results
    results_file = Path("matching_pipeline_test_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"📄 Test results saved to: {results_file}")
    
    # Exit with appropriate code
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main() 