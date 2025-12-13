#!/usr/bin/env python3
"""
Test script for the Invoices Page
Verifies that the page loads correctly and navigation works
"""

import requests
import time
import os
import json

def test_frontend():
    """Test that the frontend is running and accessible"""
    print("🧪 Testing Frontend...")
    
    try:
        response = requests.get("http://localhost:3000/invoices", timeout=10)
        if response.status_code == 200:
            print("✅ Frontend is running at http://localhost:3000")
            return True
        else:
            print(f"❌ Frontend returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Frontend not accessible: {e}")
        return False

def test_backend():
    """Test that the backend is running and accessible"""
    print("🧪 Testing Backend...")
    
    try:
        response = requests.get("http://localhost:8002/health", timeout=10)
        if response.status_code == 200:
            print("✅ Backend is running at http://localhost:8002")
            return True
        else:
            print(f"❌ Backend returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Backend not accessible: {e}")
        return False

def test_upload_endpoint():
    """Test the upload endpoint with a sample file"""
    print("🧪 Testing Upload Endpoint...")
    
    # Use one of the existing PDF files
    test_file = "data/uploads/1a5919ea-45c7-4bfa-a3bf-5c0c6d886b26_20250809_155957.pdf"
    
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return False
    
    try:
        with open(test_file, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                "http://localhost:8002/api/upload",
                files=files,
                timeout=30
            )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Upload endpoint working")
            print(f"   - Response keys: {list(data.keys())}")
            if 'saved_invoices' in data:
                print(f"   - Invoices found: {len(data['saved_invoices'])}")
            return True
        else:
            print(f"❌ Upload failed with status: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ Upload test failed: {e}")
        return False

def check_navigation():
    """Check that navigation pages exist"""
    print("🧪 Checking Navigation Pages...")
    
    nav_pages = [
        "/",
        "/analytics/",
        "/invoices/",
        "/document-queue/",
        "/flagged/",
        "/suppliers/",
        "/product-trends/",
        "/notes/",
        "/settings/"
    ]
    
    working_pages = []
    for page in nav_pages:
        try:
            response = requests.get(f"http://localhost:3000{page}", timeout=5)
            if response.status_code == 200:
                working_pages.append(page)
                print(f"✅ {page}")
            else:
                print(f"⚠️  {page} - Status: {response.status_code}")
        except:
            print(f"❌ {page} - Not accessible")
    
    return len(working_pages) > 0

def main():
    """Run all tests"""
    print("🚀 Starting Invoices Page Tests...")
    print("=" * 50)
    
    # Test basic connectivity
    frontend_ok = test_frontend()
    backend_ok = test_backend()
    
    if not frontend_ok or not backend_ok:
        print("\n❌ Basic connectivity failed. Please ensure both servers are running:")
        print("   Frontend: npm run dev (port 3000)")
        print("   Backend:  python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8002")
        return
    
    print("\n" + "=" * 50)
    
    # Test upload functionality
    upload_ok = test_upload_endpoint()
    
    print("\n" + "=" * 50)
    
    # Check navigation
    nav_ok = check_navigation()
    
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    print(f"   Frontend: {'✅' if frontend_ok else '❌'}")
    print(f"   Backend:  {'✅' if backend_ok else '❌'}")
    print(f"   Upload:   {'✅' if upload_ok else '❌'}")
    print(f"   Navigation: {'✅' if nav_ok else '❌'}")
    
    if frontend_ok and backend_ok and upload_ok:
        print("\n🎉 Ready for testing!")
        print("\n📝 Manual Test Instructions:")
        print("1. Open http://localhost:3000/invoices in your browser")
        print("2. Verify the navigation header is visible and working")
        print("3. Try uploading a PDF file from data/uploads/")
        print("4. Test the cross-fade animations and keyboard shortcuts")
        print("5. Check that the sticky footer appears when files are uploaded")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    main() 