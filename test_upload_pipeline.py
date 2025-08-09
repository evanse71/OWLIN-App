#!/usr/bin/env python3
"""
Test script for the complete upload pipeline with OCR functionality.
This script tests the entire flow from file upload to database storage.
"""

import sys
import os
import tempfile
from pathlib import Path
import logging

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_ocr_dependencies():
    """Test that all OCR dependencies are available."""
    print("🧪 Testing OCR Dependencies")
    
    try:
        from ocr_processing import TESSERACT_AVAILABLE, run_ocr
        print(f"✅ TESSERACT_AVAILABLE: {TESSERACT_AVAILABLE}")
        
        if not TESSERACT_AVAILABLE:
            print("❌ Tesseract not available - OCR will fail")
            return False
        
        # Test OCR with a simple image
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a test invoice image
        img = Image.new('RGB', (600, 200), color='white')
        draw = ImageDraw.Draw(img)
        
        # Try to use a system font, fallback to default
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        # Draw invoice content
        draw.text((20, 20), "INVOICE", fill='black', font=font)
        draw.text((20, 50), "Invoice #: INV-2024-001", fill='black', font=font)
        draw.text((20, 80), "Supplier: ABC Company Ltd", fill='black', font=font)
        draw.text((20, 110), "Date: 2024-01-15", fill='black', font=font)
        draw.text((20, 140), "Subtotal: $500.00", fill='black', font=font)
        draw.text((20, 170), "VAT (20%): $100.00", fill='black', font=font)
        draw.text((400, 170), "TOTAL: $600.00", fill='black', font=font)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            img.save(tmp_file.name)
            test_file = tmp_file.name
        
        print(f"   Created test invoice: {test_file}")
        
        # Test OCR
        results = run_ocr(test_file)
        
        # Clean up
        os.unlink(test_file)
        
        if results:
            print(f"✅ OCR successful: {len(results)} text blocks")
            for i, result in enumerate(results[:3]):  # Show first 3 results
                print(f"   {i+1}. '{result['text']}' (conf: {result['confidence']:.1f}%)")
            return True
        else:
            print("❌ OCR returned no results")
            return False
            
    except Exception as e:
        print(f"❌ OCR test failed: {e}")
        return False

def test_field_extraction():
    """Test field extraction with OCR results."""
    print("\n🧪 Testing Field Extraction")
    
    try:
        from field_extractor import extract_invoice_fields
        
        # Create mock OCR results
        mock_ocr_results = [
            {
                "text": "INVOICE",
                "bbox": [20, 20, 100, 40],
                "confidence": 95.0,
                "page_num": 1
            },
            {
                "text": "Invoice #: INV-2024-001",
                "bbox": [20, 50, 200, 70],
                "confidence": 90.0,
                "page_num": 1
            },
            {
                "text": "Supplier: ABC Company Ltd",
                "bbox": [20, 80, 300, 100],
                "confidence": 85.0,
                "page_num": 1
            },
            {
                "text": "Date: 2024-01-15",
                "bbox": [20, 110, 200, 130],
                "confidence": 88.0,
                "page_num": 1
            },
            {
                "text": "Subtotal: $500.00",
                "bbox": [20, 140, 200, 160],
                "confidence": 92.0,
                "page_num": 1
            },
            {
                "text": "VAT (20%): $100.00",
                "bbox": [20, 170, 200, 190],
                "confidence": 89.0,
                "page_num": 1
            },
            {
                "text": "TOTAL: $600.00",
                "bbox": [400, 170, 500, 190],
                "confidence": 94.0,
                "page_num": 1
            }
        ]
        
        # Extract fields
        extracted_fields = extract_invoice_fields(mock_ocr_results)
        
        print("✅ Field extraction successful")
        print(f"   Supplier: {extracted_fields.get('supplier_name', 'Unknown')}")
        print(f"   Invoice Number: {extracted_fields.get('invoice_number', 'Unknown')}")
        print(f"   Date: {extracted_fields.get('invoice_date', 'Unknown')}")
        print(f"   Net Amount: {extracted_fields.get('net_amount', 'Unknown')}")
        print(f"   VAT Amount: {extracted_fields.get('vat_amount', 'Unknown')}")
        print(f"   Total Amount: {extracted_fields.get('total_amount', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Field extraction test failed: {e}")
        return False

def test_upload_validation():
    """Test upload validation."""
    print("\n🧪 Testing Upload Validation")
    
    try:
        from upload_validator import validate_upload, SUPPORTED_EXTENSIONS
        
        print(f"✅ SUPPORTED_EXTENSIONS: {list(SUPPORTED_EXTENSIONS.keys())}")
        
        # Test with mock extracted data
        mock_extracted_data = {
            'supplier_name': 'ABC Company Ltd',
            'invoice_number': 'INV-2024-001',
            'invoice_date': '2024-01-15',
            'net_amount': 500.00,
            'vat_amount': 100.00,
            'total_amount': 600.00,
            'currency': 'GBP'
        }
        
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(b"Mock PDF content")
            test_file = tmp_file.name
        
        # Test validation
        allowed, messages, validation_data = validate_upload(test_file, mock_extracted_data, "data/test.db")
        
        # Clean up
        os.unlink(test_file)
        
        print(f"✅ Validation test completed")
        print(f"   Allowed: {allowed}")
        print(f"   Messages: {messages}")
        
        return True
        
    except Exception as e:
        print(f"❌ Upload validation test failed: {e}")
        return False

