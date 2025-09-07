#!/usr/bin/env python3
"""
Test script to upload a file and verify OCR debug information
"""

import requests
import json
import time

def create_test_invoice_text():
    """Create a test invoice text file"""
    test_content = """
INVOICE

Supplier: WILD HORSE BREWING CO
Invoice Number: TEST-DEBUG-001
Date: 2025-01-15

Items:
1. Craft Beer - 6 Pack     £12.00
2. IPA Selection - 12 Pack  £24.00
3. Stout Collection - 4 Pack £18.00

Subtotal: £54.00
VAT (20%): £10.80
TOTAL: £64.80

Thank you for your business!
"""
    
    with open("test_invoice_debug.txt", "w") as f:
        f.write(test_content)
    
    return "test_invoice_debug.txt"

def upload_test_file(filename):
    """Upload test file to backend"""
    print(f"📤 Uploading {filename}...")
    
    try:
        with open(filename, 'rb') as f:
            files = {'file': (filename, f, 'text/plain')}
            response = requests.post(
                "http://localhost:8000/api/upload",
                files=files,
                timeout=30
            )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Upload successful")
            return result
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None

def check_ocr_debug_info(upload_result):
    """Check if OCR debug information is included"""
    print("\n🔍 Checking OCR debug information...")
    
    if not upload_result:
        print("❌ No upload result to check")
        return False
    
    # Check if ocr_debug is present
    if 'ocr_debug' in upload_result:
        debug = upload_result['ocr_debug']
        print("✅ OCR debug information found!")
        
        # Check preprocessing steps
        if 'preprocessing_steps' in debug:
            steps = debug['preprocessing_steps']
            print(f"   - Preprocessing steps: {len(steps)}")
            for step in steps:
                print(f"     • {step['step']}: {step['status']} ({step.get('processing_time', 0):.2f}s)")
        
        # Check engine results
        if 'engine_results' in debug:
            engines = debug['engine_results']
            print(f"   - OCR engines: {len(engines)}")
            for engine in engines:
                print(f"     • {engine['engine']}: {engine['status']} ({engine['confidence']:.1%})")
        
        # Check field extraction
        if 'field_extraction' in debug:
            fields = debug['field_extraction']
            print(f"   - Field extraction: {len(fields)}")
            for field in fields:
                print(f"     • {field['field']}: {field['status']} ({field['value']})")
        
        # Check validation results
        if 'validation_results' in debug:
            validations = debug['validation_results']
            print(f"   - Validation rules: {len(validations)}")
            for validation in validations:
                print(f"     • {validation['rule']}: {validation['status']}")
        
        # Check segmentation info
        if 'segmentation_info' in debug:
            seg_info = debug['segmentation_info']
            print(f"   - Segmentation: {seg_info['total_sections']} sections, multi-invoice: {seg_info['multi_invoice_detected']}")
        
        return True
    else:
        print("❌ No OCR debug information found in upload result")
        return False

def main():
    """Run the upload test"""
    print("🧪 OCR Debug Upload Test")
    print("=" * 40)
    
    # Step 1: Create test file
    print("\n📝 Creating test invoice file...")
    filename = create_test_invoice_text()
    print(f"✅ Created {filename}")
    
    # Step 2: Upload file
    print("\n📤 Uploading test file...")
    upload_result = upload_test_file(filename)
    
    if not upload_result:
        print("❌ Upload failed, cannot continue")
        return False
    
    # Step 3: Check OCR debug info
    debug_found = check_ocr_debug_info(upload_result)
    
    # Step 4: Wait and check if it appears in invoices list
    print("\n⏳ Waiting for processing...")
    time.sleep(3)
    
    try:
        response = requests.get("http://localhost:8000/api/invoices", timeout=10)
        if response.status_code == 200:
            invoices = response.json()
            print(f"✅ Found {len(invoices)} invoices in database")
            
            # Look for our test invoice
            test_invoice = None
            for invoice in invoices:
                if 'TEST-DEBUG-001' in str(invoice.get('invoice_number', '')):
                    test_invoice = invoice
                    break
            
            if test_invoice:
                print("✅ Test invoice found in database")
                if 'ocr_debug' in test_invoice:
                    print("✅ OCR debug info persisted in database")
                    return True
                else:
                    print("⚠️ OCR debug info not found in database (may be normal for old data)")
            else:
                print("⚠️ Test invoice not found in database yet")
        else:
            print(f"❌ Failed to fetch invoices: {response.status_code}")
    except Exception as e:
        print(f"❌ Error checking database: {e}")
    
    return debug_found

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 OCR DEBUG PANEL IS WORKING!")
        print("\n🚀 You can now:")
        print("   1. Go to http://localhost:3000/invoices")
        print("   2. Upload any document")
        print("   3. Click on the invoice card")
        print("   4. Look for '🔍 OCR Processing Debug' section")
        print("   5. Click 'Show Debug Info' to see detailed processing steps")
    else:
        print("\n⚠️ OCR debug panel test failed")
    
    exit(0 if success else 1) 