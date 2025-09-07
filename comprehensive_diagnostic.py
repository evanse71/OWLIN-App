#!/usr/bin/env python3
"""
Comprehensive Diagnostic for OWLIN App Upload System
"""

import requests
import json
import os
import sys
from pathlib import Path
import time

def test_backend_health():
    """Test backend health and basic functionality"""
    print("🔍 Testing Backend Health...")
    
    try:
        # Test main endpoint
        response = requests.get("http://localhost:8002/", timeout=5)
        if response.status_code == 200:
            print("✅ Main endpoint working")
        else:
            print(f"❌ Main endpoint failed: {response.status_code}")
            return False
        
        # Test health endpoint
        response = requests.get("http://localhost:8002/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health endpoint working")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Backend health test failed: {e}")
        return False

def test_frontend_health():
    """Test frontend health"""
    print("\n🔍 Testing Frontend Health...")
    
    try:
        response = requests.get("http://localhost:3000", timeout=5)
        if response.status_code == 200:
            print("✅ Frontend working")
            return True
        else:
            print(f"❌ Frontend failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Frontend health test failed: {e}")
        return False

def test_ocr_engine():
    """Test OCR engine functionality"""
    print("\n🔍 Testing OCR Engine...")
    
    try:
        # Test OCR engine import
        sys.path.append('backend')
        from ocr.unified_ocr_engine import get_unified_ocr_engine
        
        engine = get_unified_ocr_engine()
        print("✅ OCR engine loaded successfully")
        
        # Test basic functionality
        if hasattr(engine, 'process_document'):
            print("✅ OCR engine has process_document method")
        else:
            print("❌ OCR engine missing process_document method")
            return False
        
        return True
    except Exception as e:
        print(f"❌ OCR engine test failed: {e}")
        return False

def test_multi_invoice_detection():
    """Test multi-invoice detection system"""
    print("\n🔍 Testing Multi-Invoice Detection...")
    
    try:
        from ocr.multi_invoice_detector import get_multi_invoice_detector
        
        detector = get_multi_invoice_detector()
        print("✅ Multi-invoice detector loaded successfully")
        
        # Test basic detection
        test_text = "Invoice 123\nSupplier: ABC Company\nTotal: £100.00"
        result = detector.detect(test_text)
        
        if hasattr(result, 'is_multi_invoice'):
            print("✅ Multi-invoice detection working")
        else:
            print("❌ Multi-invoice detection failed")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Multi-invoice detection test failed: {e}")
        return False

def test_file_upload_simulation():
    """Test file upload simulation"""
    print("\n🔍 Testing File Upload Simulation...")
    
    try:
        # Create a test file
        test_file_path = "test_invoice.txt"
        with open(test_file_path, "w") as f:
            f.write("Invoice 123\nSupplier: Test Company\nTotal: £150.00")
        
        # Test file upload endpoint
        with open(test_file_path, "rb") as f:
            files = {"file": ("test_invoice.txt", f, "text/plain")}
            response = requests.post("http://localhost:8002/api/upload", files=files, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ File upload successful")
            
            # Check response structure
            if "success" in result and result["success"]:
                print("✅ Upload response structure correct")
            else:
                print("⚠️ Upload response structure may be incorrect")
            
            # Check confidence
            if "data" in result and "confidence" in result["data"]:
                confidence = result["data"]["confidence"]
                if confidence > 0.3:
                    print(f"✅ Confidence calculation working: {confidence:.2f}")
                else:
                    print(f"⚠️ Low confidence detected: {confidence:.2f}")
            else:
                print("⚠️ Confidence not found in response")
            
        else:
            print(f"❌ File upload failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        # Clean up
        os.remove(test_file_path)
        return True
        
    except Exception as e:
        print(f"❌ File upload test failed: {e}")
        return False

def test_database_operations():
    """Test database operations"""
    print("\n🔍 Testing Database Operations...")
    
    try:
        # Test database endpoints
        response = requests.get("http://localhost:8002/api/invoices", timeout=5)
        if response.status_code == 200:
            print("✅ Database invoices endpoint working")
        else:
            print(f"⚠️ Database invoices endpoint failed: {response.status_code}")
        
        response = requests.get("http://localhost:8002/api/files", timeout=5)
        if response.status_code == 200:
            print("✅ Database files endpoint working")
        else:
            print(f"⚠️ Database files endpoint failed: {response.status_code}")
        
        return True
    except Exception as e:
        print(f"❌ Database operations test failed: {e}")
        return False

def test_error_handling():
    """Test error handling"""
    print("\n🔍 Testing Error Handling...")
    
    try:
        # Test invalid file upload
        files = {"file": ("invalid.txt", b"invalid content", "text/plain")}
        response = requests.post("http://localhost:8002/api/upload", files=files, timeout=10)
        
        if response.status_code in [400, 500]:
            print("✅ Error handling working for invalid files")
        else:
            print(f"⚠️ Unexpected response for invalid file: {response.status_code}")
        
        return True
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

def main():
    """Run comprehensive diagnostic"""
    print("🚀 Starting Comprehensive OWLIN App Diagnostic")
    print("=" * 60)
    
    tests = [
        ("Backend Health", test_backend_health),
        ("Frontend Health", test_frontend_health),
        ("OCR Engine", test_ocr_engine),
        ("Multi-Invoice Detection", test_multi_invoice_detection),
        ("File Upload", test_file_upload_simulation),
        ("Database Operations", test_database_operations),
        ("Error Handling", test_error_handling),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📊 DIAGNOSTIC RESULTS")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 SUMMARY: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - System is ready for production!")
    elif passed >= total * 0.8:
        print("⚠️ Most tests passed - Minor issues detected")
    else:
        print("🚨 Multiple issues detected - System needs attention")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 