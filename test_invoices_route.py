#!/usr/bin/env python3
"""Test script to verify /invoices route is working"""
import requests
import sys

try:
    print("Testing http://localhost:5176/invoices...")
    response = requests.get("http://localhost:5176/invoices", timeout=5)
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
    print(f"Content length: {len(response.content)} bytes")
    
    if response.status_code == 200:
        if 'html' in response.headers.get('Content-Type', '').lower():
            print("✅ SUCCESS! Route is serving HTML")
            print(f"Content preview: {response.text[:200]}")
            sys.exit(0)
        else:
            print(f"⚠️  Status 200 but not HTML: {response.text[:200]}")
            sys.exit(1)
    else:
        print(f"❌ Error: Status {response.status_code}")
        print(f"Response: {response.text[:200]}")
        sys.exit(1)
except Exception as e:
    print(f"❌ Exception: {e}")
    sys.exit(1)

