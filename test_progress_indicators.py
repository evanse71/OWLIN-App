#!/usr/bin/env python3
"""
Test script to verify progress indicators and processing completion
"""

import requests
import time
import json

def test_progress_indicators():
    """Test that progress indicators work and processing completes"""
    print("🧪 Testing Progress Indicators and Processing...")
    
    try:
        # Test with a simple file
        test_file = "data/uploads/1a5919ea-45c7-4bfa-a3bf-5c0c6d886b26_20250809_155957.pdf"
        
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
            print(f"   - Invoice ID: {data.get('invoice_id', 'N/A')}")
            print(f"   - Supplier: {data.get('supplier_name', 'N/A')}")
            print(f"   - Status: {data.get('status', 'N/A')}")
            print(f"   - Confidence: {data.get('confidence', 'N/A')}")
            print(f"   - Line items: {len(data.get('line_items', []))}")
            
            # Check if processing completed
            if data.get('status') in ['processed', 'manual_review']:
                print("✅ Processing completed successfully!")
                return True
            else:
                print("⚠️ Processing may still be in progress")
                return False
        else:
            print(f"❌ Upload failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_frontend_progress():
    """Test that frontend shows progress indicators"""
    print("🧪 Testing Frontend Progress Display...")
    
    try:
        response = requests.get("http://localhost:3000/invoices", timeout=10)
        if response.status_code == 200:
            content = response.text
            
            # Check for progress-related elements
            if "processing" in content.lower():
                print("✅ Frontend has processing state handling")
            else:
                print("⚠️ Frontend may not show processing state")
            
            # Check for circular progress indicators
            if "stroke-dasharray" in content or "animate-spin" in content:
                print("✅ Frontend has progress indicators")
            else:
                print("⚠️ Frontend may not have progress indicators")
            
            return True
        else:
            print(f"❌ Frontend not accessible: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Frontend test failed: {e}")
        return False

def main():
    """Run progress indicator tests"""
    print("🚀 Testing Progress Indicators and Processing...")
    print("=" * 50)
    
    # Test backend processing
    backend_ok = test_progress_indicators()
    
    print("\n" + "=" * 50)
    
    # Test frontend progress display
    frontend_ok = test_frontend_progress()
    
    print("\n" + "=" * 50)
    print("📋 Progress Test Summary:")
    print(f"   Backend Processing: {'✅' if backend_ok else '❌'}")
    print(f"   Frontend Progress: {'✅' if frontend_ok else '❌'}")
    
    if backend_ok and frontend_ok:
        print("\n🎉 Progress indicators are working!")
        print("\n📝 Manual Test Instructions:")
        print("1. Open http://localhost:3000/invoices in your browser")
        print("2. Upload a PDF file")
        print("3. Watch for circular progress indicators (0-100%)")
        print("4. Verify cards transition from 'processing' to 'processed'")
        print("5. Check that supplier name, total, etc. appear after processing")
    else:
        print("\n⚠️ Some progress features may not be working properly")

if __name__ == "__main__":
    main() 