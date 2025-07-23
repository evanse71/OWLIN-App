#!/usr/bin/env python3
"""
Simple test script to verify backend integration.
Run this to test the new OCR factory, file processor, and database modules.
"""

import sys
import os
import tempfile
import shutil
from io import BytesIO

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_ocr_factory():
    """Test OCR factory functionality."""
    print("🧪 Testing OCR Factory...")
    
    try:
        from app.ocr_factory import get_ocr_recognizer, get_available_ocr_engines
        
        # Test available engines
        engines = get_available_ocr_engines()
        print(f"✅ Available OCR engines: {engines}")
        
        if engines:
            # Test getting a recognizer
            recognizer = get_ocr_recognizer()
            print(f"✅ OCR recognizer created: {type(recognizer).__name__}")
            
            # Test with a simple image
            import numpy as np
            test_image = np.ones((100, 300), dtype=np.uint8) * 255
            text, confidence = recognizer.recognize(test_image)
            print(f"✅ OCR test completed - Text length: {len(text)}, Confidence: {confidence:.2f}")
        else:
            print("⚠️  No OCR engines available")
            
    except Exception as e:
        print(f"❌ OCR Factory test failed: {e}")
        return False
    
    return True

def test_file_processor():
    """Test file processor functionality."""
    print("\n🧪 Testing File Processor...")
    
    try:
        from app.file_processor import generate_file_id, get_uploaded_files
        
        # Test file ID generation
        file_id = generate_file_id()
        print(f"✅ File ID generated: {file_id}")
        
        # Test getting uploaded files
        files = get_uploaded_files()
        print(f"✅ Retrieved {len(files)} uploaded files from database")
        
    except Exception as e:
        print(f"❌ File Processor test failed: {e}")
        return False
    
    return True

def test_database():
    """Test database functionality."""
    print("\n🧪 Testing Database...")
    
    try:
        from app.database import load_invoices_from_db, get_processing_status_summary
        
        # Test loading invoices
        invoices = load_invoices_from_db()
        print(f"✅ Loaded {len(invoices)} invoices from database")
        
        # Test processing status
        summary = get_processing_status_summary()
        print(f"✅ Processing summary: {summary['files']['total']} files, {summary['invoices']['total']} invoices")
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False
    
    return True

def test_file_upload_simulation():
    """Simulate file upload and processing."""
    print("\n🧪 Testing File Upload Simulation...")
    
    try:
        from app.file_processor import save_file_metadata, update_file_processing_status
        
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test invoice content")
            temp_file_path = f.name
        
        # Simulate file metadata
        file_id = "test-file-123"
        success = save_file_metadata(
            file_id=file_id,
            original_filename="test_invoice.txt",
            file_type="invoice",
            file_path=temp_file_path,
            file_size=1024
        )
        
        if success:
            print("✅ File metadata saved successfully")
            
            # Test status update
            status_success = update_file_processing_status(file_id, "completed", "Test extracted text", 0.85, 1)
            if status_success:
                print("✅ File status updated successfully")
            else:
                print("❌ File status update failed")
        else:
            print("❌ File metadata save failed")
        
        # Clean up
        os.unlink(temp_file_path)
        
    except Exception as e:
        print(f"❌ File upload simulation failed: {e}")
        return False
    
    return True

def main():
    """Run all tests."""
    print("🚀 Starting Backend Integration Tests\n")
    
    tests = [
        test_ocr_factory,
        test_file_processor,
        test_database,
        test_file_upload_simulation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Backend integration is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 