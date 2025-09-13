"""
Agent-Powered Supplier Summary Generator

This module provides logic for generating comprehensive supplier issue summaries
based on scanned invoices, flagged items, and credit suggestions.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)

class SupplierSummary:
    """Container for supplier summary data."""
    
    def __init__(
        self,
        supplier_id: str,
        supplier_name: str,
        total_invoices: int,
        total_flagged_items: int,
        estimated_credit: float,
        common_issues: List[str],
        top_flagged_items: List[str],
        flagged_dates: List[str],
        summary_message: str,
        date_range: Dict[str, str],
        credit_breakdown: List[Dict[str, Any]] = None
    ):
        self.supplier_id = supplier_id
        self.supplier_name = supplier_name
        self.total_invoices = total_invoices
        self.total_flagged_items = total_flagged_items
        self.estimated_credit = estimated_credit
        self.common_issues = common_issues
        self.top_flagged_items = top_flagged_items
        self.flagged_dates = flagged_dates
        self.summary_message = summary_message
        self.date_range = date_range
        self.credit_breakdown = credit_breakdown or []

class InvoiceData:
    """Container for invoice data."""
    
    def __init__(
        self,
        invoice_id: str,
        invoice_number: str,
        invoice_date: str,
        total_amount: float,
        status: str,
        line_items: List[Dict[str, Any]]
    ):
        self.invoice_id = invoice_id
        self.invoice_number = invoice_number
        self.invoice_date = invoice_date
        self.total_amount = total_amount
        self.status = status
        self.line_items = line_items

class FlaggedItem:
    """Container for flagged item data."""
    
    def __init__(
        self,
        item_id: str,
        item_name: str,
        invoice_id: str,
        invoice_date: str,
        issue_type: str,
        quantity: int,
        unit_price: float,
        total: float,
        notes: str,
        suggested_credit: Optional[float] = None
    ):
        self.item_id = item_id
        self.item_name = item_name
        self.invoice_id = invoice_id
        self.invoice_date = invoice_date
        self.issue_type = issue_type
        self.quantity = quantity
        self.unit_price = unit_price
        self.total = total
        self.notes = notes
        self.suggested_credit = suggested_credit

def get_supplier_invoices(supplier_id: str, date_range: Dict[str, str]) -> List[InvoiceData]:
    """
    Get all invoices for a supplier within the date range.
    
    Args:
        supplier_id: The supplier ID
        date_range: Dictionary with 'from' and 'to' dates
        
    Returns:
        List of InvoiceData objects
    """
    try:
        # In a real implementation, this would query the database
        # For now, we'll return mock data based on supplier ID
        
        import hashlib
        hash_obj = hashlib.md5(supplier_id.encode())
        hash_int = int(hash_obj.hexdigest()[:8], 16)
        
        # Generate realistic mock invoice data
        num_invoices = (hash_int % 50) + 10  # 10-60 invoices
        invoices = []
        
        for i in range(num_invoices):
            # Generate date within range
            from_date = datetime.strptime(date_range['from'], '%Y-%m-%d')
            to_date = datetime.strptime(date_range['to'], '%Y-%m-%d')
            days_range = (to_date - from_date).days
            invoice_date = from_date + timedelta(days=hash_int % days_range)
            
            # Generate line items
            num_line_items = (hash_int % 8) + 2  # 2-10 line items
            line_items = []
            
            for j in range(num_line_items):
                line_items.append({
                    'id': f"item_{i}_{j}",
                    'name': f"Item {j+1}",
                    'quantity': (hash_int % 20) + 1,
                    'unit_price': (hash_int % 50) + 5,
                    'total': (hash_int % 100) + 10,
                    'status': 'normal' if hash_int % 4 != 0 else 'flagged'
                })
            
            invoices.append(InvoiceData(
                invoice_id=f"INV-{hash_int:06d}-{i:03d}",
                invoice_number=f"INV-{hash_int:06d}-{i:03d}",
                invoice_date=invoice_date.strftime('%Y-%m-%d'),
                total_amount=(hash_int % 500) + 50,
                status='reviewed' if hash_int % 3 != 0 else 'flagged',
                line_items=line_items
            ))
        
        logger.debug(f"📊 Retrieved {len(invoices)} invoices for supplier {supplier_id}")
        return invoices
        
    except Exception as e:
        logger.error(f"❌ Error getting invoices for supplier {supplier_id}: {str(e)}")
        return []

def get_flagged_items(supplier_id: str, date_range: Dict[str, str]) -> List[FlaggedItem]:
    """
    Get all flagged items for a supplier within the date range.
    
    Args:
        supplier_id: The supplier ID
        date_range: Dictionary with 'from' and 'to' dates
        
    Returns:
        List of FlaggedItem objects
    """
    try:
        # In a real implementation, this would query the database
        # For now, we'll return mock data based on supplier ID
        
        import hashlib
        hash_obj = hashlib.md5(supplier_id.encode())
        hash_int = int(hash_obj.hexdigest()[:8], 16)
        
        # Generate realistic mock flagged items
        num_flagged_items = (hash_int % 20) + 3  # 3-23 flagged items
        flagged_items = []
        
        # Sample item names
        item_names = [
            "Toilet Roll 2ply", "House Red 12x750ml", "Beef Steaks", 
            "Chicken Breast", "Olive Oil", "Tomatoes", "Onions",
            "Potatoes", "Carrots", "Lettuce", "Bread", "Milk"
        ]
        
        issue_types = ["missing", "mismatched", "flagged", "overcharged"]
        
        for i in range(num_flagged_items):
            # Generate date within range
            from_date = datetime.strptime(date_range['from'], '%Y-%m-%d')
            to_date = datetime.strptime(date_range['to'], '%Y-%m-%d')
            days_range = (to_date - from_date).days
            item_date = from_date + timedelta(days=(hash_int + i) % days_range)
            
            item_name = item_names[hash_int % len(item_names)]
            issue_type = issue_types[hash_int % len(issue_types)]
            quantity = (hash_int % 10) + 1
            unit_price = (hash_int % 20) + 2
            total = quantity * unit_price
            suggested_credit = total * 0.8 if issue_type in ["missing", "mismatched"] else total * 0.2
            
            flagged_items.append(FlaggedItem(
                item_id=f"item_{hash_int}_{i}",
                item_name=item_name,
                invoice_id=f"INV-{hash_int:06d}-{i:03d}",
                invoice_date=item_date.strftime('%Y-%m-%d'),
                issue_type=issue_type,
                quantity=quantity,
                unit_price=unit_price,
                total=total,
                notes=f"{issue_type.capitalize()} item detected",
                suggested_credit=round(suggested_credit, 2)
            ))
        
        logger.debug(f"📊 Retrieved {len(flagged_items)} flagged items for supplier {supplier_id}")
        return flagged_items
        
    except Exception as e:
        logger.error(f"❌ Error getting flagged items for supplier {supplier_id}: {str(e)}")
        return []

def analyze_common_issues(flagged_items: List[FlaggedItem]) -> List[str]:
    """
    Analyze flagged items to identify common issues.
    
    Args:
        flagged_items: List of FlaggedItem objects
        
    Returns:
        List of common issue descriptions
    """
    if not flagged_items:
        return []
    
    # Count issue types
    issue_counts = Counter(item.issue_type for item in flagged_items)
    
    # Map issue types to human-readable descriptions
    issue_descriptions = {
        'missing': 'Missing items',
        'mismatched': 'Quantity mismatches',
        'flagged': 'Price discrepancies',
        'overcharged': 'Overcharged items',
        'short_delivery': 'Short deliveries',
        'quality_issue': 'Quality issues'
    }
    
    # Get top 3 most common issues
    common_issues = []
    for issue_type, count in issue_counts.most_common(3):
        if issue_type in issue_descriptions:
            common_issues.append(issue_descriptions[issue_type])
    
    return common_issues

def get_top_flagged_items(flagged_items: List[FlaggedItem], limit: int = 5) -> List[str]:
    """
    Get the most frequently flagged items.
    
    Args:
        flagged_items: List of FlaggedItem objects
        limit: Maximum number of items to return
        
    Returns:
        List of top flagged item names
    """
    if not flagged_items:
        return []
    
    # Count item occurrences
    item_counts = Counter(item.item_name for item in flagged_items)
    
    # Return top items
    return [item_name for item_name, count in item_counts.most_common(limit)]

def generate_summary_message(
    supplier_name: str,
    total_invoices: int,
    total_flagged_items: int,
    estimated_credit: float,
    date_range: Dict[str, str],
    common_issues: List[str]
) -> str:
    """
    Generate a human-readable summary message.
    
    Args:
        supplier_name: The supplier name
        total_invoices: Total number of invoices
        total_flagged_items: Total number of flagged items
        estimated_credit: Estimated credit amount
        date_range: Date range dictionary
        common_issues: List of common issues
        
    Returns:
        Formatted summary message
    """
    from_date = datetime.strptime(date_range['from'], '%Y-%m-%d')
    to_date = datetime.strptime(date_range['to'], '%Y-%m-%d')
    
    # Format dates
    from_date_str = from_date.strftime('%B %d')
    to_date_str = to_date.strftime('%B %d, %Y')
    
    # Build message
    message_parts = [
        f"Between {from_date_str} and {to_date_str}, we observed {total_flagged_items} flagged items"
    ]
    
    if total_invoices > 1:
        message_parts.append(f"across {total_invoices} invoices from {supplier_name}")
    else:
        message_parts.append(f"in 1 invoice from {supplier_name}")
    
    if estimated_credit > 0:
        message_parts.append(f"Estimated credits due: £{estimated_credit:.2f}")
    
    if common_issues:
        issues_text = ", ".join(common_issues[:-1])
        if len(common_issues) > 1:
            issues_text += f" and {common_issues[-1]}"
        else:
            issues_text = common_issues[0]
        message_parts.append(f"The most common issues were {issues_text}.")
    
    message_parts.append("Please review the attached list.")
    
    return " ".join(message_parts)

def generate_supplier_summary(
    supplier_id: str,
    supplier_name: str,
    date_range: Dict[str, str]
) -> Optional[SupplierSummary]:
    """
    Generate a comprehensive supplier summary.
    
    Args:
        supplier_id: The supplier ID
        supplier_name: The supplier name
        date_range: Dictionary with 'from' and 'to' dates
        
    Returns:
        SupplierSummary object or None if error
    """
    try:
        logger.info(f"🔍 Generating supplier summary for {supplier_name} ({supplier_id})")
        
        # Get invoices and flagged items
        invoices = get_supplier_invoices(supplier_id, date_range)
        flagged_items = get_flagged_items(supplier_id, date_range)
        
        if not invoices and not flagged_items:
            logger.info(f"✅ No data found for supplier {supplier_name}")
            return None
        
        # Calculate totals
        total_invoices = len(invoices)
        total_flagged_items = len(flagged_items)
        estimated_credit = sum(item.suggested_credit or 0 for item in flagged_items)
        
        # Analyze patterns
        common_issues = analyze_common_issues(flagged_items)
        top_flagged_items = get_top_flagged_items(flagged_items)
        
        # Get unique flagged dates
        flagged_dates = sorted(list(set(item.invoice_date for item in flagged_items)))
        
        # Generate summary message
        summary_message = generate_summary_message(
            supplier_name,
            total_invoices,
            total_flagged_items,
            estimated_credit,
            date_range,
            common_issues
        )
        
        # Create credit breakdown
        credit_breakdown = []
        for item in flagged_items:
            if item.suggested_credit:
                credit_breakdown.append({
                    'item_name': item.item_name,
                    'invoice_id': item.invoice_id,
                    'issue_type': item.issue_type,
                    'suggested_credit': item.suggested_credit,
                    'date': item.invoice_date
                })
        
        summary = SupplierSummary(
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            total_invoices=total_invoices,
            total_flagged_items=total_flagged_items,
            estimated_credit=round(estimated_credit, 2),
            common_issues=common_issues,
            top_flagged_items=top_flagged_items,
            flagged_dates=flagged_dates,
            summary_message=summary_message,
            date_range=date_range,
            credit_breakdown=credit_breakdown
        )
        
        logger.info(f"✅ Generated supplier summary for {supplier_name}")
        logger.info(f"   📊 {total_invoices} invoices, {total_flagged_items} flagged items")
        logger.info(f"   💰 Estimated credit: £{estimated_credit:.2f}")
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Error generating supplier summary for {supplier_id}: {str(e)}")
        return None

def format_supplier_summary(summary: SupplierSummary) -> Dict[str, Any]:
    """
    Format a supplier summary for frontend display.
    
    Args:
        summary: SupplierSummary object
        
    Returns:
        Formatted dictionary for frontend
    """
    return {
        'supplier_id': summary.supplier_id,
        'supplier_name': summary.supplier_name,
        'total_invoices': summary.total_invoices,
        'total_flagged_items': summary.total_flagged_items,
        'estimated_credit': summary.estimated_credit,
        'common_issues': summary.common_issues,
        'top_flagged_items': summary.top_flagged_items,
        'flagged_dates': summary.flagged_dates,
        'summary_message': summary.summary_message,
        'date_range': summary.date_range,
        'credit_breakdown': summary.credit_breakdown
    }

# Convenience function for testing
def test_supplier_summary_generation():
    """Test the supplier summary generation logic."""
    
    # Test data
    supplier_id = "SUP-001"
    supplier_name = "Thomas Ridley"
    date_range = {
        'from': '2025-07-01',
        'to': '2025-07-20'
    }
    
    print("🧪 Testing supplier summary generation...")
    
    summary = generate_supplier_summary(supplier_id, supplier_name, date_range)
    
    if summary:
        print(f"📦 Supplier: {summary.supplier_name}")
        print(f"🧾 Total Invoices: {summary.total_invoices}")
        print(f"⚠️ Flagged Issues: {summary.total_flagged_items} items")
        print(f"💸 Estimated Credit Due: £{summary.estimated_credit:.2f}")
        print(f"📅 Dates Affected: {len(summary.flagged_dates)} dates")
        
        print(f"\n🛠 Common Problems:")
        for issue in summary.common_issues:
            print(f"   - {issue}")
        
        print(f"\n🔥 Top Affected Items:")
        for item in summary.top_flagged_items:
            print(f"   - {item}")
        
        print(f"\n✏️ Summary Preview:")
        print(f"   {summary.summary_message}")
        
        print(f"\n💰 Credit Breakdown:")
        for credit in summary.credit_breakdown[:3]:  # Show first 3
            print(f"   - {credit['item_name']}: £{credit['suggested_credit']:.2f}")
    else:
        print("❌ No summary generated")
    
    print("\n✅ Supplier summary test completed")

if __name__ == "__main__":
    test_supplier_summary_generation() 