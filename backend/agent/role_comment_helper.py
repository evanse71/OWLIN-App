"""
Role Comment Helper Module for Owlin Agent

Provides contextual tooltips, badges, and helper messages that explain
what users can do based on their role and the current item state.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

def get_role_comment(role: str, issue_type: str, item_status: str) -> str:
    """
    Generate a contextual comment based on user role, issue type, and item status.
    
    Args:
        role: User's role ("Finance", "GM", "Shift Lead")
        issue_type: Type of issue ("quantity_mismatch", "price_mismatch", etc.)
        item_status: Current status ("pending", "flagged", "resolved", "escalated")
        
    Returns:
        Contextual comment explaining what the user can do
    """
    logger.info(f"💬 Generating role comment for {role} - {issue_type} ({item_status})")
    
    try:
        # Normalize inputs
        role = role.lower().strip()
        issue_type = issue_type.lower().strip()
        item_status = item_status.lower().strip()
        
        # Get the appropriate comment based on the combination
        comment = _get_comment_for_combination(role, issue_type, item_status)
        
        if not comment:
            # Fallback to generic comment
            comment = _get_generic_comment(role, issue_type, item_status)
        
        logger.info(f"✅ Generated role comment: {comment[:50]}...")
        return comment
        
    except Exception as e:
        logger.error(f"❌ Error generating role comment: {e}")
        return "Unable to generate contextual guidance at this time."

def _get_comment_for_combination(role: str, issue_type: str, item_status: str) -> str:
    """
    Get specific comment for role/issue/status combination.
    
    Args:
        role: User's role
        issue_type: Type of issue
        item_status: Current status
        
    Returns:
        Specific comment or empty string if no specific match
    """
    # Define specific combinations
    combinations = {
        # Shift Lead combinations
        ("shift lead", "quantity_mismatch", "pending"): 
            "You can flag this mismatch and leave a comment, but only a Finance user can override the quantity.",
        
        ("shift lead", "quantity_mismatch", "flagged"): 
            "This quantity mismatch has been flagged. You can add additional comments or request Finance review.",
        
        ("shift lead", "delivery_missing", "pending"): 
            "You can mark items as not received and add delivery notes. Contact the supplier if needed.",
        
        ("shift lead", "delivery_missing", "flagged"): 
            "Delivery issues have been flagged. You can update the delivery status or escalate to management.",
        
        ("shift lead", "item_not_received", "pending"): 
            "You can mark this item as not received and add a comment explaining the situation.",
        
        ("shift lead", "item_not_received", "flagged"): 
            "This item has been flagged as not received. You can update the status or add additional details.",
        
        ("shift lead", "unexpected_item", "pending"): 
            "You can flag this unexpected item and add a comment explaining what was received instead.",
        
        ("shift lead", "unexpected_item", "flagged"): 
            "This unexpected item has been flagged. You can update the details or escalate if needed.",
        
        # Finance combinations
        ("finance", "quantity_mismatch", "pending"): 
            "You can override the quantity, adjust the line total, and add a comment explaining the change.",
        
        ("finance", "quantity_mismatch", "flagged"): 
            "This quantity mismatch has been flagged. You can resolve it by adjusting quantities or requesting credit.",
        
        ("finance", "quantity_mismatch", "escalated"): 
            "This quantity issue was escalated. You can resolve it directly or suggest a credit amount.",
        
        ("finance", "price_mismatch", "pending"): 
            "You can adjust the price, suggest a credit amount, or contact the supplier about the discrepancy.",
        
        ("finance", "price_mismatch", "flagged"): 
            "This price mismatch has been flagged. You can resolve it by adjusting the price or requesting credit.",
        
        ("finance", "price_mismatch", "escalated"): 
            "This price issue was escalated by a GM. You can suggest a credit value or resolve the item.",
        
        ("finance", "delivery_missing", "pending"): 
            "You can mark items as missing, request delivery notes from the supplier, or suggest credits.",
        
        ("finance", "delivery_missing", "flagged"): 
            "Delivery issues have been flagged. You can resolve by adjusting totals or requesting supplier credits.",
        
        ("finance", "item_not_received", "pending"): 
            "You can mark this as not received, adjust the invoice total, and suggest a credit amount.",
        
        ("finance", "item_not_received", "flagged"): 
            "This item has been flagged as not received. You can resolve by adjusting totals or requesting credits.",
        
        ("finance", "unexpected_item", "pending"): 
            "You can adjust the invoice to reflect the correct items received or request a corrected invoice.",
        
        ("finance", "unexpected_item", "flagged"): 
            "This unexpected item has been flagged. You can resolve by adjusting the invoice or requesting corrections.",
        
        # GM combinations
        ("gm", "quantity_mismatch", "pending"): 
            "As a GM, you can resolve this quantity mismatch, escalate it to supplier review, or delegate to Finance.",
        
        ("gm", "quantity_mismatch", "flagged"): 
            "This quantity issue has been flagged. You can resolve it directly or escalate to supplier management.",
        
        ("gm", "quantity_mismatch", "escalated"): 
            "This quantity issue is escalated. You can resolve it, contact the supplier directly, or assign to Finance.",
        
        ("gm", "price_mismatch", "pending"): 
            "As a GM, you can escalate this price issue to supplier review or delegate to Finance for credit negotiation.",
        
        ("gm", "price_mismatch", "flagged"): 
            "This price issue has been flagged. You can escalate to supplier management or assign to Finance.",
        
        ("gm", "price_mismatch", "escalated"): 
            "This price issue is escalated. You can resolve it, contact the supplier directly, or assign to Finance.",
        
        ("gm", "delivery_missing", "pending"): 
            "As a GM, you can escalate this to the supplier review log or mark it resolved.",
        
        ("gm", "delivery_missing", "flagged"): 
            "Delivery issues have been flagged. You can escalate to supplier management or resolve directly.",
        
        ("gm", "delivery_missing", "escalated"): 
            "This delivery issue is escalated. You can resolve it, contact the supplier directly, or assign to Finance.",
        
        ("gm", "item_not_received", "pending"): 
            "As a GM, you can escalate this missing item to supplier review or delegate to Finance for credit.",
        
        ("gm", "item_not_received", "flagged"): 
            "This missing item has been flagged. You can escalate to supplier management or resolve directly.",
        
        ("gm", "item_not_received", "escalated"): 
            "This missing item is escalated. You can resolve it, contact the supplier directly, or assign to Finance.",
        
        ("gm", "unexpected_item", "pending"): 
            "As a GM, you can escalate this unexpected item to supplier review or delegate to Finance for correction.",
        
        ("gm", "unexpected_item", "flagged"): 
            "This unexpected item has been flagged. You can escalate to supplier management or resolve directly.",
        
        ("gm", "unexpected_item", "escalated"): 
            "This unexpected item is escalated. You can resolve it, contact the supplier directly, or assign to Finance.",
        
        # Resolved status combinations
        ("shift lead", "quantity_mismatch", "resolved"): 
            "This quantity mismatch has been resolved. You can view the resolution details but cannot modify them.",
        
        ("finance", "price_mismatch", "resolved"): 
            "This price mismatch has been resolved. You can view the resolution details and credit amount applied.",
        
        ("gm", "delivery_missing", "resolved"): 
            "This delivery issue has been resolved. You can view the resolution details and any supplier credits applied.",
    }
    
    # Check for exact match
    key = (role, issue_type, item_status)
    if key in combinations:
        return combinations[key]
    
    # Check for partial matches (role + issue_type)
    for (r, i, s), comment in combinations.items():
        if r == role and i == issue_type:
            return comment
    
    return ""

def _get_generic_comment(role: str, issue_type: str, item_status: str) -> str:
    """
    Generate a generic comment when no specific combination is found.
    
    Args:
        role: User's role
        issue_type: Type of issue
        item_status: Current status
        
    Returns:
        Generic contextual comment
    """
    # Role-based generic comments
    role_comments = {
        "shift lead": {
            "pending": "You can flag issues and add comments. Contact Finance for quantity or price adjustments.",
            "flagged": "This item has been flagged. You can add additional comments or request review.",
            "resolved": "This item has been resolved. You can view the resolution details.",
            "escalated": "This item has been escalated. You can add comments but cannot modify the resolution."
        },
        "finance": {
            "pending": "You can resolve this issue by adjusting quantities, prices, or suggesting credits.",
            "flagged": "This item has been flagged. You can resolve it or escalate to management.",
            "resolved": "This item has been resolved. You can view the resolution details and any credits applied.",
            "escalated": "This item was escalated by a GM. You can suggest credits or resolve it directly."
        },
        "gm": {
            "pending": "As a GM, you can resolve this issue, escalate it to supplier review, or delegate to Finance.",
            "flagged": "This item has been flagged. You can resolve it directly or escalate to supplier management.",
            "resolved": "This item has been resolved. You can view the resolution details and any supplier actions.",
            "escalated": "This item is escalated. You can resolve it, contact the supplier directly, or assign to Finance."
        }
    }
    
    # Issue type specific guidance
    issue_guidance = {
        "quantity_mismatch": "Quantity discrepancies can be resolved by adjusting line totals or requesting credits.",
        "price_mismatch": "Price issues can be resolved by adjusting prices, suggesting credits, or contacting suppliers.",
        "delivery_missing": "Missing delivery issues can be resolved by marking items as not received or requesting delivery notes.",
        "item_not_received": "Items not received can be resolved by adjusting invoice totals or requesting credits.",
        "unexpected_item": "Unexpected items can be resolved by adjusting the invoice or requesting corrected invoices."
    }
    
    # Get role-specific comment
    role_comment = role_comments.get(role, {}).get(item_status, "You can view this item's details.")
    
    # Get issue-specific guidance
    issue_comment = issue_guidance.get(issue_type, "This issue can be resolved through appropriate actions.")
    
    return f"{role_comment} {issue_comment}"

def get_action_permissions(role: str, issue_type: str, item_status: str) -> Dict[str, bool]:
    """
    Get a dictionary of what actions the user can perform.
    
    Args:
        role: User's role
        issue_type: Type of issue
        item_status: Current status
        
    Returns:
        Dictionary of action permissions
    """
    role = role.lower().strip()
    issue_type = issue_type.lower().strip()
    item_status = item_status.lower().strip()
    
    # Define permissions by role and status
    permissions = {
        "shift lead": {
            "pending": {
                "can_flag": True,
                "can_comment": True,
                "can_resolve": False,
                "can_escalate": True,
                "can_override_quantity": False,
                "can_override_price": False,
                "can_suggest_credit": False
            },
            "flagged": {
                "can_flag": False,
                "can_comment": True,
                "can_resolve": False,
                "can_escalate": True,
                "can_override_quantity": False,
                "can_override_price": False,
                "can_suggest_credit": False
            },
            "resolved": {
                "can_flag": False,
                "can_comment": False,
                "can_resolve": False,
                "can_escalate": False,
                "can_override_quantity": False,
                "can_override_price": False,
                "can_suggest_credit": False
            },
            "escalated": {
                "can_flag": False,
                "can_comment": True,
                "can_resolve": False,
                "can_escalate": False,
                "can_override_quantity": False,
                "can_override_price": False,
                "can_suggest_credit": False
            }
        },
        "finance": {
            "pending": {
                "can_flag": True,
                "can_comment": True,
                "can_resolve": True,
                "can_escalate": True,
                "can_override_quantity": True,
                "can_override_price": True,
                "can_suggest_credit": True
            },
            "flagged": {
                "can_flag": False,
                "can_comment": True,
                "can_resolve": True,
                "can_escalate": True,
                "can_override_quantity": True,
                "can_override_price": True,
                "can_suggest_credit": True
            },
            "resolved": {
                "can_flag": False,
                "can_comment": False,
                "can_resolve": False,
                "can_escalate": False,
                "can_override_quantity": False,
                "can_override_price": False,
                "can_suggest_credit": False
            },
            "escalated": {
                "can_flag": False,
                "can_comment": True,
                "can_resolve": True,
                "can_escalate": False,
                "can_override_quantity": True,
                "can_override_price": True,
                "can_suggest_credit": True
            }
        },
        "gm": {
            "pending": {
                "can_flag": True,
                "can_comment": True,
                "can_resolve": True,
                "can_escalate": True,
                "can_override_quantity": True,
                "can_override_price": True,
                "can_suggest_credit": True
            },
            "flagged": {
                "can_flag": False,
                "can_comment": True,
                "can_resolve": True,
                "can_escalate": True,
                "can_override_quantity": True,
                "can_override_price": True,
                "can_suggest_credit": True
            },
            "resolved": {
                "can_flag": False,
                "can_comment": False,
                "can_resolve": False,
                "can_escalate": False,
                "can_override_quantity": False,
                "can_override_price": False,
                "can_suggest_credit": False
            },
            "escalated": {
                "can_flag": False,
                "can_comment": True,
                "can_resolve": True,
                "can_escalate": False,
                "can_override_quantity": True,
                "can_override_price": True,
                "can_suggest_credit": True
            }
        }
    }
    
    return permissions.get(role, {}).get(item_status, {
        "can_flag": False,
        "can_comment": False,
        "can_resolve": False,
        "can_escalate": False,
        "can_override_quantity": False,
        "can_override_price": False,
        "can_suggest_credit": False
    })

def get_available_actions(role: str, issue_type: str, item_status: str) -> List[str]:
    """
    Get a list of available actions for the user.
    
    Args:
        role: User's role
        issue_type: Type of issue
        item_status: Current status
        
    Returns:
        List of available actions
    """
    permissions = get_action_permissions(role, issue_type, item_status)
    
    actions = []
    
    if permissions.get("can_flag", False):
        actions.append("Flag issue")
    
    if permissions.get("can_comment", False):
        actions.append("Add comment")
    
    if permissions.get("can_resolve", False):
        actions.append("Resolve issue")
    
    if permissions.get("can_escalate", False):
        actions.append("Escalate to management")
    
    if permissions.get("can_override_quantity", False):
        actions.append("Override quantity")
    
    if permissions.get("can_override_price", False):
        actions.append("Override price")
    
    if permissions.get("can_suggest_credit", False):
        actions.append("Suggest credit")
    
    return actions

def get_restricted_actions(role: str, issue_type: str, item_status: str) -> List[str]:
    """
    Get a list of actions that are restricted for the user.
    
    Args:
        role: User's role
        issue_type: Type of issue
        item_status: Current status
        
    Returns:
        List of restricted actions with explanations
    """
    permissions = get_action_permissions(role, issue_type, item_status)
    
    restrictions = []
    
    if not permissions.get("can_override_quantity", False):
        restrictions.append("Override quantity (Finance only)")
    
    if not permissions.get("can_override_price", False):
        restrictions.append("Override price (Finance only)")
    
    if not permissions.get("can_suggest_credit", False):
        restrictions.append("Suggest credit (Finance only)")
    
    if not permissions.get("can_resolve", False):
        restrictions.append("Resolve issue (Finance/GM only)")
    
    if not permissions.get("can_escalate", False):
        restrictions.append("Escalate (GM only)")
    
    return restrictions

def format_comment_for_ui(comment: str, role: str, issue_type: str, item_status: str) -> Dict[str, Any]:
    """
    Format the comment for UI display with additional metadata.
    
    Args:
        comment: The contextual comment
        role: User's role
        issue_type: Type of issue
        item_status: Current status
        
    Returns:
        Formatted comment with metadata
    """
    permissions = get_action_permissions(role, issue_type, item_status)
    available_actions = get_available_actions(role, issue_type, item_status)
    restricted_actions = get_restricted_actions(role, issue_type, item_status)
    
    return {
        "comment": comment,
        "role": role,
        "issue_type": issue_type,
        "item_status": item_status,
        "permissions": permissions,
        "available_actions": available_actions,
        "restricted_actions": restricted_actions,
        "can_modify": item_status in ["pending", "flagged"],
        "is_resolved": item_status == "resolved",
        "is_escalated": item_status == "escalated"
    }


if __name__ == "__main__":
    # Test the role comment helper
    logging.basicConfig(level=logging.INFO)
    
    # Test scenarios
    test_scenarios = [
        ("Shift Lead", "quantity_mismatch", "pending"),
        ("Finance", "price_mismatch", "escalated"),
        ("GM", "delivery_missing", "pending"),
        ("Shift Lead", "item_not_received", "flagged"),
        ("Finance", "unexpected_item", "resolved"),
        ("GM", "quantity_mismatch", "escalated")
    ]
    
    print("💬 Role Comment Helper Test Results:")
    
    for role, issue_type, item_status in test_scenarios:
        print(f"\n{role} - {issue_type} ({item_status}):")
        
        # Get comment
        comment = get_role_comment(role, issue_type, item_status)
        print(f"  Comment: {comment}")
        
        # Get permissions
        permissions = get_action_permissions(role, issue_type, item_status)
        print(f"  Permissions: {permissions}")
        
        # Get available actions
        actions = get_available_actions(role, issue_type, item_status)
        print(f"  Available Actions: {actions}")
        
        # Get restricted actions
        restrictions = get_restricted_actions(role, issue_type, item_status)
        print(f"  Restricted Actions: {restrictions}")
        
        # Format for UI
        formatted = format_comment_for_ui(comment, role, issue_type, item_status)
        print(f"  Can Modify: {formatted['can_modify']}")
        print(f"  Is Resolved: {formatted['is_resolved']}")
        print(f"  Is Escalated: {formatted['is_escalated']}")
    
    print("\n✅ Test completed successfully") 