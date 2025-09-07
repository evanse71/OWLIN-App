#!/usr/bin/env python3
"""Full system test for OWLIN-App"""

import requests
import time
import json
import os
import sys
from pathlib import Path

# Configuration
BACKEND_URL = "http://localhost:8001"
FRONTEND_URL = "http://localhost:3000"

def test_backend_health():
    """Test backend health endpoint"""
    print("🔍 Testing Backend Health...")
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend Health: {data}")
            return True
        else:
            print(f"❌ Backend Health failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend Health error: {e}")
        return False

def test_backend_ready():
    """Test backend ready endpoint"""
    print("🔍 Testing Backend Ready...")
    try:
        response = requests.get(f"{BACKEND_URL}/ready", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend Ready: {data}")
            return True
        else:
            print(f"❌ Backend Ready failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend Ready error: {e}")
        return False

def test_backend_invoices():
    """Test backend invoices endpoint"""
    print("🔍 Testing Backend Invoices...")
    try:
        response = requests.get(f"{BACKEND_URL}/invoices", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend Invoices: {len(data)} invoices found")
            return True
        else:
            print(f"❌ Backend Invoices failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend Invoices error: {e}")
        return False

def test_backend_analytics():
    """Test backend analytics endpoint"""
    print("🔍 Testing Backend Analytics...")
    try:
        response = requests.get(f"{BACKEND_URL}/analytics", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend Analytics: {data}")
            return True
        else:
            print(f"❌ Backend Analytics failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend Analytics error: {e}")
        return False

def test_support_pack():
    """Test support pack creation"""
    print("🔍 Testing Support Pack...")
    try:
        response = requests.post(f"{BACKEND_URL}/support-pack", timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Support Pack: {data}")
            return True
        else:
            print(f"❌ Support Pack failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Support Pack error: {e}")
        return False

def test_file_upload():
    """Test file upload with deduplication"""
    print("🔍 Testing File Upload...")
    try:
        # Create a test file
        test_file_path = "/tmp/test_invoice.txt"
        with open(test_file_path, "w") as f:
            f.write("Test invoice content")
        
        # Upload the file
        with open(test_file_path, "rb") as f:
            files = {"file": ("test_invoice.txt", f, "text/plain")}
            response = requests.post(f"{BACKEND_URL}/upload", files=files, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ File Upload: {data}")
            
            # Test duplicate upload
            with open(test_file_path, "rb") as f:
                files = {"file": ("test_invoice.txt", f, "text/plain")}
                response2 = requests.post(f"{BACKEND_URL}/upload", files=files, timeout=30)
            
            if response2.status_code == 409:
                print("✅ Duplicate Detection: Working correctly")
            else:
                print(f"⚠️  Duplicate Detection: Unexpected status {response2.status_code}")
            
            return True
        else:
            print(f"❌ File Upload failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ File Upload error: {e}")
        return False

def test_frontend():
    """Test frontend accessibility"""
    print("🔍 Testing Frontend...")
    try:
        response = requests.get(FRONTEND_URL, timeout=10)
        if response.status_code == 200:
            print(f"✅ Frontend: Accessible at {FRONTEND_URL}")
            return True
        else:
            print(f"❌ Frontend failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Frontend error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Full System Test")
    print("=" * 50)
    
    # Wait for services to start
    print("⏳ Waiting for services to start...")
    time.sleep(5)
    
    tests = [
        ("Backend Health", test_backend_health),
        ("Backend Ready", test_backend_ready),
        ("Backend Invoices", test_backend_invoices),
        ("Backend Analytics", test_backend_analytics),
        ("Support Pack", test_support_pack),
        ("File Upload", test_file_upload),
        ("Frontend", test_frontend),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name}...")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! System is fully operational.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the logs above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 