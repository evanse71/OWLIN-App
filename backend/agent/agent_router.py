"""
Agent Router Module

The command hub that coordinates all agent activity in Owlin.
This module uses helper modules to process user prompts, fetch invoice context, 
generate agent responses, and return structured output for the frontend.
"""

import logging
from typing import Dict, Any, Optional
from .agent_prompt_builder import build_prompt
from .agent_memory import get_invoice_context, get_context, set_context
from .agent_client import call_agent_model
from .agent_response_parser import parse_agent_response

logger = logging.getLogger(__name__)

def route_agent_task(
    user_prompt: str, 
    user_id: str, 
    invoice_id: str, 
    role: str
) -> Dict[str, Any]:
    """
    Main router for handling agent prompts. This function:
    - Retrieves invoice context and role
    - Builds a role-aware agent prompt
    - Calls the agent model (OpenAI or HuggingFace)
    - Parses the response into structured output
    
    Args:
        user_prompt: Raw question or command from user
        user_id: Active user ID (used to load memory if needed)
        invoice_id: Current invoice the user is looking at
        role: 'gm', 'finance', or 'shift'
    
    Returns:
        Dictionary with fields:
        - markdown: original agent response
        - actions: optional actions (e.g. suggest_credit, escalate)
        - confidence: estimated confidence score (0–100)
        - entities: extracted entities (suppliers, amounts, etc.)
        - urgency: urgency level (low, medium, high)
    """
    try:
        logger.info(f"🔄 Routing agent task for user {user_id}, invoice {invoice_id}, role {role}")
        
        # Step 1: Get invoice context from memory/db
        invoice_context = get_invoice_context(invoice_id)
        if not invoice_context:
            logger.warning(f"⚠️ No invoice context found for {invoice_id}")
            invoice_context = {}
        
        # Step 2: Get user-specific context from memory
        user_context = _get_user_context(user_id)
        if user_context:
            invoice_context.update(user_context)
        
        # Step 3: Build full prompt with user message + context
        full_prompt = build_prompt(user_prompt, context=invoice_context, role=role)
        
        # Step 4: Call agent model and get raw markdown response
        raw_response = call_agent_model(full_prompt)
        
        # Step 5: Parse structured data from response
        result = parse_agent_response(raw_response)
        
        # Step 6: Store conversation in memory
        _store_conversation(user_id, user_prompt, raw_response)
        
        logger.info(f"✅ Agent task completed successfully for user {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in agent routing: {str(e)}")
        return _create_error_response(user_prompt, str(e))

def route_agent_task_with_memory(
    user_prompt: str, 
    user_id: str, 
    invoice_id: str, 
    role: str
) -> Dict[str, Any]:
    """
    Enhanced router that includes conversation history and memory.
    
    Args:
        user_prompt: Raw question or command from user
        user_id: Active user ID
        invoice_id: Current invoice the user is looking at
        role: User role ('gm', 'finance', 'shift')
    
    Returns:
        Dictionary with structured response
    """
    try:
        logger.info(f"🧠 Routing agent task with memory for user {user_id}")
        
        # Get conversation history
        from .agent_memory import get_conversation_history
        conversation_history = get_conversation_history(user_id, limit=5)
        
        # Get invoice context
        invoice_context = get_invoice_context(invoice_id) or {}
        
        # Get user context
        user_context = _get_user_context(user_id)
        if user_context:
            invoice_context.update(user_context)
        
        # Build prompt with conversation history
        from .agent_prompt_builder import build_conversation_prompt
        full_prompt = build_conversation_prompt(
            user_prompt, 
            conversation_history, 
            context=invoice_context, 
            role=role
        )
        
        # Call agent model
        raw_response = call_agent_model(full_prompt)
        
        # Parse response
        result = parse_agent_response(raw_response)
        
        # Store conversation
        _store_conversation(user_id, user_prompt, raw_response)
        
        logger.info(f"✅ Agent task with memory completed for user {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in agent routing with memory: {str(e)}")
        return _create_error_response(user_prompt, str(e))

