#!/usr/bin/env python3
"""
Test the API endpoints directly
"""
import requests
import json
import time

def test_api():
    base_url = "http://localhost:8082"
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/api/health", timeout=5)
        print(f"Health check: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Health check failed: {e}")
        return
    
    # Test delivery notes endpoint
    try:
        response = requests.get(f"{base_url}/api/delivery-notes", timeout=5)
        print(f"Delivery notes: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Found {len(data.get('items', []))} delivery notes")
            for item in data.get('items', []):
                print(f"  - {item.get('id')}: {item.get('supplier_name')} ({item.get('status')})")
    except Exception as e:
        print(f"Delivery notes test failed: {e}")
    
    # Test invoices endpoint
    try:
        response = requests.get(f"{base_url}/api/invoices", timeout=5)
        print(f"Invoices: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Found {len(data.get('items', []))} invoices")
            for item in data.get('items', []):
                print(f"  - {item.get('id')}: {item.get('supplier')} ({item.get('status')})")
    except Exception as e:
        print(f"Invoices test failed: {e}")

if __name__ == "__main__":
    print("Testing API endpoints...")
    test_api()
