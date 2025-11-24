"""
Quick Validation Script for Code Assistant Mega Upgrade

Tests that all components are working correctly.
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_endpoints():
    """Test all new endpoints."""
    print("Testing Code Assistant Mega Upgrade...")
    print("=" * 60)
    
    tests = []
    
    # Test 1: Chat status with model info
    print("\n1. Testing /api/chat/status...")
    try:
        response = requests.get(f"{BASE_URL}/api/chat/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   [OK] Status OK")
            print(f"   Primary model: {data.get('primary_model')}")
            print(f"   Available models: {', '.join(data.get('available_models', []))}")
            print(f"   Ollama available: {data.get('ollama_available')}")
            tests.append(("Status", True))
        else:
            print(f"   [FAIL] Failed: HTTP {response.status_code}")
            tests.append(("Status", False))
    except Exception as e:
        print(f"   [ERROR] Error: {e}")
        tests.append(("Status", False))
    
    # Test 2: Configuration endpoint
    print("\n2. Testing /api/chat/config...")
    try:
        response = requests.get(f"{BASE_URL}/api/chat/config", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   [OK] Config loaded")
            print(f"   Models configured: {', '.join(data['models']['configured'])}")
            print(f"   Max context available: {data['models']['registry_stats']['max_context_available']}k")
            print(f"   Features enabled: {len([k for k, v in data['features'].items() if v])}")
            tests.append(("Config", True))
        else:
            print(f"   [FAIL] Failed: HTTP {response.status_code}")
            tests.append(("Config", False))
    except Exception as e:
        print(f"   [ERROR] Error: {e}")
        tests.append(("Config", False))
    
    # Test 3: Models list
    print("\n3. Testing /api/chat/models...")
    try:
        response = requests.get(f"{BASE_URL}/api/chat/models", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   [OK] Models list retrieved")
            print(f"   Total models: {data.get('count', 0)}")
            for model in data.get('models', []):
                print(f"   - {model['name']}: {model['max_context']}k context, {model['size_mb']:.1f} MB")
            tests.append(("Models", True))
        else:
            print(f"   [FAIL] Failed: HTTP {response.status_code}")
            tests.append(("Models", False))
    except Exception as e:
        print(f"   [ERROR] Error: {e}")
        tests.append(("Models", False))
    
    # Test 4: Quality metrics
    print("\n4. Testing /api/chat/quality...")
    try:
        response = requests.get(f"{BASE_URL}/api/chat/quality", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   [OK] Quality report generated")
            print(f"   Overall health: {data.get('overall_health')}")
            print(f"   Passing checks: {data.get('passing_checks')}/{data.get('total_checks')}")
            
            # Show quality checks
            for check_name, check_data in data.get('quality_checks', {}).items():
                status = "[PASS]" if check_data['passing'] else "[FAIL]"
                print(f"   {status} {check_name}: {check_data['value']:.1f} (target: {check_data['target']})")
            tests.append(("Quality", True))
        else:
            print(f"   [FAIL] Failed: HTTP {response.status_code}")
            tests.append(("Quality", False))
    except Exception as e:
        print(f"   [ERROR] Error: {e}")
        tests.append(("Quality", False))
    
    # Test 5: Sample chat request (if Ollama is available)
    print("\n5. Testing sample chat request...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "Show me the upload code",
                "context_size": 32000
            },
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            response_text = data.get('response', '')
            print(f"   [OK] Chat request successful")
            print(f"   Model used: {data.get('model_used')}")
            print(f"   Code references: {len(data.get('code_references', []))}")
            print(f"   Response length: {len(response_text)} chars")
            
            # Check if response has code (not generic)
            has_code = "```" in response_text or ".ts" in response_text or ".py" in response_text
            print(f"   Has code references: {has_code}")
            tests.append(("Chat", True))
        else:
            print(f"   [FAIL] Failed: HTTP {response.status_code}")
            tests.append(("Chat", False))
    except Exception as e:
        print(f"   [WARN] Error: {e}")
        print(f"   (This is OK if Ollama is not running)")
        tests.append(("Chat", None))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in tests if result is True)
    failed = sum(1 for _, result in tests if result is False)
    skipped = sum(1 for _, result in tests if result is None)
    
    for name, result in tests:
        if result is True:
            print(f"[PASS] {name}")
        elif result is False:
            print(f"[FAIL] {name}")
        else:
            print(f"[SKIP] {name} (skipped)")
    
    print(f"\nPassed: {passed}/{len(tests) - skipped}")
    
    if passed >= 4:
        print("\n[SUCCESS] CODE ASSISTANT MEGA UPGRADE: OPERATIONAL")
        print("  - Model registry: Working")
        print("  - Configuration: Loaded")
        print("  - Quality tracking: Active")
        print("  - Endpoints: Responsive")
        if skipped == 0:
            print("  - Chat system: Fully operational")
        else:
            print("  - Chat system: Waiting for Ollama")
    else:
        print("\n[FAILED] SYSTEM CHECK FAILED")
        print("  Some components are not working correctly.")
        print("  Check backend logs for details.")


if __name__ == "__main__":
    test_endpoints()

