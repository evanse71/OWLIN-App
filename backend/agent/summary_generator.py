"""
Summary Generator Module for Owlin Agent

Translates technical analysis flags into plain language summaries
that are easy for hospitality teams to understand and act upon.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def generate_summary(
    flags: List[Dict[str, Any]],
    confidence_score: float,
    metadata: Dict[str, Any],
    line_items: List[Dict[str, Any]]
) -> List[str]:
    """
    Generate plain language summary from analysis flags.
    
    Translates technical flags into actionable insights that hospitality
    teams can easily understand and act upon.
    
    Args:
        flags: List of analysis flags
        confidence_score: Overall confidence score (0-100)
        metadata: Invoice metadata
        line_items: List of line items
        
    Returns:
        List of plain language summary messages
    """
    logger.debug("📝 Generating plain language summary")
    
    summary = []
    
    # Add confidence-based summary
    summary.extend(_generate_confidence_summary(confidence_score))
    
    # Add critical issues first
    critical_flags = [f for f in flags if f.get('severity') == 'critical']
    if critical_flags:
        summary.extend(_generate_critical_summary(critical_flags))
    
    # Add warning issues
    warning_flags = [f for f in flags if f.get('severity') == 'warning']
    if warning_flags:
        summary.extend(_generate_warning_summary(warning_flags))
    
    # Add info issues
    info_flags = [f for f in flags if f.get('severity') == 'info']
    if info_flags:
        summary.extend(_generate_info_summary(info_flags))
    
    # Add invoice-specific insights
    summary.extend(_generate_invoice_insights(metadata, line_items))
    
    # Add action recommendations
    summary.extend(_generate_action_recommendations(flags, confidence_score))
    
    logger.debug(f"✅ Generated {len(summary)} summary messages")
    return summary

def _generate_confidence_summary(confidence_score: float) -> List[str]:
    """
    Generate summary based on confidence score.
    
    Args:
        confidence_score: Confidence score (0-100)
        
    Returns:
        List of confidence-based summary messages
    """
    summary = []
    
    if confidence_score >= 90:
        summary.append("✅ High confidence - Invoice data appears complete and accurate")
    elif confidence_score >= 75:
        summary.append("✅ Good confidence - Minor issues detected but overall reliable")
    elif confidence_score >= 60:
        summary.append("⚠️ Moderate confidence - Some issues detected, review recommended")
    elif confidence_score >= 40:
        summary.append("⚠️ Low confidence - Multiple issues detected, manual review required")
    else:
        summary.append("❌ Very low confidence - Significant issues detected, immediate review needed")
    
    return summary

def _generate_critical_summary(critical_flags: List[Dict[str, Any]]) -> List[str]:
    """
    Generate summary for critical flags.
    
    Args:
        critical_flags: List of critical severity flags
        
    Returns:
        List of critical issue summary messages
    """
    summary = []
    
    if not critical_flags:
        return summary
    
    summary.append("🚨 Critical Issues Requiring Immediate Attention:")
    
    # Group critical flags by type
    flag_types = {}
    for flag in critical_flags:
        flag_type = flag.get('type', 'unknown')
        if flag_type not in flag_types:
            flag_types[flag_type] = []
        flag_types[flag_type].append(flag)
    
    # Generate summaries for each type
    for flag_type, flags in flag_types.items():
        if flag_type == 'missing_total':
            summary.append("  • Invoice total amount is missing or £0.00 - this is critical")
        elif flag_type == 'no_line_items':
            summary.append("  • No line items found - OCR may have failed to extract data")
        elif flag_type == 'critical_price_increase':
            summary.append("  • Critical price increases detected - verify with supplier immediately")
        elif flag_type == 'high_value_no_delivery':
            summary.append("  • High-value invoice missing delivery note - request immediately")
        elif flag_type == 'analysis_failed':
            summary.append("  • Invoice analysis failed - manual review required")
        else:
            summary.append(f"  • {len(flags)} critical {flag_type.replace('_', ' ')} issues")
    
    return summary

def _generate_warning_summary(warning_flags: List[Dict[str, Any]]) -> List[str]:
    """
    Generate summary for warning flags.
    
    Args:
        warning_flags: List of warning severity flags
        
    Returns:
        List of warning issue summary messages
    """
    summary = []
    
    if not warning_flags:
        return summary
    
    summary.append("⚠️ Issues Requiring Attention:")
    
    # Group warning flags by type
    flag_types = {}
    for flag in warning_flags:
        flag_type = flag.get('type', 'unknown')
        if flag_type not in flag_types:
            flag_types[flag_type] = []
        flag_types[flag_type].append(flag)
    
    # Generate summaries for each type
    for flag_type, flags in flag_types.items():
        if flag_type == 'missing_supplier':
            summary.append("  • Supplier name not found or is 'Unknown'")
        elif flag_type == 'missing_invoice_number':
            summary.append("  • Invoice number not found or is 'Unknown'")
        elif flag_type == 'missing_date':
            summary.append("  • Invoice date not found")
        elif flag_type == 'missing_vat_amount':
            summary.append("  • VAT amount is £0.00 but VAT rate is present")
        elif flag_type == 'subtotal_mismatch':
            summary.append("  • Line items total doesn't match invoice total")
        elif flag_type == 'high_price_increase':
            summary.append("  • Significant price increases detected")
        elif flag_type == 'missing_delivery_note':
            summary.append("  • No delivery note found for this invoice")
        elif flag_type == 'future_delivery_date':
            summary.append("  • Invoice date is in the future")
        elif flag_type == 'vague_item_description':
            summary.append("  • Some line items have vague descriptions")
        elif flag_type == 'zero_quantity':
            summary.append("  • Some line items have zero quantities")
        elif flag_type == 'zero_unit_price':
            summary.append("  • Some line items have zero unit prices")
        else:
            summary.append(f"  • {len(flags)} {flag_type.replace('_', ' ')} issues")
    
    return summary

def _generate_info_summary(info_flags: List[Dict[str, Any]]) -> List[str]:
    """
    Generate summary for info flags.
    
    Args:
        info_flags: List of info severity flags
        
    Returns:
        List of info summary messages
    """
    summary = []
    
    if not info_flags:
        return summary
    
    summary.append("ℹ️ Additional Information:")
    
    # Group info flags by type
    flag_types = {}
    for flag in info_flags:
        flag_type = flag.get('type', 'unknown')
        if flag_type not in flag_types:
            flag_types[flag_type] = []
        flag_types[flag_type].append(flag)
    
    # Generate summaries for each type
    for flag_type, flags in flag_types.items():
        if flag_type == 'old_invoice':
            summary.append("  • Invoice is over 1 year old")
        elif flag_type == 'weekend_delivery':
            summary.append("  • Weekend delivery detected")
        elif flag_type == 'high_price_volatility':
            summary.append("  • High price volatility for some items")
        elif flag_type == 'very_small_quantity':
            summary.append("  • Some items have very small quantities")
        elif flag_type == 'unusually_low_price':
            summary.append("  • Some items have unusually low prices")
        else:
            summary.append(f"  • {len(flags)} {flag_type.replace('_', ' ')} notes")
    
    return summary

def _generate_invoice_insights(metadata: Dict[str, Any], line_items: List[Dict[str, Any]]) -> List[str]:
    """
    Generate invoice-specific insights.
    
    Args:
        metadata: Invoice metadata
        line_items: List of line items
        
    Returns:
        List of invoice insights
    """
    insights = []
    
    # Supplier insights
    supplier_name = metadata.get('supplier_name', '')
    if supplier_name and supplier_name != 'Unknown':
        insights.append(f"📋 Invoice from {supplier_name}")
    
    # Date insights
    invoice_date = metadata.get('invoice_date', '')
    if invoice_date:
        insights.append(f"📅 Invoice date: {invoice_date}")
    
    # Amount insights
    total_amount = metadata.get('total_amount', 0.0)
    if total_amount > 0:
        insights.append(f"💰 Total amount: £{total_amount:.2f}")
        
        # High value flag
        if total_amount > 1000:
            insights.append("💡 High-value invoice - extra attention recommended")
    
    # Line item insights
    if line_items:
        item_count = len(line_items)
        insights.append(f"📦 {item_count} line item{'s' if item_count != 1 else ''} found")
        
        # Check for variety of items
        unique_items = len(set(item.get('item', '') for item in line_items))
        if unique_items > 5:
            insights.append("🛒 Wide variety of items - typical for large orders")
        elif unique_items == 1:
            insights.append("📦 Single item invoice - verify quantity and pricing")
    
    return insights

def _generate_action_recommendations(flags: List[Dict[str, Any]], confidence_score: float) -> List[str]:
    """
    Generate action recommendations based on flags and confidence.
    
    Args:
        flags: List of analysis flags
        confidence_score: Overall confidence score
        
    Returns:
        List of action recommendations
    """
    recommendations = []
    
    # Confidence-based recommendations
    if confidence_score < 40:
        recommendations.append("🔍 Immediate Action Required: Review invoice manually and consider re-scanning")
    elif confidence_score < 60:
        recommendations.append("🔍 Manual Review Recommended: Check flagged items and verify data accuracy")
    elif confidence_score < 80:
        recommendations.append("✅ Minor Review: Verify flagged items but overall data looks good")
    else:
        recommendations.append("✅ Ready to Process: Invoice data appears complete and accurate")
    
    # Flag-based recommendations
    critical_count = len([f for f in flags if f.get('severity') == 'critical'])
    warning_count = len([f for f in flags if f.get('severity') == 'warning'])
    
    if critical_count > 0:
        recommendations.append(f"🚨 {critical_count} critical issue{'s' if critical_count != 1 else ''} need immediate attention")
    
    if warning_count > 0:
        recommendations.append(f"⚠️ {warning_count} warning{'s' if warning_count != 1 else ''} should be addressed")
    
    # Specific recommendations based on flag types
    flag_types = [f.get('type') for f in flags]
    
    if 'missing_delivery_note' in flag_types:
        recommendations.append("📦 Action: Request delivery note from supplier")
    
    if 'critical_price_increase' in flag_types or 'high_price_increase' in flag_types:
        recommendations.append("💰 Action: Contact supplier to verify price increases")
    
    if 'missing_total' in flag_types:
        recommendations.append("💳 Action: Verify total amount manually")
    
    if 'no_line_items' in flag_types:
        recommendations.append("📋 Action: Check if OCR missed line items")
    
    return recommendations

def get_summary_stats(flags: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get summary statistics for flags.
    
    Args:
        flags: List of analysis flags
        
    Returns:
        Dictionary with flag statistics
    """
    if not flags:
        return {
            "total_flags": 0,
            "critical_flags": 0,
            "warning_flags": 0,
            "info_flags": 0,
            "flag_types": {}
        }
    
    # Count by severity
    critical_count = len([f for f in flags if f.get('severity') == 'critical'])
    warning_count = len([f for f in flags if f.get('severity') == 'warning'])
    info_count = len([f for f in flags if f.get('severity') == 'info'])
    
    # Count by type
    flag_types = {}
    for flag in flags:
        flag_type = flag.get('type', 'unknown')
        flag_types[flag_type] = flag_types.get(flag_type, 0) + 1
    
    return {
        "total_flags": len(flags),
        "critical_flags": critical_count,
        "warning_flags": warning_count,
        "info_flags": info_count,
        "flag_types": flag_types
    }


