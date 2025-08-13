#!/usr/bin/env python3
"""
Upload Flow Diagnostic Script

This script tests the upload flow step by step to identify where the 0% OCR issue is occurring.
"""

import sys
import os
import requests
import json
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_backend_health():
    """Test if backend is responding"""
    print("🔍 Testing backend health...")
    try:
        response = requests.get("http://localhost:8001/health", timeout=10)
        if response.status_code == 200:
            print("✅ Backend health check passed")
            return True
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend health check failed: {e}")
        return False

def test_upload_endpoint():
    """Test the upload endpoint directly"""
    print("\n🔍 Testing upload endpoint...")
    try:
        response = requests.get("http://localhost:8001/api/health", timeout=10)
        if response.status_code == 200:
            print("✅ Upload endpoint health check passed")
            return True
        else:
            print(f"❌ Upload endpoint health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Upload endpoint health check failed: {e}")
        return False

def test_ocr_processing():
    """Test OCR processing directly"""
    print("\n🔍 Testing OCR processing...")
    
    # Find a test file
    test_file = Path("data/uploads/435413ea-91fa-43f7-8c24-cc1cc9dacc10_20250804_213536.pdf")
    if not test_file.exists():
        print("❌ No test file found")
        return False
    
    try:
        # Import OCR processing modules
        from backend.ocr.enhanced_ocr_engine import enhanced_ocr_engine
        from backend.upload.adaptive_processor import AdaptiveProcessor
        
        print(f"📄 Testing with file: {test_file}")
        
        # Test OCR engine directly
        print("🔄 Testing OCR engine...")
        adaptive_processor = AdaptiveProcessor()
        
        # Test document processing
        result = adaptive_processor.process_with_recovery(str(test_file))
        
        print(f"📊 Processing Results:")
        print(f"   Document Type: {result.document_type}")
        print(f"   Supplier: {result.supplier}")
        print(f"   Invoice Number: {result.invoice_number}")
        print(f"   Overall Confidence: {result.overall_confidence}")
        print(f"   Line Items Count: {len(result.line_items)}")
        print(f"   Pages Processed: {result.pages_processed}")
        print(f"   Pages Failed: {result.pages_failed}")
        print(f"   Total Processing Time: {result.total_processing_time}")
        
        if result.line_items:
            print(f"   First Line Item: {result.line_items[0]}")
        
        # Check if processing was successful based on confidence and line items
        success = result.overall_confidence > 0.1 or len(result.line_items) > 0
        print(f"   Processing Success: {success}")
        
        return success
        
    except Exception as e:
        print(f"❌ OCR processing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_file_upload():
    """Test actual file upload"""
    print("\n🔍 Testing file upload...")
    
    # Find a test file
    test_file = Path("data/uploads/435413ea-91fa-43f7-8c24-cc1cc9dacc10_20250804_213536.pdf")
    if not test_file.exists():
        print("❌ No test file found")
        return False
    
    try:
        with open(test_file, 'rb') as f:
            files = {'file': (test_file.name, f, 'application/pdf')}
            data = {
                'parse_templates': 'true',
                'save_debug': 'true'
            }
            
            response = requests.post(
                "http://localhost:8001/api/upload/test",
                files=files,
                data=data,
                timeout=60
            )
            
        if response.status_code == 200:
            result = response.json()
            print("✅ File upload successful")
            print(f"📊 Upload Results:")
            print(f"   Success: {result.get('success', False)}")
            print(f"   Message: {result.get('message', 'No message')}")
            
            if 'processing_results' in result:
                proc = result['processing_results']
                print(f"   Document Type: {proc.get('document_type', 'Unknown')}")
                print(f"   Supplier: {proc.get('supplier', 'Unknown')}")
                print(f"   Overall Confidence: {proc.get('overall_confidence', 0)}")
                print(f"   Line Items Count: {proc.get('line_items_count', 0)}")
                print(f"   Processing Time: {proc.get('processing_time', 0)}")
            
            return True
        else:
            print(f"❌ File upload failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ File upload test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all diagnostic tests"""
    print("🔬 OWLIN Upload Flow Diagnostic")
    print("=" * 50)
    
    # Test 1: Backend health
    if not test_backend_health():
        print("❌ Backend is not responding. Please start the backend server.")
        return
    
    # Test 2: Upload endpoint
    if not test_upload_endpoint():
        print("❌ Upload endpoint is not responding.")
        return
    
    # Test 3: OCR processing
    if not test_ocr_processing():
        print("❌ OCR processing is failing.")
        return
    
    # Test 4: File upload
    if not test_file_upload():
        print("❌ File upload is failing.")
        return
    
    print("\n✅ All diagnostic tests completed!")

if __name__ == "__main__":
    main() 