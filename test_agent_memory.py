#!/usr/bin/env python3
"""
Test script for agent_memory.py functionality.
"""

import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.agent.agent_memory import (
    set_context, 
    get_context, 
    clear_context,
    set_invoice_context,
    get_active_invoice,
    set_flagged_item_context,
    get_flagged_item_context,
    set_supplier_context,
    get_supplier_context,
    set_user_role_context,
    get_user_role_context,
    get_all_context,
    clear_all_memory
)

def test_basic_functionality():
    """Test the basic memory functions."""
    print("🧪 Testing basic agent memory functionality...")
    
    # Test 1: Set and get context
    print("\n1. Testing set_context and get_context...")
    set_context("user_1", "active_invoice_id", "INV-73318")
    result = get_context("user_1", "active_invoice_id")
    print(f"   Set: 'INV-73318'")
    print(f"   Got: '{result}'")
    assert result == "INV-73318", f"Expected 'INV-73318', got '{result}'"
    print("   ✅ Basic context storage works")

    # Test 2: Clear specific context
    print("\n2. Testing clear_context with specific key...")
    clear_context("user_1", "active_invoice_id")
    result = get_context("user_1", "active_invoice_id")
    print(f"   After clear: {result}")
    assert result is None, f"Expected None, got '{result}'"
    print("   ✅ Clear specific context works")

    # Test 3: Clear all context
    print("\n3. Testing clear_context for all user context...")
    set_context("user_1", "test_key", "test_value")
    set_context("user_1", "another_key", "another_value")
    print(f"   Before clear: {get_all_context('user_1')}")
    clear_context("user_1")  # Clear all context
    result = get_all_context("user_1")
    print(f"   After clear: {result}")
    assert result == {}, f"Expected empty dict, got {result}"
    print("   ✅ Clear all context works")

def test_specialized_functions():
    """Test the specialized memory functions."""
    print("\n🧪 Testing specialized agent memory functions...")
    
    # Test 1: Invoice context
    print("\n1. Testing invoice context...")
    set_invoice_context("user_1", "INV-73318", {"amount": 150.50, "supplier": "ABC Corp"})
    invoice_id = get_active_invoice("user_1")
    print(f"   Active invoice: '{invoice_id}'")
    assert invoice_id == "INV-73318", f"Expected 'INV-73318', got '{invoice_id}'"
    print("   ✅ Invoice context works")

    # Test 2: Flagged item context
    print("\n2. Testing flagged item context...")
    flagged_item = {
        "item": "Tomatoes",
        "expected_price": 2.50,
        "actual_price": 2.80,
        "difference": 0.30
    }
    set_flagged_item_context("user_1", flagged_item)
    retrieved_item = get_flagged_item_context("user_1")
    print(f"   Flagged item: {retrieved_item}")
    assert retrieved_item == flagged_item, f"Expected {flagged_item}, got {retrieved_item}"
    print("   ✅ Flagged item context works")

    # Test 3: Supplier context
    print("\n3. Testing supplier context...")
    set_supplier_context("user_1", "ABC Corp", {"rating": 4.5, "total_spend": 5000})
    supplier = get_supplier_context("user_1")
    print(f"   Active supplier: '{supplier}'")
    assert supplier == "ABC Corp", f"Expected 'ABC Corp', got '{supplier}'"
    print("   ✅ Supplier context works")

    # Test 4: User role context
    print("\n4. Testing user role context...")
    set_user_role_context("user_1", "GM")
    role = get_user_role_context("user_1")
    print(f"   User role: '{role}'")
    assert role == "GM", f"Expected 'GM', got '{role}'"
    print("   ✅ User role context works")

def test_example_usage():
    """Test the example usage from the requirements."""
    print("\n🧪 Testing example usage scenario...")
    
    # Example 1: User opens an invoice and flags a mismatch
    print("\n1. User opens an invoice and flags a mismatch...")
    set_context("user_1", "active_invoice_id", "INV-73318")
    result = get_context("user_1", "active_invoice_id")
    print(f"   Active invoice: '{result}'")
    assert result == "INV-73318", f"Expected 'INV-73318', got '{result}'"
    
    # Example 2: Agent later needs to reference that
    print("\n2. Agent later needs to reference that...")
    active_invoice = get_context("user_1", "active_invoice_id")
    print(f"   Retrieved: '{active_invoice}'")
    assert active_invoice == "INV-73318", f"Expected 'INV-73318', got '{active_invoice}'"
    
    # Example 3: After resolution
    print("\n3. After resolution...")
    clear_context("user_1", "active_invoice_id")
    result = get_context("user_1", "active_invoice_id")
    print(f"   After clear: {result}")
    assert result is None, f"Expected None, got '{result}'"
    print("   ✅ Example usage works correctly")

