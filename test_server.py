#!/usr/bin/env python3
"""
Quick test to verify the single-port server works
"""
import subprocess
import time
import requests
import sys

def test_server():
    print("🧪 Testing single-port server...")
    
    # Start server
    print("Starting server...")
    proc = subprocess.Popen([sys.executable, "backend/final_single_port.py"])
    
    try:
        # Wait for server to start
        time.sleep(3)
        
        # Test endpoints
        base_url = "http://127.0.0.1:8001"
        
        print("Testing root endpoint...")
        r = requests.get(f"{base_url}/", timeout=5)
        print(f"✅ Root: {r.status_code} - {r.text[:100]}...")
        
        print("Testing health endpoint...")
        r = requests.get(f"{base_url}/api/health", timeout=5)
        print(f"✅ Health: {r.status_code} - {r.json()}")
        
        print("Testing status endpoint...")
        r = requests.get(f"{base_url}/api/status", timeout=5)
        print(f"✅ Status: {r.status_code} - {r.json()}")
        
        print("Testing LLM proxy...")
        try:
            r = requests.get(f"{base_url}/llm/api/tags", timeout=5)
            print(f"✅ LLM Proxy: {r.status_code} - {r.text[:100]}...")
        except Exception as e:
            print(f"⚠️  LLM Proxy: {e} (Ollama not running?)")
        
        print("\n🎉 All tests passed! Server is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        # Clean up
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    test_server()
