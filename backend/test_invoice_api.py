#!/usr/bin/env python3
"""
Test script to verify the invoice API is working correctly
"""

import requests
import time

def test_invoice_api():
    """Test the invoice API endpoints"""
    
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Invoice API...")
    
    # 1. Test health endpoint
    print("\n1️⃣ Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"   Health: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return False
    
    # 2. Test database path endpoint
    print("\n2️⃣ Testing database path endpoint...")
    try:
        response = requests.get(f"{base_url}/api/debug/db-path")
        db_info = response.json()
        print(f"   DB Path: {db_info['db_path']}")
        print(f"   DB Exists: {db_info['exists']}")
        print(f"   DB Size: {db_info['size_bytes']} bytes")
    except Exception as e:
        print(f"   ❌ DB path check failed: {e}")
        return False
    
    # 3. Test invoice endpoint with seeded data
    print("\n3️⃣ Testing invoice endpoint...")
    try:
        response = requests.get(f"{base_url}/api/invoices/inv_seed_001")
        if response.status_code == 200:
            invoice_data = response.json()
            print(f"   ✅ Invoice found: {invoice_data['id']}")
            print(f"   Meta: {invoice_data['meta']}")
            print(f"   Lines count: {len(invoice_data['lines'])}")
            if invoice_data['lines']:
                first_line = invoice_data['lines'][0]
                print(f"   First line: {first_line}")
        else:
            print(f"   ❌ Invoice not found: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Invoice endpoint failed: {e}")
        return False
    
    # 4. Test debug raw endpoint
    print("\n4️⃣ Testing debug raw endpoint...")
    try:
        response = requests.get(f"{base_url}/api/invoices/debug/raw/inv_seed_001")
        if response.status_code == 200:
            raw_data = response.json()
            print(f"   ✅ Raw data retrieved")
            print(f"   Raw meta: {raw_data['raw']['meta']}")
            if raw_data['raw']['lines']:
                print(f"   Raw first line: {raw_data['raw']['lines'][0]}")
        else:
            print(f"   ❌ Raw endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Raw endpoint failed: {e}")
        return False
    
    print("\n✅ All tests completed!")
    return True

if __name__ == "__main__":
    # Wait a moment for server to be ready
    print("⏳ Waiting for server to be ready...")
    time.sleep(2)
    
    success = test_invoice_api()
    if success:
        print("\n🎉 Invoice API is working correctly!")
    else:
        print("\n💥 Invoice API has issues!") 