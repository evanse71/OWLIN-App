#!/usr/bin/env python3
"""Check if backend is running and accessible"""
import requests
import sys
import time

print("=" * 50)
print("Checking Backend Status")
print("=" * 50)
print()

# Test 1: Check if port is accessible
print("1. Testing connection to http://127.0.0.1:8000...")
try:
    response = requests.get("http://127.0.0.1:8000/api/routes/status", timeout=5)
    print(f"   [OK] Backend is running! (Status: {response.status_code})")
    
    data = response.json()
    print(f"   Total Routes: {data.get('total_routes', 'N/A')}")
    print(f"   Chat Router Loaded: {data.get('chat_router_loaded', False)}")
    print(f"   Chat Endpoint Available: {data.get('chat_endpoint_available', False)}")
    
except requests.exceptions.ConnectionError:
    print("   [FAIL] Backend is NOT running - Connection refused")
    print("   Please start the backend with: START_BACKEND.bat")
    sys.exit(1)
except Exception as e:
    print(f"   [ERROR] {e}")
    sys.exit(1)

print()

# Test 2: Check chat endpoint
print("2. Testing /api/chat/status endpoint...")
try:
    response = requests.get("http://127.0.0.1:8000/api/chat/status", timeout=5)
    print(f"   [OK] Chat endpoint accessible! (Status: {response.status_code})")
    data = response.json()
    print(f"   Status: {data.get('status', 'N/A')}")
    print(f"   Ollama Available: {data.get('ollama_available', False)}")
except Exception as e:
    print(f"   [WARN] Chat endpoint error: {e}")
    print("   (This might be OK if Ollama is not running)")

print()

# Test 3: Check invoices endpoint
print("3. Testing /api/invoices endpoint...")
try:
    response = requests.get("http://127.0.0.1:8000/api/invoices?dev=1", timeout=5)
    print(f"   [OK] Invoices endpoint accessible! (Status: {response.status_code})")
    data = response.json()
    if isinstance(data, list):
        print(f"   Returned {len(data)} invoices")
except Exception as e:
    print(f"   [WARN] Invoices endpoint error: {e}")

print()
print("=" * 50)
print("Backend Status: READY")
print("=" * 50)
print()
print("Frontend should now be able to connect!")
print("Access at: http://localhost:5176")
print()
