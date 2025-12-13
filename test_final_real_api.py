#!/usr/bin/env python3
"""
Final test script for the real API integration with proper launch context
"""
import subprocess
import time
import requests
import sys
import json

def test_final_real_api():
    print("🧪 Testing Final Real API Integration...")
    print("Running from project root with proper module context...")
    
    # Start server using module approach
    print("Starting server with: python -m backend.final_single_port")
    proc = subprocess.Popen([sys.executable, "-m", "backend.final_single_port"])
    
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
        
        if status_data.get('api_mounted'):
            print("\n4. Testing real API endpoints...")
            try:
                r = requests.get(f"{base_url}/api/manual/invoices", timeout=5)
                print(f"✅ Manual Invoices: {r.status_code} - {r.json()}")
            except Exception as e:
                print(f"⚠️  Manual Invoices: {e}")
            
            try:
                r = requests.post(f"{base_url}/api/manual/invoices", 
                                json={"supplier_id": "test", "supplier_name": "Test", 
                                     "invoice_date": "2024-01-01", "invoice_ref": "TEST-001",
                                     "lines": [{"description": "Test item", "outer_qty": 1, 
                                              "unit_price": 10.00, "vat_rate_percent": 20}]}, 
                                timeout=5)
                print(f"✅ Create Invoice: {r.status_code} - {r.json()}")
            except Exception as e:
                print(f"⚠️  Create Invoice: {e}")
        else:
            print("\n4. Testing retry-mount endpoint...")
            try:
                r = requests.post(f"{base_url}/api/retry-mount", timeout=5)
                print(f"✅ Retry Mount: {r.status_code} - {r.json()}")
                
                # Check status again after retry
                r = requests.get(f"{base_url}/api/status", timeout=5)
                status_data = r.json()
                print(f"   - API Mounted After Retry: {status_data.get('api_mounted')}")
            except requests.exceptions.HTTPError as e:
                print(f"⚠️  Retry Mount: {e}")
        
        print("\n5. Testing LLM proxy...")
        try:
            r = requests.get(f"{base_url}/llm/api/tags", timeout=5)
            print(f"✅ LLM Proxy: {r.status_code} - {r.text[:100]}...")
        except Exception as e:
            print(f"⚠️  LLM Proxy: {e} (Ollama not running?)")
        
        print("\n🎉 Final real API integration test completed!")
        
        if status_data.get('api_mounted'):
            print("\n✅ SUCCESS: Real API is mounted and working!")
            print("📋 Your single-port Owlin is now running with:")
            print("   - UI: http://127.0.0.1:8001")
            print("   - API: http://127.0.0.1:8001/api/*")
            print("   - LLM Proxy: http://127.0.0.1:8001/llm/*")
            print("   - Health: http://127.0.0.1:8001/api/health")
            print("   - Status: http://127.0.0.1:8001/api/status")
            print("\n🚀 LAUNCH COMMAND: python -m backend.final_single_port")
        else:
            print("\n⚠️  API not mounted. Check the error above.")
            print("   The server is stable but the real API needs import fixes.")
            print("   Use: POST /api/retry-mount to re-mount without restart")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        # Clean up
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    test_final_real_api()
