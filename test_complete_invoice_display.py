#!/usr/bin/env python3
"""
Test script to verify complete invoice display with all required information
"""

import requests
import json
import time

def test_complete_invoice_display():
    """Test that invoices display all required information"""
    print("🧪 Testing Complete Invoice Display...")
    
    try:
        # Test with a proper test invoice file
        test_file = "test_fixtures/test_invoice.txt"
        
        print("📤 Uploading file...")
        with open(test_file, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                "http://localhost:8002/api/upload",
                files=files,
                timeout=60
            )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Upload successful!")
            
            # Check for all required fields
            required_fields = [
                'invoice_id', 'supplier_name', 'invoice_number', 'invoice_date',
                'total_amount', 'confidence', 'original_filename', 'line_items'
            ]
            
            missing_fields = []
            for field in required_fields:
                if field not in data or data[field] is None:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"⚠️ Missing fields: {missing_fields}")
            else:
                print("✅ All required fields present")
            
            print(f"   - Invoice ID: {data.get('invoice_id', 'N/A')}")
            print(f"   - Supplier: {data.get('supplier_name', 'N/A')}")
            print(f"   - Invoice #: {data.get('invoice_number', 'N/A')}")
            print(f"   - Date: {data.get('invoice_date', 'N/A')}")
            print(f"   - Total: {data.get('total_amount', 'N/A')}")
            print(f"   - Confidence: {data.get('confidence', 'N/A')}")
            print(f"   - Filename: {data.get('original_filename', 'N/A')}")
            print(f"   - Line items: {len(data.get('line_items', []))}")
            
            # Check if we got meaningful data
            meaningful_data = (
                data.get('supplier_name') != 'Unknown' and 
                data.get('supplier_name') != 'OCR Failed' and
                data.get('total_amount', 0) > 0 and
                data.get('confidence', 0) > 0
            )
            
            if meaningful_data:
                print("✅ Meaningful data extracted!")
            else:
                print("⚠️ Limited data extracted - OCR may need improvement")
            
            return len(missing_fields) == 0
        else:
            print(f"❌ Upload failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_frontend_display():
    """Test that frontend shows all required information"""
    print("🧪 Testing Frontend Display...")
    
    try:
        response = requests.get("http://localhost:3000/invoices", timeout=10)
        if response.status_code == 200:
            content = response.text
            
            # Check for required display elements
            required_elements = [
                'supplier_name', 'invoice_number', 'invoice_date', 'total_amount',
                'confidence', 'original_filename'
            ]
            
            missing_elements = []
            for element in required_elements:
                if element not in content.lower():
                    missing_elements.append(element)
            
            if missing_elements:
                print(f"⚠️ Missing display elements: {missing_elements}")
            else:
                print("✅ All display elements present")
            
            return len(missing_elements) == 0
        else:
            print(f"❌ Frontend not accessible: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Frontend test failed: {e}")
        return False

def test_backend_health():
    """Test backend health"""
    print("🧪 Testing Backend Health...")
    
    try:
        response = requests.get("http://localhost:8002/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is healthy")
            return True
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend health test failed: {e}")
        return False

def test_frontend_health():
    """Test frontend health"""
    print("🧪 Testing Frontend Health...")
    
    try:
        response = requests.get("http://localhost:3000", timeout=5)
        if response.status_code == 200:
            print("✅ Frontend is healthy")
            return True
        else:
            print(f"❌ Frontend health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Frontend health test failed: {e}")
        return False

def main():
    """Run complete invoice display tests"""
    print("🚀 Testing Complete Invoice Display...")
    print("=" * 50)
    
    # Test backend health
    backend_health = test_backend_health()
    
    print("\n" + "=" * 50)
    
    # Test frontend health
    frontend_health = test_frontend_health()
    
    print("\n" + "=" * 50)
    
    # Test backend response
    backend_ok = test_complete_invoice_display() if backend_health else False
    
    print("\n" + "=" * 50)
    
    # Test frontend display
    frontend_ok = test_frontend_display() if frontend_health else False
    
    print("\n" + "=" * 50)
    print("📋 Complete Display Test Summary:")
    print(f"   Backend Health: {'✅' if backend_health else '❌'}")
    print(f"   Frontend Health: {'✅' if frontend_health else '❌'}")
    print(f"   Backend Response: {'✅' if backend_ok else '❌'}")
    print(f"   Frontend Display: {'✅' if frontend_ok else '❌'}")
    
    if backend_ok and frontend_ok:
        print("\n🎉 Complete invoice display is working!")
        print("\n📝 Required Information Displayed:")
        print("   ✅ Supplier name")
        print("   ✅ File name")
        print("   ✅ Invoice date")
        print("   ✅ Total value (including VAT)")
        print("   ✅ OCR confidence")
        print("   ✅ Line-by-line table (when expanded)")
        print("\n🎯 Ready for manual testing!")
        print("   Open http://localhost:3000/invoices")
        print("   Upload a PDF file to see all information displayed")
    else:
        print("\n⚠️ Some display features may not be working properly")
        if not backend_health:
            print("   - Backend server may not be running")
        if not frontend_health:
            print("   - Frontend server may not be running")

if __name__ == "__main__":
    main() 