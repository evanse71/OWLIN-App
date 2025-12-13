#!/usr/bin/env python3
"""
Test Script for Upload Validator Integration

This script validates the integration of the upload validator with the existing
OWLIN pipeline and tests the upload validation capabilities.

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
import hashlib

# Add backend to path
sys.path.append('backend')

from upload_validator import (
    validate_upload, get_validation_summary, create_upload_metadata,
    is_supported_file, validate_file_size, check_duplicate_invoice,
    check_duplicate_file_hash, generate_temp_invoice_name,
    SUPPORTED_EXTENSIONS, DEFAULT_DB_PATH
)
from upload_pipeline import process_document

logger = logging.getLogger(__name__)

class UploadValidatorTester:
    def __init__(self):
        self.test_results = []
        self.test_files_dir = Path("test_files")
        self.test_files_dir.mkdir(exist_ok=True)
        self.db_path = "data/owlin.db"

    def create_test_file(self, content: str, extension: str = ".txt") -> str:
        """Create a test file with given content"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=extension)
        temp_file.write(content.encode('utf-8'))
        temp_file.close()
        return temp_file.name

    def create_test_pdf(self) -> str:
        """Create a simple test PDF file"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            temp_file.close()
            
            c = canvas.Canvas(temp_file.name, pagesize=letter)
            c.drawString(100, 750, "Test Invoice")
            c.drawString(100, 700, "Supplier: Test Company Ltd")
            c.drawString(100, 650, "Invoice No: INV-2024-001")
            c.drawString(100, 600, "Date: 15/01/2024")
            c.drawString(100, 550, "Total: £100.00")
            c.save()
            
            return temp_file.name
        except ImportError:
            # Fallback to text file if reportlab not available
            return self.create_test_file("Test Invoice\nSupplier: Test Company Ltd\nInvoice No: INV-2024-001\nDate: 15/01/2024\nTotal: £100.00", ".txt")

    def test_file_type_validation(self) -> bool:
        """Test file type validation functionality"""
        try:
            logger.info("🧪 Testing file type validation...")
            
            # Test supported formats
            for ext in SUPPORTED_EXTENSIONS:
                test_file = self.create_test_file("test content", ext)
                try:
                    assert is_supported_file(test_file), f"Supported file {ext} should be valid"
                    logger.info(f"✅ Supported format validated: {ext}")
                finally:
                    os.unlink(test_file)
            
            # Test unsupported formats
            unsupported_files = ["test.xyz", "test.doc", "test.exe"]
            for filename in unsupported_files:
                assert not is_supported_file(filename), f"Unsupported file {filename} should be invalid"
                logger.info(f"✅ Unsupported format rejected: {filename}")
            
            logger.info("✅ File type validation test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ File type validation test failed: {e}")
            return False

    def test_file_size_validation(self) -> bool:
        """Test file size validation functionality"""
        try:
            logger.info("🧪 Testing file size validation...")
            
            # Create a small test file
            small_file = self.create_test_file("small content")
            try:
                valid, error = validate_file_size(small_file, max_size_mb=50)
                assert valid, f"Small file should be valid: {error}"
                logger.info("✅ Small file validation passed")
            finally:
                os.unlink(small_file)
            
            # Test with custom size limit
            small_file = self.create_test_file("content")
            try:
                valid, error = validate_file_size(small_file, max_size_mb=0.001)  # 1KB limit
                assert not valid, "File should be too large for 1KB limit"
                assert "exceeds maximum" in error, "Error message should mention size limit"
                logger.info("✅ File size limit validation passed")
            finally:
                os.unlink(small_file)
            
            logger.info("✅ File size validation test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ File size validation test failed: {e}")
            return False

    def test_duplicate_invoice_check(self) -> bool:
        """Test duplicate invoice checking functionality"""
        try:
            logger.info("🧪 Testing duplicate invoice checking...")
            
            # Test with non-existent database (should return False)
            result = check_duplicate_invoice("INV-2024-001", "non_existent.db")
            assert not result, "Non-existent database should return False"
            logger.info("✅ Non-existent database handled correctly")
            
            # Test with None/empty invoice number
            result = check_duplicate_invoice(None, self.db_path)
            assert not result, "None invoice number should return False"
            
            result = check_duplicate_invoice("", self.db_path)
            assert not result, "Empty invoice number should return False"
            
            result = check_duplicate_invoice("   ", self.db_path)
            assert not result, "Whitespace invoice number should return False"
            
            logger.info("✅ Duplicate invoice checking test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Duplicate invoice checking test failed: {e}")
            return False

    def test_duplicate_file_hash_check(self) -> bool:
        """Test duplicate file hash checking functionality"""
        try:
            logger.info("🧪 Testing duplicate file hash checking...")
            
            # Create test files
            file1 = self.create_test_file("identical content")
            file2 = self.create_test_file("identical content")
            file3 = self.create_test_file("different content")
            
            try:
                # Test with non-existent database
                duplicate1, hash1 = check_duplicate_file_hash(file1, "non_existent.db")
                assert not duplicate1, "Non-existent database should return False"
                assert hash1 is not None, "Hash should be calculated even if database doesn't exist"
                
                # Test that identical files have same hash
                duplicate2, hash2 = check_duplicate_file_hash(file2, "non_existent.db")
                assert hash1 == hash2, "Identical files should have same hash"
                
                # Test that different files have different hashes
                duplicate3, hash3 = check_duplicate_file_hash(file3, "non_existent.db")
                assert hash1 != hash3, "Different files should have different hashes"
                
                logger.info("✅ Duplicate file hash checking test passed")
                return True
                
            finally:
                os.unlink(file1)
                os.unlink(file2)
                os.unlink(file3)
                
        except Exception as e:
            logger.error(f"❌ Duplicate file hash checking test failed: {e}")
            return False

    def test_name_generation(self) -> bool:
        """Test descriptive name generation functionality"""
        try:
            logger.info("🧪 Testing name generation...")
            
            # Test with all parameters
            name1 = generate_temp_invoice_name("ACME Corp", "2024-01-15", "INV-001")
            assert "ACME Corp" in name1, "Supplier should be in name"
            assert "2024-01-15" in name1, "Date should be in name"
            logger.info(f"✅ Full name generation: {name1}")
            
            # Test with missing parameters
            name2 = generate_temp_invoice_name("ACME Corp", None, None)
            assert "ACME Corp" in name2, "Supplier should be in name"
            assert "Invoice" in name2, "Should include 'Invoice'"
            logger.info(f"✅ Partial name generation: {name2}")
            
            # Test with invoice number when date is missing
            name3 = generate_temp_invoice_name("ACME Corp", None, "INV-001")
            assert "INV-001" in name3, "Invoice number should be in name"
            logger.info(f"✅ Name with invoice number: {name3}")
            
            # Test with all None values
            name4 = generate_temp_invoice_name(None, None, None)
            assert name4 == "Invoice", "Should return 'Invoice' for all None values"
            logger.info(f"✅ Default name generation: {name4}")
            
            # Test with "Unknown" values
            name5 = generate_temp_invoice_name("Unknown", "Unknown", "Unknown")
            assert name5 == "Invoice", "Should return 'Invoice' for 'Unknown' values"
            logger.info(f"✅ Unknown values handled: {name5}")
            
            logger.info("✅ Name generation test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Name generation test failed: {e}")
            return False

    def test_validation_summary(self) -> bool:
        """Test validation summary generation"""
        try:
            logger.info("🧪 Testing validation summary generation...")
            
            # Create mock validation data
            validation_data = {
                "file_name": "test_invoice.pdf",
                "file_size": 1024 * 1024,  # 1MB
                "mime_type": "application/pdf",
                "extracted_data": {
                    "supplier_name": "ACME Corp",
                    "invoice_number": "INV-2024-001",
                    "invoice_date": "2024-01-15"
                },
                "duplicate_invoice": False,
                "duplicate_file": False,
                "suggested_name": "Invoice – ACME Corp – 2024-01-15"
            }
            
            summary = get_validation_summary(validation_data)
            
            # Validate summary structure
            assert "file_info" in summary, "Summary should have file_info"
            assert "extracted_info" in summary, "Summary should have extracted_info"
            assert "validation_results" in summary, "Summary should have validation_results"
            
            # Validate file info
            file_info = summary["file_info"]
            assert file_info["name"] == "test_invoice.pdf", "File name should match"
            assert file_info["size_mb"] == 1.0, "File size should be 1MB"
            assert file_info["mime_type"] == "application/pdf", "MIME type should match"
            
            # Validate extracted info
            extracted_info = summary["extracted_info"]
            assert extracted_info["supplier"] == "ACME Corp", "Supplier should match"
            assert extracted_info["invoice_number"] == "INV-2024-001", "Invoice number should match"
            assert extracted_info["date"] == "2024-01-15", "Date should match"
            
            # Validate validation results
            validation_results = summary["validation_results"]
            assert validation_results["duplicate_invoice"] == False, "Duplicate invoice should be False"
            assert validation_results["duplicate_file"] == False, "Duplicate file should be False"
            assert "ACME Corp" in validation_results["suggested_name"], "Suggested name should contain supplier"
            
            logger.info("✅ Validation summary test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Validation summary test failed: {e}")
            return False

    def test_upload_metadata_creation(self) -> bool:
        """Test upload metadata creation"""
        try:
            logger.info("🧪 Testing upload metadata creation...")
            
            # Create mock validation data
            validation_data = {
                "file_name": "test_invoice.pdf",
                "file_size": 1024 * 1024,
                "mime_type": "application/pdf",
                "file_hash": "abc123def456",
                "extracted_data": {
                    "supplier_name": "ACME Corp",
                    "invoice_number": "INV-2024-001",
                    "invoice_date": "2024-01-15"
                },
                "suggested_name": "Invoice – ACME Corp – 2024-01-15"
            }
            
            metadata = create_upload_metadata(validation_data)
            
            # Validate metadata structure
            expected_keys = [
                "original_filename", "file_size", "mime_type", "file_hash",
                "upload_timestamp", "extracted_supplier", "extracted_invoice_number",
                "extracted_date", "suggested_name", "validation_status"
            ]
            
            for key in expected_keys:
                assert key in metadata, f"Metadata should have key: {key}"
            
            # Validate metadata values
            assert metadata["original_filename"] == "test_invoice.pdf", "Original filename should match"
            assert metadata["file_size"] == 1024 * 1024, "File size should match"
            assert metadata["mime_type"] == "application/pdf", "MIME type should match"
            assert metadata["file_hash"] == "abc123def456", "File hash should match"
            assert metadata["extracted_supplier"] == "ACME Corp", "Extracted supplier should match"
            assert metadata["extracted_invoice_number"] == "INV-2024-001", "Extracted invoice number should match"
            assert metadata["extracted_date"] == "2024-01-15", "Extracted date should match"
            assert metadata["suggested_name"] == "Invoice – ACME Corp – 2024-01-15", "Suggested name should match"
            assert metadata["validation_status"] == "validated", "Validation status should be 'validated'"
            
            logger.info("✅ Upload metadata creation test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Upload metadata creation test failed: {e}")
            return False

    def test_integration_with_upload_pipeline(self) -> bool:
        """Test integration with upload pipeline"""
        try:
            logger.info("🧪 Testing integration with upload pipeline...")
            
            # Create test PDF
            test_pdf = self.create_test_pdf()
            
            try:
                # Process document with validation enabled
                result = process_document(
                    test_pdf,
                    parse_templates=True,
                    save_debug=False,
                    validate_upload=True,
                    db_path=self.db_path
                )
                
                # Check that validation results are included
                assert "upload_validation" in result, "Result should include upload_validation"
                
                validation = result["upload_validation"]
                assert "allowed" in validation, "Validation should have 'allowed' field"
                assert "messages" in validation, "Validation should have 'messages' field"
                assert "validation_data" in validation, "Validation should have 'validation_data' field"
                assert "summary" in validation, "Validation should have 'summary' field"
                assert "metadata" in validation, "Validation should have 'metadata' field"
                
                # Check that processing results are included
                assert "ocr_results" in result, "Result should include OCR results"
                assert "confidence_scores" in result, "Result should include confidence scores"
                assert "document_type" in result, "Result should include document type"
                
                logger.info(f"✅ Integration test passed - Document type: {result['document_type']}")
                logger.info(f"✅ Validation allowed: {validation['allowed']}")
                logger.info(f"✅ Processing time: {result['processing_time']:.2f}s")
                
                return True
                
            finally:
                os.unlink(test_pdf)
                
        except Exception as e:
            logger.error(f"❌ Integration test failed: {e}")
            return False

    def test_comprehensive_validation(self) -> bool:
        """Test comprehensive validation workflow"""
        try:
            logger.info("🧪 Testing comprehensive validation workflow...")
            
            # Create test file
            test_file = self.create_test_file("Test invoice content", ".pdf")
            
            try:
                # Mock extracted data
                extracted_data = {
                    "supplier_name": "ACME Corporation Ltd",
                    "invoice_number": "INV-2024-001",
                    "invoice_date": "2024-01-15"
                }
                
                # Run comprehensive validation
                allowed, messages, validation_data = validate_upload(
                    test_file, extracted_data, self.db_path, max_file_size_mb=50
                )
                
                # Validate response structure
                assert isinstance(allowed, bool), "Allowed should be boolean"
                assert isinstance(messages, dict), "Messages should be dictionary"
                assert isinstance(validation_data, dict), "Validation data should be dictionary"
                
                # Check that file format validation worked
                assert "mime_type" in validation_data, "Should have MIME type"
                assert validation_data["mime_type"] == "application/pdf", "Should be PDF MIME type"
                
                # Check that file size validation worked
                assert "file_size" in validation_data, "Should have file size"
                assert validation_data["file_size"] > 0, "File size should be positive"
                
                # Check that name generation worked
                assert "suggested_name" in validation_data, "Should have suggested name"
                assert "ACME Corporation Ltd" in validation_data["suggested_name"], "Name should contain supplier"
                
                # Check that duplicate checks were performed
                assert "duplicate_invoice" in validation_data, "Should have duplicate invoice check"
                assert "duplicate_file" in validation_data, "Should have duplicate file check"
                
                # Check messages
                if allowed:
                    assert "name" in messages, "Should have name message when allowed"
                else:
                    assert "error" in messages, "Should have error message when not allowed"
                
                logger.info(f"✅ Comprehensive validation passed - Allowed: {allowed}")
                logger.info(f"✅ Messages: {messages}")
                
                return True
                
            finally:
                os.unlink(test_file)
                
        except Exception as e:
            logger.error(f"❌ Comprehensive validation test failed: {e}")
            return False

    def run_all_tests(self) -> Dict[str, bool]:
        """Run all upload validator tests"""
        logger.info("🚀 Starting upload validator integration tests...")
        
        tests = [
            ("File Type Validation", self.test_file_type_validation),
            ("File Size Validation", self.test_file_size_validation),
            ("Duplicate Invoice Check", self.test_duplicate_invoice_check),
            ("Duplicate File Hash Check", self.test_duplicate_file_hash_check),
            ("Name Generation", self.test_name_generation),
            ("Validation Summary", self.test_validation_summary),
            ("Upload Metadata Creation", self.test_upload_metadata_creation),
            ("Integration with Upload Pipeline", self.test_integration_with_upload_pipeline),
            ("Comprehensive Validation", self.test_comprehensive_validation),
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
            logger.info("🎉 All upload validator tests passed! Integration is working correctly.")
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
            logging.FileHandler('upload_validator_test.log')
        ]
    )
    
    # Run tests
    tester = UploadValidatorTester()
    results = tester.run_all_tests()
    
    # Save results
    results_file = Path("upload_validator_test_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"📄 Test results saved to: {results_file}")
    
    # Exit with appropriate code
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main() 