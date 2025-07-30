"""
Role-Aware Suggestions Module for Owlin Agent

Provides tailored guidance and suggestions based on user role,
document status, confidence scores, and flagged issues.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def get_role_aware_suggestions(
    user_role: str, 
    document_status: str, 
    confidence: float, 
    flagged_issues: List[Dict]
) -> List[str]:
    """
    Generate role-aware suggestions based on context.
    
    Args:
        user_role: User's role ("Finance", "GM", "Shift Lead")
        document_status: Document status ("pending", "scanned", "needs_review", "matched")
        confidence: Confidence score (0-100)
        flagged_issues: List of flagged issues from analysis
        
    Returns:
        List of plain-language, actionable suggestions
    """
    logger.info(f"🎯 Generating role-aware suggestions for {user_role} (status: {document_status}, confidence: {confidence:.1f}%)")
    
    try:
        suggestions = []
        
        # Get base suggestions based on role
        role_suggestions = _get_role_specific_suggestions(user_role, document_status, confidence, flagged_issues)
        suggestions.extend(role_suggestions)
        
        # Get status-based suggestions
        status_suggestions = _get_status_specific_suggestions(document_status, confidence, flagged_issues)
        suggestions.extend(status_suggestions)
        
        # Get confidence-based suggestions
        confidence_suggestions = _get_confidence_specific_suggestions(confidence, flagged_issues)
        suggestions.extend(confidence_suggestions)
        
        # Get issue-specific suggestions
        issue_suggestions = _get_issue_specific_suggestions(flagged_issues, user_role)
        suggestions.extend(issue_suggestions)
        
        # Remove duplicates while preserving order
        unique_suggestions = []
        seen = set()
        for suggestion in suggestions:
            if suggestion not in seen:
                unique_suggestions.append(suggestion)
                seen.add(suggestion)
        
        logger.info(f"✅ Generated {len(unique_suggestions)} role-aware suggestions")
        return unique_suggestions
        
    except Exception as e:
        logger.error(f"❌ Error generating role-aware suggestions: {e}")
        return ["Review this invoice manually — analysis encountered an error."]

def _get_role_specific_suggestions(
    user_role: str, 
    document_status: str, 
    confidence: float, 
    flagged_issues: List[Dict]
) -> List[str]:
    """
    Generate suggestions specific to user role.
    
    Args:
        user_role: User's role
        document_status: Document status
        confidence: Confidence score
        flagged_issues: List of flagged issues
        
    Returns:
        List of role-specific suggestions
    """
    suggestions = []
    
    if user_role.lower() == "finance":
        suggestions.extend(_get_finance_suggestions(document_status, confidence, flagged_issues))
    elif user_role.lower() == "gm":
        suggestions.extend(_get_gm_suggestions(document_status, confidence, flagged_issues))
    elif user_role.lower() == "shift lead":
        suggestions.extend(_get_shift_lead_suggestions(document_status, confidence, flagged_issues))
    else:
        # Default suggestions for unknown roles
        suggestions.extend(_get_default_suggestions(document_status, confidence, flagged_issues))
    
    return suggestions

def _get_finance_suggestions(document_status: str, confidence: float, flagged_issues: List[Dict]) -> List[str]:
    """
    Generate Finance-specific suggestions.
    
    Args:
        document_status: Document status
        confidence: Confidence score
        flagged_issues: List of flagged issues
        
    Returns:
        List of Finance-specific suggestions
    """
    suggestions = []
    
    # Low confidence suggestions
    if confidence < 70:
        critical_issues = [issue for issue in flagged_issues if issue.get('severity') == 'critical']
        warning_issues = [issue for issue in flagged_issues if issue.get('severity') == 'warning']
        
        if critical_issues:
            suggestions.append(f"Review line items — confidence is low and {len(critical_issues)} critical issues are flagged.")
        elif warning_issues:
            suggestions.append(f"Review line items — confidence is low and {len(warning_issues)} issues are flagged.")
        else:
            suggestions.append("Review line items — confidence is low and data quality may be poor.")
    
    # Price-related suggestions
    price_issues = [issue for issue in flagged_issues if 'price' in issue.get('type', '').lower()]
    if price_issues:
        for issue in price_issues[:2]:  # Limit to first 2 price issues
            item_name = issue.get('field', '').split('.')[-1] if '.' in issue.get('field', '') else 'item'
            suggestions.append(f"Check supplier pricing — {item_name} may be overpriced.")
    
    # Credit suggestions
    credit_issues = [issue for issue in flagged_issues if any(keyword in issue.get('type', '').lower() 
                                                              for keyword in ['missing', 'overcharge', 'quantity'])]
    if credit_issues:
        suggestions.append("Suggested credits available for flagged issues — see credit suggestions below.")
    
    # Supplier escalation
    supplier_issues = [issue for issue in flagged_issues if 'supplier' in issue.get('message', '').lower()]
    if len(supplier_issues) >= 3:
        suggestions.append(f"{len(supplier_issues)} unresolved issues with this supplier — consider escalation.")
    
    # Document status suggestions
    if document_status == "needs_review":
        suggestions.append("This invoice requires manual review before approval.")
    elif document_status == "pending":
        suggestions.append("Invoice is pending processing — review when complete.")
    
    return suggestions

def _get_gm_suggestions(document_status: str, confidence: float, flagged_issues: List[Dict]) -> List[str]:
    """
    Generate GM-specific suggestions.
    
    Args:
        document_status: Document status
        confidence: Confidence score
        flagged_issues: List of flagged issues
        
    Returns:
        List of GM-specific suggestions
    """
    suggestions = []
    
    # Escalation logic
    critical_issues = [issue for issue in flagged_issues if issue.get('severity') == 'critical']
    if len(critical_issues) >= 3:
        suggestions.append(f"{len(critical_issues)} critical issues detected — consider supplier escalation.")
    elif len(flagged_issues) >= 5:
        suggestions.append(f"{len(flagged_issues)} unresolved issues with this supplier in the last 30 days — consider escalation.")
    
    # Supplier performance
    supplier_issues = [issue for issue in flagged_issues if 'supplier' in issue.get('message', '').lower()]
    if supplier_issues:
        suggestions.append("Add a note if you've contacted the supplier already.")
    
    # High-value invoice handling
    high_value_issues = [issue for issue in flagged_issues if 'high_value' in issue.get('type', '').lower()]
    if high_value_issues:
        suggestions.append("High-value invoice requires special attention — review personally.")
    
    # Quality assurance
    if confidence < 60:
        suggestions.append("Low confidence score indicates data quality issues — review manually.")
    
    # Operational insights
    delivery_issues = [issue for issue in flagged_issues if 'delivery' in issue.get('type', '').lower()]
    if delivery_issues:
        suggestions.append("Delivery issues detected — review operational procedures.")
    
    return suggestions

def _get_shift_lead_suggestions(document_status: str, confidence: float, flagged_issues: List[Dict]) -> List[str]:
    """
    Generate Shift Lead-specific suggestions.
    
    Args:
        document_status: Document status
        confidence: Confidence score
        flagged_issues: List of flagged issues
        
    Returns:
        List of Shift Lead-specific suggestions
    """
    suggestions = []
    
    # Delivery note suggestions
    delivery_issues = [issue for issue in flagged_issues if 'delivery' in issue.get('type', '').lower()]
    if delivery_issues:
        suggestions.append("This invoice has no matching delivery note — upload a photo or scan if available.")
        suggestions.append("Flag any missing items manually if not all were delivered.")
    
    # Quantity verification
    quantity_issues = [issue for issue in flagged_issues if 'quantity' in issue.get('type', '').lower()]
    if quantity_issues:
        suggestions.append("Verify quantities received against invoice — discrepancies detected.")
    
    # Quality checks
    quality_issues = [issue for issue in flagged_issues if 'quality' in issue.get('type', '').lower()]
    if quality_issues:
        suggestions.append("Check item quality and condition — issues reported.")
    
    # Operational tasks
    if document_status == "scanned":
        suggestions.append("Review scanned invoice for accuracy before processing.")
    elif document_status == "needs_review":
        suggestions.append("Invoice needs review — check for missing or incorrect items.")
    
    # Perishable goods
    perishable_issues = [issue for issue in flagged_issues if 'perishable' in issue.get('message', '').lower()]
    if perishable_issues:
        suggestions.append("Perishable goods detected — ensure proper storage and rotation.")
    
    return suggestions

def _get_default_suggestions(document_status: str, confidence: float, flagged_issues: List[Dict]) -> List[str]:
    """
    Generate default suggestions for unknown roles.
    
    Args:
        document_status: Document status
        confidence: Confidence score
        flagged_issues: List of flagged issues
        
    Returns:
        List of default suggestions
    """
    suggestions = []
    
    # General suggestions
    if confidence < 70:
        suggestions.append(f"Review this invoice — confidence is low ({confidence:.1f}%).")
    
    if flagged_issues:
        suggestions.append(f"Review {len(flagged_issues)} flagged issues before approval.")
    
    if document_status == "needs_review":
        suggestions.append("This invoice requires manual review.")
    
    return suggestions

def _get_status_specific_suggestions(document_status: str, confidence: float, flagged_issues: List[Dict]) -> List[str]:
    """
    Generate suggestions based on document status.
    
    Args:
        document_status: Document status
        confidence: Confidence score
        flagged_issues: List of flagged issues
        
    Returns:
        List of status-specific suggestions
    """
    suggestions = []
    
    if document_status == "pending":
        suggestions.append("Invoice is pending processing — wait for completion before review.")
    
    elif document_status == "scanned":
        if confidence < 80:
            suggestions.append("OCR processing complete — review extracted data for accuracy.")
        else:
            suggestions.append("Invoice scanned successfully — proceed with review.")
    
    elif document_status == "needs_review":
        suggestions.append("Invoice flagged for manual review — address issues before approval.")
        
        critical_issues = [issue for issue in flagged_issues if issue.get('severity') == 'critical']
        if critical_issues:
            suggestions.append(f"Critical issues detected — immediate attention required.")
    
    elif document_status == "matched":
        if flagged_issues:
            suggestions.append("Invoice matched but has flagged issues — review before final approval.")
        else:
            suggestions.append("Invoice matched successfully — ready for approval.")
    
    return suggestions

def _get_confidence_specific_suggestions(confidence: float, flagged_issues: List[Dict]) -> List[str]:
    """
    Generate suggestions based on confidence score.
    
    Args:
        confidence: Confidence score
        flagged_issues: List of flagged issues
        
    Returns:
        List of confidence-specific suggestions
    """
    suggestions = []
    
    if confidence < 50:
        suggestions.append("Very low confidence — manual review strongly recommended.")
        suggestions.append("Check OCR quality and invoice clarity.")
    
    elif confidence < 70:
        suggestions.append("Low confidence — review extracted data carefully.")
        suggestions.append("Verify line items and totals manually.")
    
    elif confidence < 85:
        suggestions.append("Moderate confidence — review recommended.")
    
    elif confidence >= 85:
        if flagged_issues:
            suggestions.append("High confidence but issues detected — review flagged items.")
        else:
            suggestions.append("High confidence — invoice appears to be in good condition.")
    
    return suggestions

def _get_issue_specific_suggestions(flagged_issues: List[Dict], user_role: str) -> List[str]:
    """
    Generate suggestions based on specific issue types.
    
    Args:
        flagged_issues: List of flagged issues
        user_role: User's role
        
    Returns:
        List of issue-specific suggestions
    """
    suggestions = []
    
    # Group issues by type
    issue_types = {}
    for issue in flagged_issues:
        issue_type = issue.get('type', 'unknown')
        if issue_type not in issue_types:
            issue_types[issue_type] = []
        issue_types[issue_type].append(issue)
    
    # Price issues
    if 'price_increase' in issue_types:
        price_issues = issue_types['price_increase']
        if len(price_issues) == 1:
            suggestions.append("Price increase detected — verify with supplier.")
        else:
            suggestions.append(f"{len(price_issues)} price increases detected — review supplier pricing.")
    
    # Delivery issues
    if 'missing_delivery_note' in issue_types:
        if user_role.lower() == "shift lead":
            suggestions.append("No delivery note found — check if delivery was received.")
        else:
            suggestions.append("Missing delivery note — request from supplier.")
    
    # Quantity issues
    if 'quantity_mismatch' in issue_types:
        suggestions.append("Quantity discrepancies detected — verify received amounts.")
    
    # Quality issues
    if 'data_quality' in issue_types:
        suggestions.append("Data quality issues detected — review OCR results.")
    
    # Supplier issues
    if 'supplier_escalation' in issue_types:
        suggestions.append("Supplier performance issues — consider escalation.")
    
    return suggestions

def get_suggestion_priority(suggestion: str) -> int:
    """
    Determine the priority of a suggestion for sorting.
    
    Args:
        suggestion: Suggestion text
        
    Returns:
        Priority level (1=high, 2=medium, 3=low)
    """
    high_priority_keywords = ['critical', 'immediate', 'strongly recommended', 'escalation']
    medium_priority_keywords = ['review', 'verify', 'check', 'attention']
    
    suggestion_lower = suggestion.lower()
    
    if any(keyword in suggestion_lower for keyword in high_priority_keywords):
        return 1
    elif any(keyword in suggestion_lower for keyword in medium_priority_keywords):
        return 2
    else:
        return 3

def format_suggestions_for_ui(suggestions: List[str]) -> List[Dict[str, Any]]:
    """
    Format suggestions for UI display with metadata.
    
    Args:
        suggestions: List of suggestion strings
        
    Returns:
        List of formatted suggestion dictionaries
    """
    formatted_suggestions = []
    
    for suggestion in suggestions:
        priority = get_suggestion_priority(suggestion)
        
        formatted_suggestion = {
            "text": suggestion,
            "priority": priority,
            "priority_label": "high" if priority == 1 else "medium" if priority == 2 else "low",
            "category": _categorize_suggestion(suggestion),
            "actionable": _is_actionable_suggestion(suggestion)
        }
        
        formatted_suggestions.append(formatted_suggestion)
    
    # Sort by priority (high to low)
    formatted_suggestions.sort(key=lambda x: x['priority'])
    
    return formatted_suggestions

def _categorize_suggestion(suggestion: str) -> str:
    """
    Categorize a suggestion based on its content.
    
    Args:
        suggestion: Suggestion text
        
    Returns:
        Category string
    """
    suggestion_lower = suggestion.lower()
    
    if any(keyword in suggestion_lower for keyword in ['price', 'pricing', 'cost']):
        return "pricing"
    elif any(keyword in suggestion_lower for keyword in ['delivery', 'delivered', 'received']):
        return "delivery"
    elif any(keyword in suggestion_lower for keyword in ['quality', 'ocr', 'data']):
        return "quality"
    elif any(keyword in suggestion_lower for keyword in ['supplier', 'escalation']):
        return "supplier"
    elif any(keyword in suggestion_lower for keyword in ['review', 'verify', 'check']):
        return "review"
    else:
        return "general"

def _is_actionable_suggestion(suggestion: str) -> bool:
    """
    Determine if a suggestion is actionable.
    
    Args:
        suggestion: Suggestion text
        
    Returns:
        True if actionable, False otherwise
    """
    action_keywords = ['upload', 'flag', 'check', 'verify', 'review', 'contact', 'request', 'add']
    suggestion_lower = suggestion.lower()
    
    return any(keyword in suggestion_lower for keyword in action_keywords)


if __name__ == "__main__":
    # Test the role-aware suggestions engine
    logging.basicConfig(level=logging.INFO)
    
    # Test scenarios
    test_scenarios = [
        {
            "user_role": "Finance",
            "document_status": "needs_review",
            "confidence": 65.0,
            "flagged_issues": [
                {
                    "type": "price_increase",
                    "severity": "warning",
                    "field": "line_items[0].unit_price",
                    "message": "Price increased 25% above average"
                },
                {
                    "type": "missing_delivery_note",
                    "severity": "warning",
                    "field": "delivery_note",
                    "message": "No delivery note found"
                }
            ]
        },
        {
            "user_role": "Shift Lead",
            "document_status": "scanned",
            "confidence": 85.0,
            "flagged_issues": [
                {
                    "type": "missing_delivery_note",
                    "severity": "warning",
                    "field": "delivery_note",
                    "message": "No delivery note found"
                }
            ]
        },
        {
            "user_role": "GM",
            "document_status": "needs_review",
            "confidence": 45.0,
            "flagged_issues": [
                {
                    "type": "critical_price_increase",
                    "severity": "critical",
                    "field": "line_items[0].unit_price",
                    "message": "Critical price increase detected"
                },
                {
                    "type": "supplier_escalation",
                    "severity": "critical",
                    "field": "supplier",
                    "message": "Multiple issues with this supplier"
                }
            ]
        }
    ]
    
    print("🎯 Role-Aware Suggestions Test Results:")
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{i}. {scenario['user_role']} - {scenario['document_status']} (Confidence: {scenario['confidence']:.1f}%)")
        
        suggestions = get_role_aware_suggestions(
            scenario['user_role'],
            scenario['document_status'],
            scenario['confidence'],
            scenario['flagged_issues']
        )
        
        print(f"   Generated {len(suggestions)} suggestions:")
        for j, suggestion in enumerate(suggestions, 1):
            print(f"   {j}. {suggestion}")
        
        # Test formatting
        formatted = format_suggestions_for_ui(suggestions)
        print(f"   Formatted for UI: {len(formatted)} suggestions with priority levels")
    
    print("\n✅ Test completed successfully") 