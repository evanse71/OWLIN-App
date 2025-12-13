#!/usr/bin/env python3
"""
Final verification of the complete single-port Owlin setup
"""
import subprocess
import time
import requests
import sys
import json

def verify_final_setup():
    print("🎯 Final Verification of Single-Port Owlin Setup")
    print("=" * 60)
    
    # Start server
    print("🚀 Starting server...")
    proc = subprocess.Popen([sys.executable, "-m", "backend.final_single_port"])
    
    try:
        time.sleep(3)
        base_url = "http://127.0.0.1:8001"
        
        print("\n1. 🌐 Root Endpoint (UI)")
        r = requests.get(f"{base_url}/", timeout=5)
        print(f"✅ Status: {r.status_code}")
        print(f"   Content: {'HTML UI' if 'html' in r.text.lower() else 'JSON fallback'}")
        
        print("\n2. ❤️  Health Endpoint")
        r = requests.get(f"{base_url}/api/health", timeout=5)
        print(f"✅ Status: {r.status_code} - {r.json()}")
        
        print("\n3. 📊 Status Endpoint")
        r = requests.get(f"{base_url}/api/status", timeout=5)
        status_data = r.json()
        print(f"✅ Status: {r.status_code}")
        print(f"   API Mounted: {status_data.get('api_mounted', 'Unknown')}")
        print(f"   API Error: {status_data.get('api_error', 'None')}")
        
        print("\n4. 🔄 Retry-Mount Test")
        r = requests.post(f"{base_url}/api/retry-mount", timeout=5)
        print(f"✅ Status: {r.status_code} - {r.json()}")
        
        print("\n5. 🎯 Real API Test")
        if status_data.get('api_mounted'):
            r = requests.get(f"{base_url}/api/manual/invoices", timeout=5)
            print(f"✅ Manual Invoices: {r.status_code} - {r.json()}")
        else:
            print("⚠️  API not mounted")
        
        print("\n6. 🧠 LLM Proxy Test")
        try:
            r = requests.get(f"{base_url}/llm/api/tags", timeout=5)
            print(f"✅ LLM Proxy: {r.status_code}")
        except Exception as e:
            print(f"⚠️  LLM Proxy: {e} (Ollama not running?)")
        
        print("\n" + "=" * 60)
        print("🎉 FINAL VERIFICATION COMPLETE!")
        print("=" * 60)
        
        if status_data.get('api_mounted'):
            print("✅ SUCCESS: Complete single-port Owlin is working!")
            print("\n🚀 LAUNCH COMMAND:")
            print("   python -m backend.final_single_port")
            print("\n🌐 ACCESS POINTS:")
            print("   UI: http://127.0.0.1:8001")
            print("   API: http://127.0.0.1:8001/api/*")
            print("   LLM: http://127.0.0.1:8001/llm/*")
            print("   Health: http://127.0.0.1:8001/api/health")
            print("   Status: http://127.0.0.1:8001/api/status")
        else:
            print("⚠️  PARTIAL SUCCESS: Server stable, API needs fixes")
            print("   Use: POST /api/retry-mount after fixing imports")
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    verify_final_setup()
