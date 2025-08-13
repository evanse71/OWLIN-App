"""
Agent Escalation Suggestion System

This module provides logic for detecting supplier misbehavior patterns
and suggesting escalation when thresholds are crossed.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SupplierMetrics:
    """Container for supplier performance metrics."""
    
    def __init__(
        self,
        supplier_id: str,
        supplier_name: str,
        mismatch_rate: float = 0.0,
        avg_confidence: float = 100.0,
        late_delivery_rate: float = 0.0,
        flagged_issue_count: int = 0,
        total_invoices: int = 0,
        recent_issues: List[str] = None
    ):
        self.supplier_id = supplier_id
        self.supplier_name = supplier_name
        self.mismatch_rate = mismatch_rate
        self.avg_confidence = avg_confidence
        self.late_delivery_rate = late_delivery_rate
        self.flagged_issue_count = flagged_issue_count
        self.total_invoices = total_invoices
        self.recent_issues = recent_issues or []

def should_escalate_supplier(supplier_metrics: SupplierMetrics) -> Tuple[bool, str]:
    """
    Determine if a supplier should be escalated based on their metrics.
    
    Args:
        supplier_metrics: SupplierMetrics object containing performance data
        
    Returns:
        Tuple of (should_escalate: bool, reason: str)
    """
    escalation_reasons = []
    
    # Check mismatch rate threshold
    if supplier_metrics.mismatch_rate > 25 and supplier_metrics.total_invoices >= 3:
        escalation_reasons.append(
            f"High delivery mismatch rate ({supplier_metrics.mismatch_rate:.1f}%)"
        )
    
    # Check average confidence threshold
    if supplier_metrics.avg_confidence < 60:
        escalation_reasons.append(
            f"Low average confidence ({supplier_metrics.avg_confidence:.1f}%)"
        )
    
    # Check late delivery rate threshold
    if supplier_metrics.late_delivery_rate > 40:
        escalation_reasons.append(
            f"High late delivery rate ({supplier_metrics.late_delivery_rate:.1f}%)"
        )
    
    # Check flagged issue count threshold
    if supplier_metrics.flagged_issue_count >= 5:
        escalation_reasons.append(
            f"Multiple flagged issues ({supplier_metrics.flagged_issue_count} in 30 days)"
        )
    
    should_escalate = len(escalation_reasons) > 0
    reason = "; ".join(escalation_reasons) if escalation_reasons else ""
    
    logger.info(f"Escalation check for {supplier_metrics.supplier_name}: {should_escalate} - {reason}")
    
    return should_escalate, reason

def get_supplier_metrics(supplier_id: str, supplier_name: str) -> SupplierMetrics:
    """
    Get supplier performance metrics from the database.
    
    Args:
        supplier_id: The supplier ID
        supplier_name: The supplier name
        
    Returns:
        SupplierMetrics object with calculated performance data
    """
    try:
        # In a real implementation, this would query the database
        # For now, we'll return mock data based on supplier ID
        
        # Mock data generation based on supplier ID
        import hashlib
        hash_obj = hashlib.md5(supplier_id.encode())
        hash_int = int(hash_obj.hexdigest()[:8], 16)
        
        # Generate realistic mock metrics
        mismatch_rate = (hash_int % 50) + 10  # 10-60%
        avg_confidence = 100 - (hash_int % 40)  # 60-100%
        late_delivery_rate = (hash_int % 60) + 5  # 5-65%
        flagged_issue_count = (hash_int % 8) + 1  # 1-8 issues
        total_invoices = (hash_int % 20) + 5  # 5-25 invoices
        
        # Generate recent issues based on metrics
        recent_issues = []
        if mismatch_rate > 25:
            recent_issues.append("Delivery quantity mismatch detected")
        if avg_confidence < 70:
            recent_issues.append("Low confidence in invoice processing")
        if late_delivery_rate > 30:
            recent_issues.append("Multiple late deliveries reported")
        if flagged_issue_count > 3:
            recent_issues.append("Multiple price discrepancies flagged")
        
        # Add some random issues
        if hash_int % 3 == 0:
            recent_issues.append("Missing items in delivery")
        if hash_int % 4 == 0:
            recent_issues.append("Incorrect pricing on multiple items")
        
        metrics = SupplierMetrics(
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            mismatch_rate=mismatch_rate,
            avg_confidence=avg_confidence,
            late_delivery_rate=late_delivery_rate,
            flagged_issue_count=flagged_issue_count,
            total_invoices=total_invoices,
            recent_issues=recent_issues
        )
        
        logger.debug(f"📊 Retrieved metrics for {supplier_name}: mismatch={mismatch_rate}%, confidence={avg_confidence}%")
        
        return metrics
        
    except Exception as e:
        logger.error(f"❌ Error getting supplier metrics for {supplier_id}: {str(e)}")
        # Return default metrics (no escalation)
        return SupplierMetrics(
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            mismatch_rate=0.0,
            avg_confidence=100.0,
            late_delivery_rate=0.0,
            flagged_issue_count=0,
            total_invoices=1,
            recent_issues=[]
        )

def check_supplier_escalation(supplier_id: str, supplier_name: str) -> Optional[Dict[str, Any]]:
    """
    Check if a supplier should be escalated and return escalation data.
    
    Args:
        supplier_id: The supplier ID
        supplier_name: The supplier name
        
    Returns:
        Escalation data dict or None if no escalation needed
    """
    try:
        # Get supplier metrics
        metrics = get_supplier_metrics(supplier_id, supplier_name)
        
        # Check if escalation is needed
        should_escalate, reason = should_escalate_supplier(metrics)
        
        if should_escalate:
            escalation_data = {
                "supplier_id": supplier_id,
                "supplier_name": supplier_name,
                "should_escalate": True,
                "reason": reason,
                "metrics": {
                    "mismatch_rate": metrics.mismatch_rate,
                    "avg_confidence": metrics.avg_confidence,
                    "late_delivery_rate": metrics.late_delivery_rate,
                    "flagged_issue_count": metrics.flagged_issue_count,
                    "total_invoices": metrics.total_invoices,
                    "recent_issues": metrics.recent_issues
                }
            }
            
            logger.info(f"🚨 Escalation suggested for {supplier_name}: {reason}")
            return escalation_data
        else:
            logger.debug(f"✅ No escalation needed for {supplier_name}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error checking supplier escalation for {supplier_id}: {str(e)}")
        return None

def get_escalation_message(supplier_name: str, metrics: Dict[str, Any]) -> str:
    """
    Generate a human-readable escalation message.
    
    Args:
        supplier_name: The supplier name
        metrics: Supplier metrics dictionary
        
    Returns:
        Formatted escalation message
    """
    primary_issue = ""
    
    if metrics["mismatch_rate"] > 25:
        primary_issue = f"{metrics['mismatch_rate']:.1f}% of their deliveries have mismatches"
    elif metrics["flagged_issue_count"] >= 5:
        primary_issue = f"{metrics['flagged_issue_count']} issues flagged in the last 30 days"
    elif metrics["late_delivery_rate"] > 40:
        primary_issue = f"{metrics['late_delivery_rate']:.1f}% of their deliveries are late"
    elif metrics["avg_confidence"] < 60:
        primary_issue = f"consistently low confidence ({metrics['avg_confidence']:.1f}%)"
    else:
        primary_issue = "multiple quality issues detected"
    
    return f"You may want to escalate {supplier_name}. {primary_issue}."

def log_escalation_action(supplier_id: str, supplier_name: str, reason: str, user_id: str) -> None:
    """
    Log an escalation action for audit purposes.
    
    Args:
        supplier_id: The supplier ID
        supplier_name: The supplier name
        reason: The escalation reason
        user_id: The user who initiated the escalation
    """
    try:
        # In a real implementation, this would log to the database
        logger.info(f"📝 Escalation logged: {supplier_name} ({supplier_id}) - {reason} by user {user_id}")
        
        # You could also send notifications, update supplier status, etc.
        
    except Exception as e:
        logger.error(f"❌ Error logging escalation for {supplier_id}: {str(e)}")

# Convenience function for testing
def test_escalation_logic():
    """Test the escalation logic with sample suppliers."""
    test_suppliers = [
        ("SUP-001", "Tom's Meats"),
        ("SUP-002", "Fresh Produce Co"),
        ("SUP-003", "Quality Beverages"),
        ("SUP-004", "Reliable Suppliers Ltd")
    ]
    
    print("🧪 Testing escalation logic...")
    
    for supplier_id, supplier_name in test_suppliers:
        escalation_data = check_supplier_escalation(supplier_id, supplier_name)
        
        if escalation_data:
            print(f"🚨 {supplier_name}: {escalation_data['reason']}")
        else:
            print(f"✅ {supplier_name}: No escalation needed")
    
    print("✅ Escalation logic test completed")

if __name__ == "__main__":
    test_escalation_logic() 