def test_user_flow_scenario():
    """Test the user flow scenario from the requirements."""
    print("\n🧪 Testing user flow scenario...")
    
    # The GM clicks on a flagged invoice issue and asks "What should I do here?"
    print("\nScenario: GM clicks on flagged invoice issue...")
    
    # Set up the context
    set_context("gm_user", "active_invoice_id", "INV-73318")
    set_flagged_item_context("gm_user", {
        "item": "Tomatoes",
        "expected_price": 2.50,
        "actual_price": 2.80,
        "difference": 0.30,
        "issue_type": "overcharge"
    })
    set_user_role_context("gm_user", "GM")
    
    # Simulate agent consulting memory
    active_invoice = get_context("gm_user", "active_invoice_id")
    flagged_item = get_flagged_item_context("gm_user")
    user_role = get_user_role_context("gm_user")
    
    print(f"   Active invoice: {active_invoice}")
    print(f"   Flagged item: {flagged_item}")
    print(f"   User role: {user_role}")
    
    # Simulate agent response
    if active_invoice and flagged_item and user_role == "GM":
        difference = flagged_item.get("difference", 0)
        item_name = flagged_item.get("item", "item")
        print(f"   Agent response: This {item_name} was overcharged by £{difference:.2f}. You could generate an email or flag for escalation.")
        print("   ✅ User flow scenario works correctly")
    else:
        print("   ❌ User flow scenario failed - missing context")

def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n🧪 Testing edge cases...")
    
    # Test 1: Get context for non-existent user
    print("\n1. Testing non-existent user...")
    result = get_context("non_existent_user", "some_key")
    print(f"   Result: {result}")
    assert result is None, f"Expected None for non-existent user, got '{result}'"
    print("   ✅ Non-existent user handled correctly")
    
    # Test 2: Get context for non-existent key
    print("\n2. Testing non-existent key...")
    result = get_context("user_1", "non_existent_key")
    print(f"   Result: {result}")
    assert result is None, f"Expected None for non-existent key, got '{result}'"
    print("   ✅ Non-existent key handled correctly")
    
    # Test 3: Clear context for non-existent user
    print("\n3. Testing clear for non-existent user...")
    try:
        clear_context("non_existent_user", "some_key")
        print("   ✅ Clear for non-existent user handled gracefully")
    except Exception as e:
        print(f"   ❌ Error clearing non-existent user: {e}")
    
    # Test 4: Set context with None value
    print("\n4. Testing set context with None value...")
    set_context("user_1", "none_key", None)
    result = get_context("user_1", "none_key")
    print(f"   Result: {result}")
    assert result is None, f"Expected None, got '{result}'"
    print("   ✅ None value handled correctly")

def test_memory_persistence():
    """Test that memory persists across multiple operations."""
    print("\n🧪 Testing memory persistence...")
    
    # Set multiple contexts
    set_context("persist_user", "key1", "value1")
    set_context("persist_user", "key2", "value2")
    set_context("persist_user", "key3", "value3")
    
    # Verify all contexts are stored
    all_context = get_all_context("persist_user")
    print(f"   All context: {all_context}")
    assert len(all_context) == 3, f"Expected 3 context items, got {len(all_context)}"
    
    # Verify individual contexts
    assert get_context("persist_user", "key1") == "value1"
    assert get_context("persist_user", "key2") == "value2"
    assert get_context("persist_user", "key3") == "value3"
    
    print("   ✅ Memory persistence works correctly")

def main():
    """Run all tests."""
    print("🚀 Starting agent memory tests...")
    
    try:
        test_basic_functionality()
        test_specialized_functions()
        test_example_usage()
        test_user_flow_scenario()
        test_edge_cases()
        test_memory_persistence()
        
        # Clean up
        clear_all_memory()
        
        print("\n🎉 All tests passed! Agent memory module is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 