#!/usr/bin/env python3
"""
Simple Upload Test
Tests the upload endpoint with minimal data
"""

import requests

def test_simple_upload():
    """Test upload with minimal data"""
    print("🔍 Simple Upload Test")
    print("=" * 30)
    
    # Create a very simple test file
    test_content = "Simple test file"
    
    try:
        files = {"file": ("test.txt", test_content, "text/plain")}
        response = requests.post("http://localhost:8002/api/upload", files=files, timeout=30)
        
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Upload successful")
            print(f"Keys in response: {list(result.keys())}")
            if 'data' in result:
                print(f"✅ Data field present")
                print(f"Data keys: {list(result['data'].keys())}")
            else:
                print(f"❌ Data field missing")
                print(f"Available fields: {list(result.keys())}")
        else:
            print(f"❌ Upload failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_simple_upload() 