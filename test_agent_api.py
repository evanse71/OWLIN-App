#!/usr/bin/env python3
"""
Test script for agent API endpoints.
"""

import requests
import json
import time

# API base URL
BASE_URL = "http://localhost:8000/api"

def test_agent_health():
    """Test agent health check endpoint."""
    print("🏥 Testing agent health check...")
    
    try:
        response = requests.get(f"{BASE_URL}/agent/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_agent_capabilities():
    """Test agent capabilities endpoint."""
    print("\n🔧 Testing agent capabilities...")
    
    try:
        response = requests.get(f"{BASE_URL}/agent/capabilities")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Capabilities: {data}")
            return True
        else:
            print(f"❌ Capabilities failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Capabilities error: {e}")
        return False

def test_agent_ask():
    """Test main agent ask endpoint."""
    print("\n🤖 Testing agent ask endpoint...")
    
    payload = {
        "user_prompt": "What should I do about this invoice?",
        "user_id": "test_user_123",
        "invoice_id": "INV-73318",
        "role": "gm"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/agent/ask", json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Agent response: {data.get('markdown', 'No response')[:100]}...")
            print(f"Confidence: {data.get('confidence', 0)}%")
            print(f"Actions: {len(data.get('actions', []))}")
            return True
        else:
            print(f"❌ Agent ask failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Agent ask error: {e}")
        return False

def test_agent_ask_with_memory():
    """Test agent ask with memory endpoint."""
    print("\n🧠 Testing agent ask with memory...")
    
    payload = {
        "user_prompt": "Can you help me with this flagged item?",
        "user_id": "test_user_123",
        "invoice_id": "INV-73318",
        "role": "gm"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/agent/ask-with-memory", json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Agent response with memory: {data.get('markdown', 'No response')[:100]}...")
            return True
        else:
            print(f"❌ Agent ask with memory failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Agent ask with memory error: {e}")
        return False

def test_specialized_tasks():
    """Test specialized agent tasks."""
    print("\n🎯 Testing specialized tasks...")
    
    # Test credit suggestion
    payload = {
        "user_prompt": "Suggest a credit for this invoice",
        "user_id": "test_user_123",
        "invoice_id": "INV-73318",
        "role": "gm",
        "task_type": "credit_suggestion"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/agent/specialized", json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Credit suggestion: {data.get('markdown', 'No response')[:50]}...")
        else:
            print(f"❌ Credit suggestion failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Credit suggestion error: {e}")
        return False
    
    return True

def test_convenience_endpoints():
    """Test convenience endpoints."""
    print("\n⚡ Testing convenience endpoints...")
    
    base_payload = {
        "user_id": "test_user_123",
        "invoice_id": "INV-73318",
        "role": "gm"
    }
    
    endpoints = [
        ("/agent/suggest-credit", "Credit suggestion"),
        ("/agent/generate-email", "Email generation"),
        ("/agent/escalate", "Issue escalation")
    ]
    
    for endpoint, description in endpoints:
        try:
            response = requests.post(f"{BASE_URL}{endpoint}", json=base_payload)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {description}: {data.get('markdown', 'No response')[:50]}...")
            else:
                print(f"❌ {description} failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ {description} error: {e}")
            return False
    
    return True

def test_different_roles():
    """Test agent with different user roles."""
    print("\n👥 Testing different user roles...")
    
    roles = ["gm", "finance", "shift"]
    
    for role in roles:
        payload = {
            "user_prompt": "How should I handle this invoice?",
            "user_id": f"test_user_{role}",
            "invoice_id": "INV-73318",
            "role": role
        }
        
        try:
            response = requests.post(f"{BASE_URL}/agent/ask", json=payload)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {role.upper()} role: {data.get('markdown', 'No response')[:50]}...")
            else:
                print(f"❌ {role.upper()} role failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ {role.upper()} role error: {e}")
            return False
    
    return True

def test_error_handling():
    """Test error handling in agent endpoints."""
    print("\n⚠️ Testing error handling...")
    
    # Test with invalid data
    payload = {
        "user_prompt": "Test",
        "user_id": "test_user",
        "invoice_id": "INVALID-INVOICE",
        "role": "invalid_role"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/agent/ask", json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Error handling: {data.get('markdown', 'No response')[:50]}...")
            return True
        else:
            print(f"❌ Error handling failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error handling error: {e}")
        return False

def main():
    """Run all agent API tests."""
    print("🚀 Starting agent API tests...")
    
    # Wait a moment for server to be ready
    time.sleep(1)
    
    tests = [
        test_agent_health,
        test_agent_capabilities,
        test_agent_ask,
        test_agent_ask_with_memory,
        test_specialized_tasks,
        test_convenience_endpoints,
        test_different_roles,
        test_error_handling
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All agent API tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    exit(main()) 