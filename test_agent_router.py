#!/usr/bin/env python3
"""
Test script for agent_router.py functionality.
"""

import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.agent.agent_router import (
    route_agent_task,
    route_agent_task_with_memory,
    route_specialized_task,
    suggest_credit,
    generate_email,
    escalate_issue
)

def test_basic_routing():
    """Test basic agent routing functionality."""
    print("🧪 Testing basic agent routing...")
    
    try:
        result = route_agent_task(
            user_prompt="What should I do about this invoice?",
            user_id="test_user",
            invoice_id="INV-73318",
            role="gm"
        )
        
        print(f"✅ Basic routing test completed")
        print(f"Response: {result.get('markdown', 'No response')[:100]}...")
        print(f"Actions: {len(result.get('actions', []))}")
        print(f"Confidence: {result.get('confidence', 0)}%")
        print(f"Urgency: {result.get('urgency', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic routing test failed: {e}")
        return False

def test_memory_routing():
    """Test agent routing with memory."""
    print("\n🧪 Testing agent routing with memory...")
    
    try:
        result = route_agent_task_with_memory(
            user_prompt="Can you help me with this flagged item?",
            user_id="test_user",
            invoice_id="INV-73318",
            role="gm"
        )
        
        print(f"✅ Memory routing test completed")
        print(f"Response: {result.get('markdown', 'No response')[:100]}...")
        print(f"Actions: {len(result.get('actions', []))}")
        print(f"Confidence: {result.get('confidence', 0)}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Memory routing test failed: {e}")
        return False

def test_specialized_tasks():
    """Test specialized task routing."""
    print("\n🧪 Testing specialized task routing...")
    
    try:
        # Test credit suggestion
        credit_result = suggest_credit("test_user", "INV-73318", "gm")
        print(f"✅ Credit suggestion test completed")
        print(f"Credit data: {credit_result.get('credit_data', {})}")
        
        # Test email generation
        email_result = generate_email("test_user", "INV-73318", "gm")
        print(f"✅ Email generation test completed")
        print(f"Email data: {email_result.get('email_data', {})}")
        
        # Test escalation
        escalation_result = escalate_issue("test_user", "INV-73318", "gm")
        print(f"✅ Escalation test completed")
        print(f"Escalation response: {escalation_result.get('markdown', 'No response')[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Specialized task test failed: {e}")
        return False

def test_different_roles():
    """Test routing with different user roles."""
    print("\n🧪 Testing different user roles...")
    
    roles = ["gm", "finance", "shift"]
    
    for role in roles:
        try:
            result = route_agent_task(
                user_prompt="How should I handle this invoice?",
                user_id=f"test_user_{role}",
                invoice_id="INV-73318",
                role=role
            )
            
            print(f"✅ {role.upper()} role test completed")
            print(f"Response: {result.get('markdown', 'No response')[:50]}...")
            
        except Exception as e:
            print(f"❌ {role.upper()} role test failed: {e}")
            return False
    
    return True

def test_error_handling():
    """Test error handling in agent routing."""
    print("\n🧪 Testing error handling...")
    
    try:
        # Test with invalid invoice ID
        result = route_agent_task(
            user_prompt="What should I do?",
            user_id="test_user",
            invoice_id="INVALID-INVOICE",
            role="gm"
        )
        
        print(f"✅ Error handling test completed")
        print(f"Error response: {result.get('markdown', 'No response')[:50]}...")
        print(f"Has error: {'error' in result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

def test_entities_extraction():
    """Test entity extraction from responses."""
    print("\n🧪 Testing entity extraction...")
    
    try:
        result = route_agent_task(
            user_prompt="The invoice from ABC Corporation shows £150.50 for tomatoes. What should I do?",
            user_id="test_user",
            invoice_id="INV-73318",
            role="gm"
        )
        
        entities = result.get('entities', {})
        print(f"✅ Entity extraction test completed")
        print(f"Suppliers: {entities.get('suppliers', [])}")
        print(f"Amounts: {entities.get('amounts', [])}")
        print(f"Items: {entities.get('items', [])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Entity extraction test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting agent router tests...")
    
    tests = [
        test_basic_routing,
        test_memory_routing,
        test_specialized_tasks,
        test_different_roles,
        test_error_handling,
        test_entities_extraction
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All agent router tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    exit(main()) 