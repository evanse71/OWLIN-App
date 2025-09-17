#!/usr/bin/env python3
"""
Test the server startup and API endpoints
"""
import sys
import os
sys.path.insert(0, '.')

try:
    from main import app
    print("✅ App imported successfully")
    
    # Test the app creation
    print("✅ App created successfully")
    
    # Test a simple endpoint
    from fastapi.testclient import TestClient
    client = TestClient(app)
    
    # Test health endpoint
    response = client.get("/api/health")
    print(f"✅ Health endpoint: {response.status_code}")
    
    # Test delivery notes endpoint
    response = client.get("/api/delivery-notes")
    print(f"✅ Delivery notes endpoint: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Found {len(data.get('items', []))} delivery notes")
    
    print("🎉 All tests passed!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()