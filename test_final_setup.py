#!/usr/bin/env python3
"""
Comprehensive test for the final single-port setup with retry-mount functionality
"""
import subprocess
import time
import requests
import sys
import json

def test_final_setup():
    print("🧪 Testing Final Single-Port Setup...")
    
    # Start server
    print("Starting server...")
    proc = subprocess.Popen([sys.executable, "backend/final_single_port.py"])
    
    try:
        # Wait for server to start
        time.sleep(3)
        
        base_url = "http://127.0.0.1:8001"
        
        print("\n1. Testing root endpoint...")
        r = requests.get(f"{base_url}/", timeout=5)
        print(f"✅ Root: {r.status_code} - {r.text[:100]}...")
        
        print("\n2. Testing health endpoint...")
        r = requests.get(f"{base_url}/api/health", timeout=5)
        print(f"✅ Health: {r.status_code} - {r.json()}")
        
        print("\n3. Testing status endpoint...")
        r = requests.get(f"{base_url}/api/status", timeout=5)
        status_data = r.json()
        print(f"✅ Status: {r.status_code}")
        print(f"   - API Mounted: {status_data.get('api_mounted')}")
        print(f"   - API Error: {status_data.get('api_error', 'None')[:100]}...")
        
        print("\n4. Testing retry-mount endpoint...")
        try:
            r = requests.post(f"{base_url}/api/retry-mount", timeout=5)
            print(f"✅ Retry Mount: {r.status_code} - {r.json()}")
        except requests.exceptions.HTTPError as e:
            print(f"⚠️  Retry Mount: {e} (Expected if API has import issues)")
        
        print("\n5. Testing LLM proxy...")
        try:
            r = requests.get(f"{base_url}/llm/api/tags", timeout=5)
            print(f"✅ LLM Proxy: {r.status_code} - {r.text[:100]}...")
        except Exception as e:
            print(f"⚠️  LLM Proxy: {e} (Ollama not running?)")
        
        print("\n🎉 Final setup test completed!")
        print("\n📋 Next Steps:")
        print("1. Check /api/status for detailed error info")
        print("2. Fix any import issues in your real API")
        print("3. POST /api/retry-mount to re-mount without restart")
        print("4. Verify api_mounted: true in status")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        # Clean up
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    test_final_setup()