if __name__ == "__main__":
    # Test summary generator
    logging.basicConfig(level=logging.INFO)
    
    # Sample flags
    sample_flags = [
        {
            "type": "missing_delivery_note",
            "severity": "warning",
            "field": "delivery_note",
            "message": "No delivery note found for this invoice",
            "suggested_action": "Request delivery note from supplier"
        },
        {
            "type": "critical_price_increase",
            "severity": "critical",
            "field": "line_items[0].unit_price",
            "message": "Critical price increase: Beef Sirloin is 25.0% above average",
            "suggested_action": "Contact supplier immediately"
        },
        {
            "type": "missing_supplier",
            "severity": "warning",
            "field": "supplier_name",
            "message": "Supplier name not found or is 'Unknown'",
            "suggested_action": "Manually verify supplier name"
        }
    ]
    
    # Sample metadata and line items
    metadata = {
        "supplier_name": "Quality Foods Ltd",
        "invoice_date": "2024-12-01",
        "total_amount": 150.00
    }
    
    line_items = [
        {
            "item": "Beef Sirloin",
            "quantity": 5.0,
            "unit_price_excl_vat": 20.00,
            "line_total_excl_vat": 100.00
        },
        {
            "item": "Chicken Breast",
            "quantity": 2.5,
            "unit_price_excl_vat": 10.00,
            "line_total_excl_vat": 25.00
        }
    ]
    
    # Generate summary
    summary = generate_summary(sample_flags, 65.0, metadata, line_items)
    
    print("📝 Summary Generation Test:")
    for message in summary:
        print(f"  {message}")
    
    # Test summary stats
    stats = get_summary_stats(sample_flags)
    print(f"\n📊 Summary Statistics:")
    print(f"  Total flags: {stats['total_flags']}")
    print(f"  Critical: {stats['critical_flags']}")
    print(f"  Warnings: {stats['warning_flags']}")
    print(f"  Info: {stats['info_flags']}")
    print(f"  Flag types: {stats['flag_types']}") 