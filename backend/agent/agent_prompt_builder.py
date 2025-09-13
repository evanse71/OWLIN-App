"""
Agent Prompt Builder Module

Builds role-aware prompts for the Owlin Agent based on user input, context, and user role.
This module ensures that prompts are tailored to the specific role and context of the user.
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

def build_prompt(
    user_prompt: str, 
    context: Optional[Dict[str, Any]] = None, 
    role: str = "gm"
) -> str:
    """
    Build a role-aware prompt for the agent.
    
    Args:
        user_prompt: The user's original question or command
        context: Optional context data (invoice info, flagged items, etc.)
        role: User role ('gm', 'finance', 'shift')
        
    Returns:
        Formatted prompt string for the agent
    """
    
    # Define role-specific instructions
    role_instructions = {
        "gm": """You are an AI assistant helping a General Manager (GM) in a hospitality business. 
Your role is to help with invoice review, cost management, and operational decisions. 
Focus on practical actions, cost implications, and operational impact.""",
        
        "finance": """You are an AI assistant helping a Finance team member in a hospitality business.
Your role is to help with invoice auditing, financial analysis, and compliance.
Focus on accuracy, compliance, and financial implications.""",
        
        "shift": """You are an AI assistant helping a Shift Lead in a hospitality business.
Your role is to help with daily operations, inventory management, and immediate issues.
Focus on immediate actions, inventory impact, and operational efficiency."""
    }
    
    # Get role-specific instructions
    role_instruction = role_instructions.get(role.lower(), role_instructions["gm"])
    
    # Build context section
    context_section = ""
    if context:
        context_section = _build_context_section(context)
    
    # Build the full prompt
    full_prompt = f"""{role_instruction}

CONTEXT:
{context_section}

USER QUESTION:
{user_prompt}

Please provide a helpful response that:
1. Addresses the user's question directly
2. Considers the context provided
3. Suggests relevant actions based on the user's role
4. Uses clear, professional language
5. Provides specific, actionable advice when appropriate

Response:"""
    
    logger.debug(f"Built prompt for role '{role}' with context: {bool(context)}")
    return full_prompt

def _build_context_section(context: Dict[str, Any]) -> str:
    """
    Build a formatted context section from context data.
    
    Args:
        context: Dictionary containing context information
        
    Returns:
        Formatted context string
    """
    sections = []
    
    # Invoice context
    if "invoice" in context:
        invoice = context["invoice"]
        sections.append(f"INVOICE: {invoice.get('supplier_name', 'Unknown Supplier')} - {invoice.get('invoice_number', 'No Number')}")
        sections.append(f"AMOUNT: £{invoice.get('total_amount', 0):.2f}")
        sections.append(f"DATE: {invoice.get('invoice_date', 'Unknown Date')}")
    
    # Flagged items context
    if "flagged_items" in context:
        flagged = context["flagged_items"]
        sections.append(f"FLAGGED ITEMS: {len(flagged)} items requiring attention")
        for item in flagged[:3]:  # Show first 3 items
            sections.append(f"  - {item.get('item_name', 'Unknown')}: £{item.get('difference', 0):.2f} variance")
    
    # Supplier context
    if "supplier" in context:
        supplier = context["supplier"]
        sections.append(f"SUPPLIER: {supplier.get('name', 'Unknown')}")
        if "rating" in supplier:
            sections.append(f"SUPPLIER RATING: {supplier['rating']}/5")
    
    # User preferences
    if "preferences" in context:
        prefs = context["preferences"]
        if prefs:
            sections.append("USER PREFERENCES:")
            for key, value in prefs.items():
                sections.append(f"  - {key}: {value}")
    
    # Workflow state
    if "workflow" in context:
        workflow = context["workflow"]
        sections.append(f"WORKFLOW: {workflow.get('state', 'Unknown')}")
    
    return "\n".join(sections) if sections else "No specific context available."

def build_specialized_prompt(
    prompt_type: str,
    user_prompt: str,
    context: Optional[Dict[str, Any]] = None,
    role: str = "gm"
) -> str:
    """
    Build specialized prompts for different types of interactions.
    
    Args:
        prompt_type: Type of prompt ('credit_suggestion', 'email_generation', 'escalation')
        user_prompt: User's original question
        context: Optional context data
        role: User role
        
    Returns:
        Specialized prompt string
    """
    
    specialized_instructions = {
        "credit_suggestion": """You are helping with credit suggestions for invoice discrepancies.
Focus on:
- Calculating accurate credit amounts
- Justifying the credit with clear reasoning
- Suggesting appropriate actions (email, phone call, etc.)
- Considering supplier relationship impact""",
        
        "email_generation": """You are helping to generate professional emails to suppliers.
Focus on:
- Professional and courteous tone
- Clear explanation of issues
- Specific requests or questions
- Appropriate level of urgency
- Contact information and next steps""",
        
        "escalation": """You are helping to escalate invoice issues.
Focus on:
- Severity assessment
- Appropriate escalation level
- Required documentation
- Timeline expectations
- Stakeholder communication""",
        
        "price_analysis": """You are helping with price analysis and cost management.
Focus on:
- Price variance analysis
- Historical price trends
- Market comparison
- Cost impact assessment
- Budget implications"""
    }
    
    # Get specialized instruction
    instruction = specialized_instructions.get(prompt_type, specialized_instructions["credit_suggestion"])
    
    # Build context section
    context_section = _build_context_section(context) if context else "No specific context available."
    
    # Build specialized prompt
    full_prompt = f"""{instruction}

CONTEXT:
{context_section}

USER REQUEST:
{user_prompt}

Please provide a detailed response that addresses the specific {prompt_type} requirements while considering the user's role as {role.upper()}.

Response:"""
    
    logger.debug(f"Built specialized prompt type '{prompt_type}' for role '{role}'")
    return full_prompt

def build_conversation_prompt(
    user_prompt: str,
    conversation_history: List[Dict[str, str]],
    context: Optional[Dict[str, Any]] = None,
    role: str = "gm"
) -> str:
    """
    Build a prompt that includes conversation history for follow-up questions.
    
    Args:
        user_prompt: Current user question
        conversation_history: List of previous exchanges
        context: Optional context data
        role: User role
        
    Returns:
        Prompt with conversation history
    """
    
    # Build conversation history section
    history_section = ""
    if conversation_history:
        history_section = "CONVERSATION HISTORY:\n"
        for i, exchange in enumerate(conversation_history[-3:], 1):  # Last 3 exchanges
            user_msg = exchange.get("user", "")
            agent_msg = exchange.get("agent", "")
            history_section += f"Exchange {i}:\nUser: {user_msg}\nAgent: {agent_msg}\n\n"
    
    # Build context section
    context_section = _build_context_section(context) if context else "No specific context available."
    
    # Build the full prompt
    full_prompt = f"""You are an AI assistant helping a {role.upper()} in a hospitality business.
Continue the conversation naturally, considering the previous exchanges.

CONTEXT:
{context_section}

{history_section}USER QUESTION:
{user_prompt}

Please provide a helpful response that:
1. Addresses the user's current question
2. References relevant information from the conversation history
3. Maintains consistency with previous responses
4. Suggests relevant actions based on the user's role

Response:"""
    
    logger.debug(f"Built conversation prompt for role '{role}' with {len(conversation_history)} history items")
    return full_prompt 