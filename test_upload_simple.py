#!/usr/bin/env python3
"""
Simple test script to verify the upload flow is working properly.
This script uses only built-in Python libraries (no aiohttp required).
"""

import requests
import json
import time
import os
from pathlib import Path

# Test configuration
API_BASE_URL = "http://localhost:8000"
TEST_FILE_PATH = "data/uploads/7fddbd78-5edf-4b02-88df-4cca80bdcbd2.pdf"  # Use existing PDF file

def test_api_health():
    """Test if the API is running and healthy."""
    print("🏥 Testing API Health")
    print("-" * 30)
    
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ API is healthy and responding")
            return True
        else:
            print(f"⚠️ API responded with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API health check failed: {str(e)}")
        return False

def test_upload_flow():
    """Test the complete upload flow with debugging."""
    print("🧪 Starting Upload Flow Test")
    print("=" * 50)
    
    # Check if test file exists
    if not os.path.exists(TEST_FILE_PATH):
        print(f"❌ Test file not found: {TEST_FILE_PATH}")
        print("Please create a test PDF file or update TEST_FILE_PATH")
        print("For testing, you can create a simple PDF or use any existing PDF file.")
        return False
    
    try:
        print(f"📤 Uploading file: {TEST_FILE_PATH}")
        
        # Prepare file for upload
        with open(TEST_FILE_PATH, 'rb') as f:
            files = {'file': (os.path.basename(TEST_FILE_PATH), f, 'application/pdf')}
            
            # Start timer
            start_time = time.time()
            
            # Make upload request with timeout
            response = requests.post(
                f"{API_BASE_URL}/api/upload",
                files=files,
                timeout=60  # 60 second timeout
            )
            
            elapsed_time = time.time() - start_time
            print(f"⏱️ Request completed in {elapsed_time:.2f} seconds")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Upload successful!")
                print(f"📊 Response: {json.dumps(result, indent=2)}")
                
                # Verify response structure
                required_fields = ['message', 'invoice_id', 'filename', 'parsed_data']
                missing_fields = [field for field in required_fields if field not in result]
                
                if missing_fields:
                    print(f"⚠️ Missing required fields: {missing_fields}")
                    return False
                
                # Check parsed data
                parsed_data = result.get('parsed_data', {})
                confidence = parsed_data.get('confidence', 0)
                line_items = parsed_data.get('line_items', [])
                
                print(f"📈 Confidence: {confidence}%")
                print(f"📝 Line items: {len(line_items)}")
                print(f"🏷️ Supplier: {parsed_data.get('supplier_name', 'Unknown')}")
                print(f"💰 Total: £{parsed_data.get('total_amount', 0):.2f}")
                
                return True
                
            else:
                print(f"❌ Upload failed with status {response.status_code}")
                print(f"Error: {response.text}")
                return False
                
    except requests.exceptions.Timeout:
        print("⏰ Request timed out after 60 seconds")
        return False
    except Exception as e:
        print(f"💥 Unexpected error: {str(e)}")
        return False

def test_backend_endpoints():
    """Test basic backend endpoints."""
    print("🔧 Testing Backend Endpoints")
    print("-" * 30)
    
    endpoints = [
        ("/", "Root endpoint"),
        ("/health", "Health check"),
        ("/api/health", "API health check"),
        ("/api/invoices", "Invoices endpoint"),
    ]
    
    all_passed = True
    
    for endpoint, description in endpoints:
        try:
            response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {description}: OK")
            else:
                print(f"⚠️ {description}: Status {response.status_code}")
                all_passed = False
        except Exception as e:
            print(f"❌ {description}: Failed - {str(e)}")
            all_passed = False
    
    return all_passed

def main():
    """Main test function."""
    print("🚀 Owlin Upload Flow Test (Simple Version)")
    print("=" * 50)
    
    # Test API health first
    if not test_api_health():
        print("\n❌ API is not available. Please start the backend server.")
        print("Run: python -m uvicorn backend.main:app --reload --port 8000")
        return
    
    print("\n" + "=" * 50)
    
    # Test backend endpoints
    if not test_backend_endpoints():
        print("\n⚠️ Some backend endpoints are not responding correctly.")
    
    print("\n" + "=" * 50)
    
    # Test upload flow
    success = test_upload_flow()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed! Upload flow is working correctly.")
    else:
        print("❌ Tests failed. Check the logs above for details.")
    
    print("\n📋 Debugging Tips:")
    print("• Check browser console for frontend logs")
    print("• Check backend logs for detailed processing info")
    print("• Verify OCR dependencies are installed")
    print("• Check file permissions and disk space")
    print("• Make sure you have a test PDF file available")

if __name__ == "__main__":
    main() 