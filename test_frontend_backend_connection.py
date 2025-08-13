#!/usr/bin/env python3
"""
Frontend-Backend Connection Test
Tests the connection between frontend and backend
"""

import requests
import json

def test_connection():
    """Test the connection between frontend and backend"""
    print("🔍 Testing Frontend-Backend Connection")
    print("=" * 50)
    
    # Test 1: Backend direct
    print("\n🔍 Test 1: Backend Direct")
    print("-" * 30)
    try:
        response = requests.get("http://localhost:8002/health", timeout=5)
        print(f"✅ Backend health: {response.status_code}")
    except Exception as e:
        print(f"❌ Backend health failed: {e}")
        return False
    
    # Test 2: Frontend to backend via proxy
    print("\n🔍 Test 2: Frontend Proxy")
    print("-" * 30)
    try:
        response = requests.get("http://localhost:3000/api/health", timeout=5)
        print(f"✅ Frontend proxy health: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Frontend proxy failed: {e}")
    
    # Test 3: Upload test with different file types
    print("\n🔍 Test 3: Upload Tests")
    print("-" * 30)
    
    test_files = [
        ("test.txt", "This is a test file", "text/plain"),
        ("test.pdf", "PDF content", "application/pdf"),
    ]
    
    for filename, content, content_type in test_files:
        print(f"\n📤 Testing upload: {filename}")
        
        # Test direct backend upload
        try:
            files = {"file": (filename, content, content_type)}
            response = requests.post("http://localhost:8002/api/upload", files=files, timeout=30)
            print(f"  Backend direct: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"  Confidence: {result.get('parsed_data', {}).get('confidence', 'N/A')}")
                print(f"  Supplier: {result.get('parsed_data', {}).get('supplier_name', 'N/A')}")
            else:
                print(f"  Error: {response.text}")
        except Exception as e:
            print(f"  Backend error: {e}")
        
        # Test frontend proxy upload
        try:
            files = {"file": (filename, content, content_type)}
            response = requests.post("http://localhost:3000/api/upload", files=files, timeout=30)
            print(f"  Frontend proxy: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"  Confidence: {result.get('parsed_data', {}).get('confidence', 'N/A')}")
                print(f"  Supplier: {result.get('parsed_data', {}).get('supplier_name', 'N/A')}")
            else:
                print(f"  Error: {response.text}")
        except Exception as e:
            print(f"  Frontend error: {e}")
    
    # Test 4: Check if there are any CORS or routing issues
    print("\n🔍 Test 4: Routing Analysis")
    print("-" * 30)
    
    try:
        # Test the rewrite rule
        response = requests.get("http://localhost:3000/api/files", timeout=5)
        print(f"Files endpoint via frontend: {response.status_code}")
        
        response = requests.get("http://localhost:8002/api/files", timeout=5)
        print(f"Files endpoint direct: {response.status_code}")
        
    except Exception as e:
        print(f"Routing test failed: {e}")
    
    return True

if __name__ == "__main__":
    test_connection()
    print("\n🎯 Summary:")
    print("If backend direct works but frontend proxy doesn't, there's a routing issue")
    print("If both fail, there's a backend issue")
    print("If both work, the issue might be in the frontend JavaScript") 