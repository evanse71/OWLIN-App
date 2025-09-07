"""
Agent API Routes

Provides API endpoints for the Owlin Agent to handle user questions
and return intelligent responses with suggested actions.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging

# Import agent router functions
from agent.agent_router import (
    route_agent_task,
    route_agent_task_with_memory,
    route_specialized_task,
    suggest_credit,
    generate_email,
    escalate_issue
)

logger = logging.getLogger(__name__)
router = APIRouter()

class AgentRequest(BaseModel):
    """Request model for agent questions."""
    user_prompt: Optional[str] = None
    user_id: str
    invoice_id: str
    role: str  # 'gm', 'finance', 'shift'

class AgentResponse(BaseModel):
    """Response model for agent answers."""
    markdown: str
    actions: List[Dict[str, Any]] = []
    confidence: int = 0
    entities: Dict[str, Any] = {}
    urgency: str = "medium"
    error: Optional[str] = None

@router.post("/agent/ask", response_model=AgentResponse)
async def ask_agent(request: AgentRequest) -> Dict[str, Any]:
    """
    Handle agent questions from the frontend.
    
    Args:
        user_prompt: User's natural language query
        user_id: Owlin user ID
        invoice_id: ID of the invoice they're viewing
        role: Role of the user (used for permissions and response type)
    
    Returns:
        {
            "markdown": Agent's written reply (string),
            "actions": Optional structured actions (e.g. suggest_credit),
            "confidence": Confidence score (0–100),
            "entities": Extracted entities (suppliers, amounts, etc.),
            "urgency": Urgency level (low, medium, high)
        }
    """
    try:
        logger.info(f"🤖 Agent question from user {request.user_id} for invoice {request.invoice_id}")
        logger.debug(f"📝 User prompt: {request.user_prompt}")
        logger.debug(f"👤 User role: {request.role}")
        
        # Route the agent task
        result = route_agent_task(
            user_prompt=request.user_prompt,
            user_id=request.user_id,
            invoice_id=request.invoice_id,
            role=request.role
        )
        
        logger.info(f"✅ Agent response generated with confidence: {result.get('confidence', 0)}%")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in agent endpoint: {str(e)}")
        return {
            "error": str(e),
            "markdown": "⚠️ The agent encountered an error. Please try again.",
            "actions": [],
            "confidence": 0,
            "entities": {},
            "urgency": "low"
        }

@router.post("/agent/ask-with-memory", response_model=AgentResponse)
async def ask_agent_with_memory(request: AgentRequest) -> Dict[str, Any]:
    """
    Handle agent questions with conversation memory.
    
    This endpoint includes conversation history for more contextual responses.
    """
    try:
        logger.info(f"🧠 Agent question with memory from user {request.user_id}")
        
        result = route_agent_task_with_memory(
            user_prompt=request.user_prompt,
            user_id=request.user_id,
            invoice_id=request.invoice_id,
            role=request.role
        )
        
        logger.info(f"✅ Agent response with memory generated")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in agent memory endpoint: {str(e)}")
        return {
            "error": str(e),
            "markdown": "⚠️ The agent encountered an error. Please try again.",
            "actions": [],
            "confidence": 0,
            "entities": {},
            "urgency": "low"
        }

class SpecializedAgentRequest(BaseModel):
    """Request model for specialized agent tasks."""
    user_prompt: str
    user_id: str
    invoice_id: str
    role: str
    task_type: str  # 'credit_suggestion', 'email_generation', 'escalation'

@router.post("/agent/specialized", response_model=AgentResponse)
async def specialized_agent_task(request: SpecializedAgentRequest) -> Dict[str, Any]:
    """
    Handle specialized agent tasks like credit suggestions, email generation, etc.
    """
    try:
        logger.info(f"🎯 Specialized agent task: {request.task_type} for user {request.user_id}")
        
        result = route_specialized_task(
            task_type=request.task_type,
            user_prompt=request.user_prompt,
            user_id=request.user_id,
            invoice_id=request.invoice_id,
            role=request.role
        )
        
        logger.info(f"✅ Specialized task {request.task_type} completed")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in specialized agent task: {str(e)}")
        return {
            "error": str(e),
            "markdown": "⚠️ The agent encountered an error. Please try again.",
            "actions": [],
            "confidence": 0,
            "entities": {},
            "urgency": "low"
        }

# Convenience endpoints for common tasks
@router.post("/agent/suggest-credit", response_model=AgentResponse)
async def suggest_credit_endpoint(request: AgentRequest) -> Dict[str, Any]:
    """Convenience endpoint for credit suggestions."""
    try:
        logger.info(f"💰 Credit suggestion request from user {request.user_id}")
        
        # Use the user_prompt if provided, otherwise use a default
        user_prompt = request.user_prompt or "Suggest a credit for this invoice"
        
        result = suggest_credit(
            user_id=request.user_id,
            invoice_id=request.invoice_id,
            role=request.role
        )
        
        logger.info(f"✅ Credit suggestion generated")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in credit suggestion: {str(e)}")
        return {
            "error": str(e),
            "markdown": "⚠️ Unable to generate credit suggestion. Please try again.",
            "actions": [],
            "confidence": 0,
            "entities": {},
            "urgency": "low"
        }

@router.post("/agent/generate-email", response_model=AgentResponse)
async def generate_email_endpoint(request: AgentRequest) -> Dict[str, Any]:
    """Convenience endpoint for email generation."""
    try:
        logger.info(f"📧 Email generation request from user {request.user_id}")
        
        # Use the user_prompt if provided, otherwise use a default
        user_prompt = request.user_prompt or "Generate an email to the supplier"
        
        result = generate_email(
            user_id=request.user_id,
            invoice_id=request.invoice_id,
            role=request.role
        )
        
        logger.info(f"✅ Email generated")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in email generation: {str(e)}")
        return {
            "error": str(e),
            "markdown": "⚠️ Unable to generate email. Please try again.",
            "actions": [],
            "confidence": 0,
            "entities": {},
            "urgency": "low"
        }

@router.post("/agent/escalate", response_model=AgentResponse)
async def escalate_issue_endpoint(request: AgentRequest) -> Dict[str, Any]:
    """Convenience endpoint for issue escalation."""
    try:
        logger.info(f"🚨 Escalation request from user {request.user_id}")
        
        # Use the user_prompt if provided, otherwise use a default
        user_prompt = request.user_prompt or "Escalate this invoice issue"
        
        result = escalate_issue(
            user_id=request.user_id,
            invoice_id=request.invoice_id,
            role=request.role
        )
        
        logger.info(f"✅ Escalation processed")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in escalation: {str(e)}")
        return {
            "error": str(e),
            "markdown": "⚠️ Unable to process escalation. Please try again.",
            "actions": [],
            "confidence": 0,
            "entities": {},
            "urgency": "low"
        }

# Health check endpoint
@router.get("/agent/health")
async def agent_health_check() -> Dict[str, Any]:
    """
    Health check endpoint for the agent service.
    """
    try:
        # Import agent info to verify the agent is working
        from agent import get_agent_info
        
        agent_info = get_agent_info()
        
        return {
            "status": "healthy",
            "agent_version": agent_info.get("version", "unknown"),
            "capabilities": agent_info.get("capabilities", []),
            "message": "Agent service is operational"
        }
        
    except Exception as e:
        logger.error(f"❌ Agent health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "message": "Agent service is experiencing issues"
        }

# Agent capabilities endpoint
@router.get("/agent/capabilities")
async def get_agent_capabilities() -> Dict[str, Any]:
    """
    Get information about agent capabilities and supported features.
    """
    return {
        "capabilities": [
            "invoice_analysis",
            "credit_suggestions",
            "email_generation",
            "issue_escalation",
            "price_analysis",
            "supplier_insights",
            "role_aware_responses",
            "conversation_memory"
        ],
        "supported_roles": ["gm", "finance", "shift"],
        "supported_tasks": [
            "credit_suggestion",
            "email_generation", 
            "escalation",
            "price_analysis"
        ],
        "response_formats": {
            "markdown": "Agent's written response",
            "actions": "Suggested actions for the user",
            "confidence": "Confidence score (0-100)",
            "entities": "Extracted entities (suppliers, amounts, etc.)",
            "urgency": "Urgency level (low, medium, high)"
        }
    } 