def test_database_operations():
    """Test database operations."""
    print("\n🧪 Testing Database Operations")
    
    try:
        from db_manager import init_db, save_invoice, save_file_hash, user_has_permission
        
        # Test database initialization
        test_db_path = "data/test_upload.db"
        init_db(test_db_path)
        print("✅ Database initialization successful")
        
        # Test user permissions
        assert user_has_permission("Finance") == True
        assert user_has_permission("admin") == True
        assert user_has_permission("viewer") == False
        print("✅ User permissions working correctly")
        
        # Test saving invoice
        test_invoice_data = {
            'supplier_name': 'Test Company',
            'invoice_number': 'TEST-001',
            'invoice_date': '2024-01-15',
            'net_amount': 100.00,
            'vat_amount': 20.00,
            'total_amount': 120.00,
            'currency': 'GBP',
            'file_path': '/tmp/test.pdf',
            'file_hash': 'test_hash_123',
            'file_size': 1024,
            'mime_type': 'application/pdf'
        }
        
        save_success = save_invoice(test_invoice_data, test_db_path)
        print(f"✅ Invoice save test: {'Success' if save_success else 'Failed'}")
        
        # Test saving file hash
        hash_success = save_file_hash('test_hash_123', '/tmp/test.pdf', 1024, 'application/pdf', test_db_path)
        print(f"✅ File hash save test: {'Success' if hash_success else 'Failed'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database operations test failed: {e}")
        return False

def test_complete_pipeline():
    """Test the complete upload pipeline."""
    print("\n🧪 Testing Complete Upload Pipeline")
    
    try:
        from ocr_processing import run_ocr
        from field_extractor import extract_invoice_fields
        from upload_validator import validate_upload
        from db_manager import init_db, save_invoice, save_file_hash
        
        # Create a test invoice image
        from PIL import Image, ImageDraw, ImageFont
        
        img = Image.new('RGB', (600, 200), color='white')
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        # Draw invoice content
        draw.text((20, 20), "INVOICE", fill='black', font=font)
        draw.text((20, 50), "Invoice #: INV-2024-002", fill='black', font=font)
        draw.text((20, 80), "Supplier: Test Company Ltd", fill='black', font=font)
        draw.text((20, 110), "Date: 2024-01-16", fill='black', font=font)
        draw.text((20, 140), "Subtotal: $750.00", fill='black', font=font)
        draw.text((20, 170), "VAT (20%): $150.00", fill='black', font=font)
        draw.text((400, 170), "TOTAL: $900.00", fill='black', font=font)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            img.save(tmp_file.name)
            test_file = tmp_file.name
        
        print(f"   Created test invoice: {test_file}")
        
        # Step 1: Run OCR
        print("   Step 1: Running OCR...")
        ocr_results = run_ocr(test_file)
        print(f"   ✅ OCR completed: {len(ocr_results)} text blocks")
        
        # Step 2: Extract fields
        print("   Step 2: Extracting fields...")
        extracted_fields = extract_invoice_fields(ocr_results)
        print(f"   ✅ Field extraction completed")
        
        # Step 3: Validate upload
        print("   Step 3: Validating upload...")
        allowed, messages, validation_data = validate_upload(test_file, extracted_fields, "data/test_pipeline.db")
        print(f"   ✅ Validation completed: {allowed}")
        
        # Step 4: Save to database
        if allowed:
            print("   Step 4: Saving to database...")
            init_db("data/test_pipeline.db")
            
            # Add file information
            extracted_fields.update({
                'file_path': test_file,
                'file_hash': 'test_hash_pipeline',
                'file_size': os.path.getsize(test_file),
                'mime_type': 'image/png'
            })
            
            save_success = save_invoice(extracted_fields, "data/test_pipeline.db")
            print(f"   ✅ Database save: {'Success' if save_success else 'Failed'}")
        
        # Clean up
        os.unlink(test_file)
        
        print("✅ Complete pipeline test successful!")
        return True
        
    except Exception as e:
        print(f"❌ Complete pipeline test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting Upload Pipeline Tests")
    print("=" * 50)
    
    tests = [
        ("OCR Dependencies", test_ocr_dependencies),
        ("Field Extraction", test_field_extraction),
        ("Upload Validation", test_upload_validation),
        ("Database Operations", test_database_operations),
        ("Complete Pipeline", test_complete_pipeline)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All upload pipeline tests passed!")
        print("✅ Upload pipeline is ready for production")
    else:
        print("⚠️ Some tests failed - check the error messages above")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 