def route_specialized_task(
    task_type: str,
    user_prompt: str,
    user_id: str,
    invoice_id: str,
    role: str
) -> Dict[str, Any]:
    """
    Route specialized tasks like credit suggestions, email generation, etc.
    
    Args:
        task_type: Type of task ('credit_suggestion', 'email_generation', 'escalation')
        user_prompt: User's question
        user_id: User ID
        invoice_id: Invoice ID
        role: User role
    
    Returns:
        Dictionary with specialized response
    """
    try:
        logger.info(f"🎯 Routing specialized task: {task_type} for user {user_id}")
        
        # Get context
        invoice_context = get_invoice_context(invoice_id) or {}
        user_context = _get_user_context(user_id)
        if user_context:
            invoice_context.update(user_context)
        
        # Build specialized prompt
        from .agent_prompt_builder import build_specialized_prompt
        full_prompt = build_specialized_prompt(
            task_type, 
            user_prompt, 
            context=invoice_context, 
            role=role
        )
        
        # Call agent model
        raw_response = call_agent_model(full_prompt)
        
        # Parse with specialized parser if available
        if task_type == "credit_suggestion":
            from .agent_response_parser import parse_credit_suggestion
            credit_data = parse_credit_suggestion(raw_response)
            result = parse_agent_response(raw_response)
            result["credit_data"] = credit_data
        elif task_type == "email_generation":
            from .agent_response_parser import parse_email_suggestion
            email_data = parse_email_suggestion(raw_response)
            result = parse_agent_response(raw_response)
            result["email_data"] = email_data
        else:
            result = parse_agent_response(raw_response)
        
        # Store conversation
        _store_conversation(user_id, user_prompt, raw_response)
        
        logger.info(f"✅ Specialized task {task_type} completed for user {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in specialized task routing: {str(e)}")
        return _create_error_response(user_prompt, str(e))

def _get_user_context(user_id: str) -> Dict[str, Any]:
    """
    Get user-specific context from memory.
    
    Args:
        user_id: User ID
        
    Returns:
        Dictionary with user context
    """
    try:
        from .agent_memory import (
            get_active_invoice, 
            get_flagged_item_context, 
            get_supplier_context, 
            get_user_role_context,
            get_all_preferences
        )
        
        context = {}
        
        # Get active invoice
        active_invoice = get_active_invoice(user_id)
        if active_invoice:
            context["active_invoice"] = active_invoice
        
        # Get flagged item context
        flagged_item = get_flagged_item_context(user_id)
        if flagged_item:
            context["active_flagged_item"] = flagged_item
        
        # Get supplier context
        supplier = get_supplier_context(user_id)
        if supplier:
            context["active_supplier"] = supplier
        
        # Get user role
        user_role = get_user_role_context(user_id)
        if user_role:
            context["user_role"] = user_role
        
        # Get user preferences
        preferences = get_all_preferences(user_id)
        if preferences:
            context["preferences"] = preferences
        
        return context
        
    except Exception as e:
        logger.error(f"❌ Error getting user context: {str(e)}")
        return {}

def _store_conversation(user_id: str, user_message: str, agent_response: str) -> None:
    """
    Store conversation in memory.
    
    Args:
        user_id: User ID
        user_message: User's message
        agent_response: Agent's response
    """
    try:
        from .agent_memory import add_conversation_history
        add_conversation_history(user_id, user_message, agent_response)
        logger.debug(f"💾 Stored conversation for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Error storing conversation: {str(e)}")

def _create_error_response(user_prompt: str, error_message: str) -> Dict[str, Any]:
    """
    Create an error response when agent routing fails.
    
    Args:
        user_prompt: Original user prompt
        error_message: Error message
        
    Returns:
        Error response dictionary
    """
    return {
        "markdown": f"I apologize, but I encountered an error while processing your request: '{user_prompt}'. Please try again or contact support if the issue persists.",
        "actions": [],
        "confidence": 0,
        "entities": {},
        "urgency": "low",
        "error": error_message
    }

# Convenience functions for common tasks
def suggest_credit(user_id: str, invoice_id: str, role: str = "gm") -> Dict[str, Any]:
    """Convenience function for credit suggestions."""
    return route_specialized_task("credit_suggestion", "Suggest a credit for this invoice", user_id, invoice_id, role)

def generate_email(user_id: str, invoice_id: str, role: str = "gm") -> Dict[str, Any]:
    """Convenience function for email generation."""
    return route_specialized_task("email_generation", "Generate an email to the supplier", user_id, invoice_id, role)

def escalate_issue(user_id: str, invoice_id: str, role: str = "gm") -> Dict[str, Any]:
    """Convenience function for issue escalation."""
    return route_specialized_task("escalation", "Escalate this invoice issue", user_id, invoice_id, role)

if __name__ == "__main__":
    # Test the agent router
    print("🧪 Testing agent router...")
    
    # Test basic routing
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
    
    # Test specialized routing
    credit_result = suggest_credit("test_user", "INV-73318", "gm")
    print(f"✅ Credit suggestion test completed")
    print(f"Credit data: {credit_result.get('credit_data', {})}") 