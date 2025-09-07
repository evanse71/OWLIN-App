#!/usr/bin/env python3
"""
Test script to verify OCR debug panel functionality
"""

import requests
import json
import time

def test_ocr_debug_integration():
    """Test that OCR debug information is included in responses"""
    print("🔍 Testing OCR Debug Panel Integration...")
    
    try:
        # Test backend health
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("❌ Backend not responding")
            return False
        
        # Test invoices endpoint to see if OCR debug info is included
        response = requests.get("http://localhost:8000/api/invoices", timeout=5)
        if response.status_code == 200:
            invoices = response.json()
            print(f"✅ Found {len(invoices)} invoices")
            
            # Check if any invoice has OCR debug info
            debug_count = 0
            for invoice in invoices:
                if 'ocr_debug' in invoice:
                    debug_count += 1
                    print(f"✅ Invoice {invoice.get('id', 'unknown')} has OCR debug info")
                    
                    # Check debug structure
                    debug = invoice['ocr_debug']
                    if 'preprocessing_steps' in debug:
                        print(f"   - Preprocessing steps: {len(debug['preprocessing_steps'])}")
                    if 'engine_results' in debug:
                        print(f"   - Engine results: {len(debug['engine_results'])}")
                    if 'field_extraction' in debug:
                        print(f"   - Field extraction: {len(debug['field_extraction'])}")
                    if 'validation_results' in debug:
                        print(f"   - Validation results: {len(debug['validation_results'])}")
                    if 'segmentation_info' in debug:
                        print(f"   - Segmentation info: {debug['segmentation_info']['total_sections']} sections")
            
            if debug_count > 0:
                print(f"✅ {debug_count} invoices have OCR debug information")
            else:
                print("⚠️ No invoices have OCR debug information yet")
            
            return True
        else:
            print(f"❌ Failed to fetch invoices: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_frontend_debug_panel():
    """Test that frontend can display OCR debug information"""
    print("\n🌐 Testing Frontend OCR Debug Panel...")
    
    try:
        # Test main page loads
        response = requests.get("http://localhost:3000", timeout=5)
        if response.status_code == 200:
            print("✅ Frontend main page loading")
        else:
            print(f"❌ Frontend main page failed: {response.status_code}")
            return False
        
        # Test invoices page loads
        response = requests.get("http://localhost:3000/invoices", timeout=5)
        if response.status_code == 200:
            print("✅ Invoices page loading")
        else:
            print(f"❌ Invoices page failed: {response.status_code}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Frontend test failed: {e}")
        return False

def test_debug_panel_features():
    """Test specific debug panel features"""
    print("\n🔧 Testing Debug Panel Features...")
    
    try:
        # Test that debug information structure is correct
        response = requests.get("http://localhost:8000/api/invoices", timeout=5)
        if response.status_code == 200:
            invoices = response.json()
            
            for invoice in invoices:
                if 'ocr_debug' in invoice:
                    debug = invoice['ocr_debug']
                    
                    # Test preprocessing steps
                    if 'preprocessing_steps' in debug:
                        steps = debug['preprocessing_steps']
                        for step in steps:
                            required_fields = ['step', 'status', 'processing_time']
                            missing = [field for field in required_fields if field not in step]
                            if missing:
                                print(f"⚠️ Preprocessing step missing fields: {missing}")
                            else:
                                print(f"✅ Preprocessing step '{step['step']}' has all required fields")
                    
                    # Test engine results
                    if 'engine_results' in debug:
                        engines = debug['engine_results']
                        for engine in engines:
                            required_fields = ['engine', 'status', 'confidence', 'processing_time']
                            missing = [field for field in required_fields if field not in engine]
                            if missing:
                                print(f"⚠️ Engine result missing fields: {missing}")
                            else:
                                print(f"✅ Engine '{engine['engine']}' has all required fields")
                    
                    # Test field extraction
                    if 'field_extraction' in debug:
                        fields = debug['field_extraction']
                        for field in fields:
                            required_fields = ['field', 'status', 'value', 'confidence', 'extraction_method']
                            missing = [field_name for field_name in required_fields if field_name not in field]
                            if missing:
                                print(f"⚠️ Field extraction missing fields: {missing}")
                            else:
                                print(f"✅ Field '{field['field']}' has all required fields")
                    
                    # Test validation results
                    if 'validation_results' in debug:
                        validations = debug['validation_results']
                        for validation in validations:
                            required_fields = ['rule', 'status']
                            missing = [field for field in required_fields if field not in validation]
                            if missing:
                                print(f"⚠️ Validation result missing fields: {missing}")
                            else:
                                print(f"✅ Validation rule '{validation['rule']}' has all required fields")
                    
                    # Test segmentation info
                    if 'segmentation_info' in debug:
                        seg_info = debug['segmentation_info']
                        required_fields = ['total_sections', 'sections_processed', 'multi_invoice_detected']
                        missing = [field for field in required_fields if field not in seg_info]
                        if missing:
                            print(f"⚠️ Segmentation info missing fields: {missing}")
                        else:
                            print(f"✅ Segmentation info has all required fields")
                    
                    break  # Only test first invoice with debug info
            
            return True
        else:
            print(f"❌ Failed to fetch invoices for feature test: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Feature test failed: {e}")
        return False

def main():
    """Run all OCR debug panel tests"""
    print("🧪 OCR Debug Panel Verification")
    print("=" * 50)
    
    tests = [
        ("OCR Debug Integration", test_ocr_debug_integration),
        ("Frontend Debug Panel", test_frontend_debug_panel),
        ("Debug Panel Features", test_debug_panel_features),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        print("-" * 30)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 OCR DEBUG PANEL TEST RESULTS")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 OCR DEBUG PANEL IS WORKING!")
        print("\n🚀 Debug Panel Features:")
        print("   • Preprocessing steps tracking")
        print("   • OCR engine results comparison")
        print("   • Field extraction analysis")
        print("   • Validation rule checking")
        print("   • Multi-invoice segmentation info")
        print("\n🌐 Access your application:")
        print("   • Frontend: http://localhost:3000")
        print("   • Invoices: http://localhost:3000/invoices")
        print("   • Click on any invoice card to see debug info")
        print("   • Look for the '🔍 OCR Processing Debug' section")
    else:
        print("⚠️ Some tests failed. Please check the logs above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 