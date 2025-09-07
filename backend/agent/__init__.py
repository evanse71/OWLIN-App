"""
Owlin Agent Package

A smart, offline-first assistant that helps hospitality teams review, audit, 
and act on scanned invoice data inside the Owlin app.

The agent provides:
- Confidence scoring based on data quality
- Price mismatch detection against historical data
- Delivery note pairing analysis
- Credit suggestions for mismatches
- Supplier performance scoring
- Role-aware suggestions and guidance
- Manual review recommendations
- Plain language summaries
"""

from .agent_core import run_owlin_agent, get_agent_info, analyze_invoice
from .confidence_scoring import score_confidence
from .price_checker import check_price_mismatches, get_price_summary
from .delivery_pairing import check_delivery_pairing, get_delivery_summary
from .summary_generator import generate_summary, get_summary_stats
from .credit_suggestion import suggest_credits_for_invoice, suggest_credit_for_invoice, get_credit_summary, generate_credit_email_template, validate_credit_suggestion
from .supplier_scoring import calculate_supplier_scores, get_supplier_summary, get_supplier_recommendations
from .role_aware_suggestions import get_role_aware_suggestions, format_suggestions_for_ui, get_suggestion_priority
from .matching_explainer import explain_match_status, get_match_confidence_level, format_match_summary
from .role_comment_helper import get_role_comment, get_action_permissions, get_available_actions, get_restricted_actions, format_comment_for_ui
from .credit_suggestion_engine import suggest_credit, suggest_credit_for_quantity_mismatch, suggest_credit_for_overcharge, suggest_credit_for_missing_item, validate_credit_suggestion, format_credit_suggestion_for_ui, get_credit_summary
from .email_generator import generate_supplier_email, generate_credit_email, generate_delivery_email, generate_price_query_email, format_email_for_ui, validate_email_content
from .agent_memory import set_context, get_context, get_context_with_metadata, clear_context, get_all_context, set_invoice_context, get_active_invoice, set_flagged_item_context, get_flagged_item_context, set_supplier_context, get_supplier_context, set_user_role_context, get_user_role_context, add_conversation_history, get_conversation_history, set_workflow_state, get_workflow_state, clear_workflow_state, set_preference, get_preference, get_all_preferences, set_temporary_context, cleanup_expired_context, get_memory_stats, export_user_context, import_user_context, clear_all_memory, get_invoice_context
from .agent_router import route_agent_task, route_agent_task_with_memory, route_specialized_task, suggest_credit, generate_email, escalate_issue
from .agent_prompt_builder import build_prompt, build_specialized_prompt, build_conversation_prompt
from .agent_client import call_agent_model, call_agent_model_with_retry, get_agent_client
from .agent_response_parser import parse_agent_response, parse_credit_suggestion, parse_email_suggestion

__version__ = "1.0.0"
__author__ = "Owlin Team"
__description__ = "Smart invoice analysis assistant for hospitality teams"

# Convenience function for easy integration
def analyze_invoice_with_agent(
    invoice_data: dict,
    historical_prices: dict = None,
    delivery_note_attached: bool = False
) -> dict:
    """
    Convenience function to analyze an invoice using the Owlin Agent.
    
    Args:
        invoice_data: Dictionary containing invoice data
        historical_prices: Optional dict of historical prices
        delivery_note_attached: Whether delivery note was matched
        
    Returns:
        Dictionary with analysis results including confidence score, flags, and summary
    """
    return run_owlin_agent(invoice_data, historical_prices)

# Export main functions for easy access
__all__ = [
    'run_owlin_agent',
    'get_agent_info', 
    'analyze_invoice',
    'analyze_invoice_with_agent',
    'score_confidence',
    'check_price_mismatches',
    'get_price_summary',
    'check_delivery_pairing',
    'get_delivery_summary',
    'generate_summary',
    'get_summary_stats',
    'suggest_credits_for_invoice',
    'suggest_credit_for_invoice',
    'get_credit_summary',
    'generate_credit_email_template',
    'validate_credit_suggestion',
    'calculate_supplier_scores',
    'get_supplier_summary',
    'get_supplier_recommendations',
    'get_role_aware_suggestions',
    'format_suggestions_for_ui',
    'get_suggestion_priority',
    'explain_match_status',
    'get_match_confidence_level',
    'format_match_summary',
    'get_role_comment',
    'get_action_permissions',
    'get_available_actions',
    'get_restricted_actions',
    'format_comment_for_ui',
    'suggest_credit',
    'suggest_credit_for_quantity_mismatch',
    'suggest_credit_for_overcharge',
    'suggest_credit_for_missing_item',
    'validate_credit_suggestion',
    'format_credit_suggestion_for_ui',
    'get_credit_summary',
    'generate_supplier_email',
    'generate_credit_email',
    'generate_delivery_email',
    'generate_price_query_email',
    'format_email_for_ui',
    'validate_email_content',
    'set_context',
    'get_context',
    'get_context_with_metadata',
    'clear_context',
    'get_all_context',
    'set_invoice_context',
    'get_active_invoice',
    'set_flagged_item_context',
    'get_flagged_item_context',
    'set_supplier_context',
    'get_supplier_context',
    'set_user_role_context',
    'get_user_role_context',
    'add_conversation_history',
    'get_conversation_history',
    'set_workflow_state',
    'get_workflow_state',
    'clear_workflow_state',
    'set_preference',
    'get_preference',
    'get_all_preferences',
    'set_temporary_context',
    'cleanup_expired_context',
    'get_memory_stats',
    'export_user_context',
    'import_user_context',
    'clear_all_memory',
    'get_invoice_context',
    'route_agent_task',
    'route_agent_task_with_memory',
    'route_specialized_task',
    'suggest_credit',
    'generate_email',
    'escalate_issue',
    'build_prompt',
    'build_specialized_prompt',
    'build_conversation_prompt',
    'call_agent_model',
    'call_agent_model_with_retry',
    'get_agent_client',
    'parse_agent_response',
    'parse_credit_suggestion',
    'parse_email_suggestion'
] 