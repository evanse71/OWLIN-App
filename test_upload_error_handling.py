#!/usr/bin/env python3
"""
Test script for upload error handling and edge cases
"""

import requests
import tempfile
import os
from pathlib import Path

def test_upload_error_handling():
    """Test various upload error scenarios"""
    base_url = "http://localhost:8000/api"
    
    print("🧪 Testing Upload Error Handling")
    print("=" * 50)
    
    # Test 1: Upload empty file
    print("\n1️⃣ Testing empty file upload...")
    try:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'')  # Empty file
        
        with open(f.name, 'rb') as file:
            response = requests.post(f"{base_url}/upload/invoice", files={"file": file})
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        os.unlink(f.name)
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Upload invalid file type
    print("\n2️⃣ Testing invalid file type...")
    try:
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'This is a text file, not a PDF or image')
        
        with open(f.name, 'rb') as file:
            response = requests.post(f"{base_url}/upload/invoice", files={"file": file})
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        os.unlink(f.name)
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Upload very large file
    print("\n3️⃣ Testing large file upload...")
    try:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            # Create a 15MB file (larger than 10MB limit)
            f.write(b'0' * (15 * 1024 * 1024))
        
        with open(f.name, 'rb') as file:
            response = requests.post(f"{base_url}/upload/invoice", files={"file": file})
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        os.unlink(f.name)
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 4: Upload corrupted PDF
    print("\n4️⃣ Testing corrupted PDF upload...")
    try:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'This is not a valid PDF file')
        
        with open(f.name, 'rb') as file:
            response = requests.post(f"{base_url}/upload/invoice", files={"file": file})
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        os.unlink(f.name)
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 5: Check server logs
    print("\n5️⃣ Checking server logs...")
    print("Check the server console output for detailed logging information.")
    print("You should see step-by-step progress and detailed error information.")
    
    print("\n✅ Error handling test completed!")
    print("\n📋 Expected log output should include:")
    print("   - Step-by-step progress indicators (🔄 Step 1, Step 2, etc.)")
    print("   - File validation results")
    print("   - File save operations")
    print("   - Database operations")
    print("   - OCR processing status")
    print("   - Detailed error messages with full stack traces")
    print("   - File status updates")

if __name__ == "__main__":
    test_upload_error_handling() 