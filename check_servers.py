#!/usr/bin/env python3
"""Quick script to verify backend and frontend are running"""
import requests
import sys
import time

print("=" * 50)
print("   Verifying Server Status")
print("=" * 50)
print()

# Check Backend
print("Checking Backend (Port 8000)...")
try:
    response = requests.get("http://127.0.0.1:8000/api/invoices?dev=1", timeout=5)
    print(f"  [OK] Backend is running (Status: {response.status_code})")
except requests.exceptions.ConnectionError:
    print("  [FAIL] Backend not running on port 8000")
except Exception as e:
    print(f"  [WARN] Backend error: {e}")

print()

# Check Frontend
print("Checking Frontend (Port 5176)...")
try:
    response = requests.get("http://127.0.0.1:5176", timeout=5)
    print(f"  [OK] Frontend is running (Status: {response.status_code})")
except requests.exceptions.ConnectionError:
    print("  [FAIL] Frontend not running on port 5176")
except Exception as e:
    print(f"  [WARN] Frontend error: {e}")

print()
print("=" * 50)
print("   Access URLs:")
print("   Frontend: http://localhost:5176")
print("   Backend API: http://localhost:8000/api")
print("=" * 50)
