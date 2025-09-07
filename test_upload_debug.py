#!/usr/bin/env python3
"""
Upload Debug Test
Tests the upload endpoint to identify issues
"""

import requests
import os
import sys

def test_upload_endpoint():
    """Test the upload endpoint to see what's happening"""
    print("🔍 Testing Upload Endpoint")
    print("=" * 40)
    
    # Test 1: Check if backend is running
    try:
        response = requests.get("http://localhost:8002/health", timeout=5)
        print(f"✅ Backend health: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Backend health check failed: {e}")
        return False
    
    # Test 2: Check upload endpoint directly
    try:
        # Create a simple test file
        test_content = "This is a test file for upload debugging"
        with open("test_upload.txt", "w") as f:
            f.write(test_content)
        
        # Test upload
        with open("test_upload.txt", "rb") as f:
            files = {"file": ("test_upload.txt", f, "text/plain")}
            response = requests.post("http://localhost:8002/api/upload", files=files, timeout=30)
        
        print(f"📤 Upload response status: {response.status_code}")
        print(f"📤 Upload response headers: {dict(response.headers)}")
        print(f"📤 Upload response text: {response.text}")
        
        # Clean up
        os.remove("test_upload.txt")
        
        if response.status_code == 200:
            print("✅ Upload endpoint working correctly")
            return True
        else:
            print(f"❌ Upload endpoint returned status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Upload test failed: {e}")
        return False

def test_backend_logs():
    """Check what's happening in the backend"""
    print("\n🔍 Backend Logs Check")
    print("-" * 40)
    
    try:
        # Check if we can access the backend logs
        import subprocess
        result = subprocess.run(
            ["ps", "aux", "|", "grep", "uvicorn"],
            capture_output=True,
            text=True,
            shell=True
        )
        print("Backend processes:")
        print(result.stdout)
        
    except Exception as e:
        print(f"Could not check backend logs: {e}")

if __name__ == "__main__":
    success = test_upload_endpoint()
    test_backend_logs()
    
    if success:
        print("\n✅ Upload endpoint is working correctly")
    else:
        print("\n❌ Upload endpoint has issues")
        print("\n🔧 Troubleshooting steps:")
        print("1. Check if backend is running: curl http://localhost:8002/health")
        print("2. Check backend logs for errors")
        print("3. Verify upload route is properly configured")
        print("4. Test with a simple file upload") 