"""
Agent Memory Module for Owlin Agent

Enables Owlin Agent to retain relevant context (active invoice, flagged items, 
supplier insights, etc.) across interactions. It ensures follow-up prompts are 
coherent and don't require repeating prior information.

This module provides a lightweight, in-memory context store using Python 
dictionaries. It is not persistent (clears on restart), but provides rich 
assistant experiences without cloud storage.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

# Global memory store
agent_memory = {}

def set_context(user_id: str, key: str, value: any) -> None:
    """
    Store a value under a key for a specific user.
    
    Args:
        user_id: Unique identifier for the user
        key: Context key to store the value under
        value: Value to store (can be any type)
    """
    if user_id not in agent_memory:
        agent_memory[user_id] = {}
    
    # Add timestamp for context tracking
    agent_memory[user_id][key] = {
        "value": value,
        "timestamp": datetime.now().isoformat(),
        "created_at": datetime.now().isoformat()
    }
    
    logger.info(f"💾 Stored context for user {user_id}: {key} = {type(value).__name__}")

def get_context(user_id: str, key: str) -> any:
    """
    Retrieve stored context by user and key.
    
    Args:
        user_id: Unique identifier for the user
        key: Context key to retrieve
        
    Returns:
        Stored value or None if not found
    """
    user_context = agent_memory.get(user_id, {})
    context_data = user_context.get(key)
    
    if context_data:
        # Return just the value, not the metadata
        return context_data.get("value")
    
    return None

def get_context_with_metadata(user_id: str, key: str) -> Optional[Dict]:
    """
    Retrieve stored context with metadata (timestamp, etc.).
    
    Args:
        user_id: Unique identifier for the user
        key: Context key to retrieve
        
    Returns:
        Dictionary with value and metadata, or None if not found
    """
    user_context = agent_memory.get(user_id, {})
    return user_context.get(key)

def clear_context(user_id: str, key: str = None) -> None:
    """
    Clear context for a user. Optionally clear just one key.
    
    Args:
        user_id: Unique identifier for the user
        key: Optional specific key to clear. If None, clears all user context
    """
    if user_id in agent_memory:
        if key:
            if key in agent_memory[user_id]:
                del agent_memory[user_id][key]
                logger.info(f"🗑️ Cleared context for user {user_id}: {key}")
        else:
            agent_memory[user_id] = {}
            logger.info(f"🗑️ Cleared all context for user {user_id}")

def get_all_context(user_id: str) -> Dict[str, Any]:
    """
    Get all context for a specific user.
    
    Args:
        user_id: Unique identifier for the user
        
    Returns:
        Dictionary of all stored context for the user
    """
    return agent_memory.get(user_id, {})

def set_invoice_context(user_id: str, invoice_id: str, invoice_data: Dict = None) -> None:
    """
    Set context for an active invoice.
    
    Args:
        user_id: Unique identifier for the user
        invoice_id: Invoice identifier
        invoice_data: Optional invoice data to store
    """
    set_context(user_id, "active_invoice_id", invoice_id)
    if invoice_data:
        set_context(user_id, "active_invoice_data", invoice_data)
    
    logger.info(f"📄 Set active invoice context for user {user_id}: {invoice_id}")

def get_active_invoice(user_id: str) -> Optional[str]:
    """
    Get the currently active invoice ID for a user.
    
    Args:
        user_id: Unique identifier for the user
        
    Returns:
        Active invoice ID or None
    """
    return get_context(user_id, "active_invoice_id")

def set_flagged_item_context(user_id: str, item_data: Dict) -> None:
    """
    Set context for a flagged item being reviewed.
    
    Args:
        user_id: Unique identifier for the user
        item_data: Dictionary containing flagged item information
    """
    set_context(user_id, "active_flagged_item", item_data)
    logger.info(f"🚩 Set flagged item context for user {user_id}: {item_data.get('item', 'Unknown')}")

def get_flagged_item_context(user_id: str) -> Optional[Dict]:
    """
    Get the currently active flagged item for a user.
    
    Args:
        user_id: Unique identifier for the user
        
    Returns:
        Flagged item data or None
    """
    return get_context(user_id, "active_flagged_item")

def set_supplier_context(user_id: str, supplier_name: str, supplier_data: Dict = None) -> None:
    """
    Set context for a supplier being reviewed.
    
    Args:
        user_id: Unique identifier for the user
        supplier_name: Name of the supplier
        supplier_data: Optional supplier performance data
    """
    set_context(user_id, "active_supplier", supplier_name)
    if supplier_data:
        set_context(user_id, "active_supplier_data", supplier_data)
    
    logger.info(f"🏭 Set supplier context for user {user_id}: {supplier_name}")

def get_supplier_context(user_id: str) -> Optional[str]:
    """
    Get the currently active supplier for a user.
    
    Args:
        user_id: Unique identifier for the user
        
    Returns:
        Active supplier name or None
    """
    return get_context(user_id, "active_supplier")

def set_user_role_context(user_id: str, role: str) -> None:
    """
    Set the user's role context.
    
    Args:
        user_id: Unique identifier for the user
        role: User role (Finance, GM, Shift Lead, etc.)
    """
    set_context(user_id, "user_role", role)
    logger.info(f"👤 Set user role context for user {user_id}: {role}")

def get_user_role_context(user_id: str) -> Optional[str]:
    """
    Get the user's role context.
    
    Args:
        user_id: Unique identifier for the user
        
    Returns:
        User role or None
    """
    return get_context(user_id, "user_role")

def add_conversation_history(user_id: str, message: str, response: str = None) -> None:
    """
    Add a conversation entry to the user's history.
    
    Args:
        user_id: Unique identifier for the user
        message: User's message
        response: Optional agent response
    """
    history = get_context(user_id, "conversation_history") or []
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "message": message,
        "response": response
    }
    
    history.append(entry)
    
    # Keep only last 10 conversations to prevent memory bloat
    if len(history) > 10:
        history = history[-10:]
    
    set_context(user_id, "conversation_history", history)
    logger.info(f"💬 Added conversation history for user {user_id}")

def get_conversation_history(user_id: str, limit: int = 5) -> List[Dict]:
    """
    Get recent conversation history for a user.
    
    Args:
        user_id: Unique identifier for the user
        limit: Maximum number of recent conversations to return
        
    Returns:
        List of recent conversation entries
    """
    history = get_context(user_id, "conversation_history") or []
    return history[-limit:] if limit else history

def set_workflow_state(user_id: str, workflow: str, state: str, data: Dict = None) -> None:
    """
    Set the current workflow state for a user.
    
    Args:
        user_id: Unique identifier for the user
        workflow: Workflow name (e.g., "invoice_review", "credit_request")
        state: Current state in the workflow
        data: Optional workflow-specific data
    """
    workflow_data = {
        "workflow": workflow,
        "state": state,
        "data": data or {},
        "timestamp": datetime.now().isoformat()
    }
    
    set_context(user_id, "current_workflow", workflow_data)
    logger.info(f"🔄 Set workflow state for user {user_id}: {workflow} -> {state}")

def get_workflow_state(user_id: str) -> Optional[Dict]:
    """
    Get the current workflow state for a user.
    
    Args:
        user_id: Unique identifier for the user
        
    Returns:
        Current workflow state or None
    """
    return get_context(user_id, "current_workflow")

def clear_workflow_state(user_id: str) -> None:
    """
    Clear the current workflow state for a user.
    
    Args:
        user_id: Unique identifier for the user
    """
    clear_context(user_id, "current_workflow")
    logger.info(f"🔄 Cleared workflow state for user {user_id}")

def set_preference(user_id: str, preference_key: str, preference_value: any) -> None:
    """
    Set a user preference.
    
    Args:
        user_id: Unique identifier for the user
        preference_key: Preference key
        preference_value: Preference value
    """
    preferences = get_context(user_id, "user_preferences") or {}
    preferences[preference_key] = preference_value
    set_context(user_id, "user_preferences", preferences)
    logger.info(f"⚙️ Set preference for user {user_id}: {preference_key}")

def get_preference(user_id: str, preference_key: str, default: any = None) -> any:
    """
    Get a user preference.
    
    Args:
        user_id: Unique identifier for the user
        preference_key: Preference key
        default: Default value if preference not found
        
    Returns:
        Preference value or default
    """
    preferences = get_context(user_id, "user_preferences") or {}
    return preferences.get(preference_key, default)

def get_all_preferences(user_id: str) -> Dict[str, Any]:
    """
    Get all user preferences.
    
    Args:
        user_id: Unique identifier for the user
        
    Returns:
        Dictionary of all user preferences
    """
    return get_context(user_id, "user_preferences") or {}

def set_temporary_context(user_id: str, key: str, value: any, ttl_seconds: int = 300) -> None:
    """
    Set context with a time-to-live (TTL) that automatically expires.
    
    Args:
        user_id: Unique identifier for the user
        key: Context key
        value: Value to store
        ttl_seconds: Time to live in seconds (default: 5 minutes)
    """
    expiry_time = datetime.now() + timedelta(seconds=ttl_seconds)
    
    context_data = {
        "value": value,
        "timestamp": datetime.now().isoformat(),
        "expires_at": expiry_time.isoformat(),
        "ttl_seconds": ttl_seconds
    }
    
    if user_id not in agent_memory:
        agent_memory[user_id] = {}
    
    agent_memory[user_id][key] = context_data
    logger.info(f"⏰ Set temporary context for user {user_id}: {key} (expires in {ttl_seconds}s)")

def cleanup_expired_context() -> int:
    """
    Clean up expired temporary context entries.
    
    Returns:
        Number of expired entries removed
    """
    removed_count = 0
    current_time = datetime.now()
    
    for user_id in list(agent_memory.keys()):
        user_context = agent_memory[user_id]
        expired_keys = []
        
        for key, context_data in user_context.items():
            if isinstance(context_data, dict) and "expires_at" in context_data:
                try:
                    expiry_time = datetime.fromisoformat(context_data["expires_at"])
                    if current_time > expiry_time:
                        expired_keys.append(key)
                except ValueError:
                    # Invalid timestamp, remove it
                    expired_keys.append(key)
        
        for key in expired_keys:
            del user_context[key]
            removed_count += 1
        
        # Remove empty user contexts
        if not user_context:
            del agent_memory[user_id]
    
    if removed_count > 0:
        logger.info(f"🧹 Cleaned up {removed_count} expired context entries")
    
    return removed_count

def get_memory_stats() -> Dict[str, Any]:
    """
    Get statistics about the agent memory usage.
    
    Returns:
        Dictionary with memory statistics
    """
    total_users = len(agent_memory)
    total_entries = sum(len(user_context) for user_context in agent_memory.values())
    
    # Count temporary entries
    temporary_entries = 0
    for user_context in agent_memory.values():
        for context_data in user_context.values():
            if isinstance(context_data, dict) and "expires_at" in context_data:
                temporary_entries += 1
    
    stats = {
        "total_users": total_users,
        "total_entries": total_entries,
        "temporary_entries": temporary_entries,
        "permanent_entries": total_entries - temporary_entries,
        "memory_size_mb": len(str(agent_memory)) / (1024 * 1024)  # Rough estimate
    }
    
    return stats

def export_user_context(user_id: str) -> Dict[str, Any]:
    """
    Export all context for a specific user (for debugging/migration).
    
    Args:
        user_id: Unique identifier for the user
        
    Returns:
        Dictionary containing all user context
    """
    user_context = agent_memory.get(user_id, {})
    
    # Convert to serializable format
    export_data = {}
    for key, context_data in user_context.items():
        if isinstance(context_data, dict) and "value" in context_data:
            export_data[key] = {
                "value": context_data["value"],
                "timestamp": context_data.get("timestamp"),
                "expires_at": context_data.get("expires_at")
            }
        else:
            export_data[key] = context_data
    
    return {
        "user_id": user_id,
        "export_timestamp": datetime.now().isoformat(),
        "context": export_data
    }

def import_user_context(user_id: str, context_data: Dict[str, Any]) -> bool:
    """
    Import context for a specific user (for debugging/migration).
    
    Args:
        user_id: Unique identifier for the user
        context_data: Context data to import
        
    Returns:
        True if import successful, False otherwise
    """
    try:
        if "context" in context_data:
            for key, value in context_data["context"].items():
                if isinstance(value, dict) and "value" in value:
                    # Handle exported format
                    set_context(user_id, key, value["value"])
                else:
                    # Handle direct value
                    set_context(user_id, key, value)
        
        logger.info(f"📥 Imported context for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to import context for user {user_id}: {e}")
        return False

def get_invoice_context(invoice_id: str) -> Optional[Dict[str, Any]]:
    """
    Get comprehensive context for a specific invoice.
    
    Args:
        invoice_id: The invoice ID to get context for
        
    Returns:
        Dictionary containing invoice context or None if not found
    """
    try:
        # This would typically query the database for invoice data
        # For now, we'll return a mock structure
        # In a real implementation, this would fetch from the database
        
        # Mock invoice context structure
        invoice_context = {
            "invoice": {
                "id": invoice_id,
                "supplier_name": "ABC Corporation",
                "invoice_number": f"INV-{invoice_id[-5:]}",
                "invoice_date": "2024-01-15",
                "total_amount": 150.50,
                "subtotal": 125.00,
                "vat": 25.50,
                "status": "flagged"
            },
            "flagged_items": [
                {
                    "item_name": "Tomatoes",
                    "expected_price": 2.50,
                    "actual_price": 2.80,
                    "difference": 0.30,
                    "quantity": 10
                }
            ],
            "supplier": {
                "name": "ABC Corporation",
                "rating": 4.2,
                "total_spend": 5000.00,
                "contact_email": "accounts@abc-corp.com"
            },
            "workflow": {
                "state": "review_required",
                "assigned_to": "gm",
                "priority": "medium"
            }
        }
        
        logger.debug(f"📄 Retrieved invoice context for {invoice_id}")
        return invoice_context
        
    except Exception as e:
        logger.error(f"❌ Error getting invoice context for {invoice_id}: {str(e)}")
        return None

def clear_all_memory() -> None:
    """
    Clear all agent memory (use with caution).
    """
    global agent_memory
    agent_memory = {}
    logger.warning("🗑️ Cleared all agent memory")


if __name__ == "__main__":
    # Test the agent memory module
    logging.basicConfig(level=logging.INFO)
    
    print("🧠 Agent Memory Module Test Results:")
    
    # Test basic context operations
    user_id = "test_user_1"
    
    # Test 1: Set and get context
    set_context(user_id, "active_invoice_id", "INV-73318")
    invoice_id = get_context(user_id, "active_invoice_id")
    print(f"\n1. Basic context: {invoice_id}")
    
    # Test 2: Set invoice context
    invoice_data = {
        "supplier_name": "Brakes Catering",
        "total_amount": 146.75,
        "flagged_items": 2
    }
    set_invoice_context(user_id, "INV-73318", invoice_data)
    active_invoice = get_active_invoice(user_id)
    print(f"2. Active invoice: {active_invoice}")
    
    # Test 3: Set flagged item context
    flagged_item = {
        "item": "Coca-Cola 330ml",
        "issue": "Short delivery",
        "quantity_expected": 24,
        "quantity_received": 20
    }
    set_flagged_item_context(user_id, flagged_item)
    current_item = get_flagged_item_context(user_id)
    print(f"3. Flagged item: {current_item['item'] if current_item else 'None'}")
    
    # Test 4: Set supplier context
    set_supplier_context(user_id, "Brakes Catering")
    supplier = get_supplier_context(user_id)
    print(f"4. Active supplier: {supplier}")
    
    # Test 5: Set user role
    set_user_role_context(user_id, "Finance")
    role = get_user_role_context(user_id)
    print(f"5. User role: {role}")
    
    # Test 6: Add conversation history
    add_conversation_history(user_id, "What should I do about this invoice?", "You can generate a credit email.")
    history = get_conversation_history(user_id)
    print(f"6. Conversation history: {len(history)} entries")
    
    # Test 7: Set workflow state
    set_workflow_state(user_id, "invoice_review", "reviewing_flagged_items", {"current_item": 1, "total_items": 2})
    workflow = get_workflow_state(user_id)
    print(f"7. Workflow state: {workflow['workflow']} -> {workflow['state']}")
    
    # Test 8: Set preferences
    set_preference(user_id, "email_templates", True)
    set_preference(user_id, "auto_suggestions", False)
    email_templates = get_preference(user_id, "email_templates", False)
    print(f"8. Email templates preference: {email_templates}")
    
    # Test 9: Set temporary context
    set_temporary_context(user_id, "temp_analysis", {"confidence": 85.0}, 60)
    temp_data = get_context(user_id, "temp_analysis")
    print(f"9. Temporary context: {temp_data is not None}")
    
    # Test 10: Get memory stats
    stats = get_memory_stats()
    print(f"10. Memory stats: {stats['total_users']} users, {stats['total_entries']} entries")
    
    # Test 11: Export context
    export_data = export_user_context(user_id)
    print(f"11. Export data: {len(export_data['context'])} context entries")
    
    # Test 12: Clear specific context
    clear_context(user_id, "active_invoice_id")
    cleared_invoice = get_context(user_id, "active_invoice_id")
    print(f"12. Cleared invoice context: {cleared_invoice is None}")
    
    # Test 13: Cleanup expired context
    removed = cleanup_expired_context()
    print(f"13. Cleaned up {removed} expired entries")
    
    print("\n✅ Test completed successfully") 