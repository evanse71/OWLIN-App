#!/usr/bin/env python3
"""
Test script to check LLM status and verify the banner should be gone
"""

import requests
import json

def test_llm_status():
    """Test if LLM is working by checking the backend response"""
    print("🧪 Testing LLM Status...")
    
    try:
        # Test with a simple file to see if LLM processing is available
        test_file = "data/uploads/1a5919ea-45c7-4bfa-a3bf-5c0c6d886b26_20250809_155957.pdf"
        
        with open(test_file, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                "http://localhost:8002/api/upload",
                files=files,
                timeout=60  # Longer timeout for LLM processing
            )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Upload successful with LLM processing")
            print(f"   - Engine used: {data.get('engine_used', 'Unknown')}")
            print(f"   - Confidence: {data.get('confidence', 'Unknown')}")
            print(f"   - Line items: {len(data.get('line_items', []))}")
            
            # Check if LLM was used
            engine_used = data.get('engine_used', '')
            if 'llm' in engine_used.lower():
                print("✅ LLM processing confirmed - banner should be gone!")
                return True
            else:
                print("⚠️  OCR processing used - LLM may not be available")
                return False
        else:
            print(f"❌ Upload failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ LLM test failed: {e}")
        return False

def test_frontend_banner():
    """Test if the frontend shows the LLM banner"""
    print("🧪 Testing Frontend Banner...")
    
    try:
        response = requests.get("http://localhost:3000/invoices", timeout=10)
        if response.status_code == 200:
            content = response.text
            if "Local AI unavailable" in content:
                print("⚠️  Frontend still shows 'Local AI unavailable' banner")
                return False
            else:
                print("✅ Frontend does not show LLM unavailable banner")
                return True
        else:
            print(f"❌ Frontend not accessible: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Frontend test failed: {e}")
        return False

def main():
    """Run LLM status tests"""
    print("🚀 Testing LLM Status and Banner...")
    print("=" * 50)
    
    # Test LLM functionality
    llm_working = test_llm_status()
    
    print("\n" + "=" * 50)
    
    # Test frontend banner
    banner_gone = test_frontend_banner()
    
    print("\n" + "=" * 50)
    print("📋 LLM Status Summary:")
    print(f"   LLM Working: {'✅' if llm_working else '❌'}")
    print(f"   Banner Gone: {'✅' if banner_gone else '❌'}")
    
    if llm_working and banner_gone:
        print("\n🎉 LLM is fully working! The banner should be gone.")
        print("   - Local AI is available and processing documents")
        print("   - Frontend should not show the 'unavailable' banner")
    elif llm_working and not banner_gone:
        print("\n⚠️  LLM is working but frontend may need refresh")
        print("   - Try refreshing the browser page")
        print("   - Check browser console for any errors")
    else:
        print("\n❌ LLM is not working properly")
        print("   - Check if Ollama is running with multimodal model")
        print("   - Verify QWEN_VL_MODEL_NAME environment variable")

if __name__ == "__main__":
    main() 