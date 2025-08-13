"""
Owlin Agent Core Module

The main entry point for the Owlin Agent - a smart, offline-first assistant
that helps hospitality teams review, audit, and act on scanned invoice data.

This module orchestrates the analysis of invoice data and returns structured
results with confidence scores, flags, and actionable insights.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import agent submodules (to be implemented)
try:
    from .confidence_scoring import score_confidence
    from .price_checker import check_price_mismatches
    from .delivery_pairing import check_delivery_pairing
    from .summary_generator import generate_summary
except ImportError:
    # Fallback for direct execution
    from confidence_scoring import score_confidence
    from price_checker import check_price_mismatches
    from delivery_pairing import check_delivery_pairing
    from summary_generator import generate_summary

logger = logging.getLogger(__name__)

def run_owlin_agent(
    invoice_data: Dict[str, Any],
    historical_prices: Optional[Dict[str, List[float]]] = None
) -> Dict[str, Any]:
    """
    Main entry point for the Owlin Agent analysis.
    
    Orchestrates the analysis of invoice data by routing it through submodules:
    - Confidence scoring
    - Price mismatch detection
    - Delivery note verification
    - Summary generation
    
    Args:
        invoice_data: Dictionary containing invoice data with fields:
            - metadata: Dict with supplier_name, invoice_date, subtotal, vat, etc.
            - line_items: List of items with name, qty, unit price, etc.
            - delivery_note_attached: Boolean indicating if delivery note was matched
            - confidence: Float representing OCR confidence (0-100)
        historical_prices: Optional dict of past prices in format:
            {"item_name": [price1, price2, ...]}
            
    Returns:
        Dictionary with structured analysis results:
        {
            "confidence_score": float,           # 0-100 score
            "manual_review_required": bool,      # True if data quality is poor
            "flags": List[Dict],                 # List of issue flags
            "summary": List[str]                 # Human-readable messages
        }
        
    Each flag in the flags list contains:
        {
            "type": str,                        # Issue type (e.g., "missing_total", "price_mismatch")
            "severity": str,                     # "info", "warning", "critical"
            "field": str,                        # Affected field (e.g., "subtotal", "supplier_name")
            "message": str,                      # Description of the issue
            "suggested_action": str              # Recommended action
        }
    """
    logger.info("🔍 Starting Owlin Agent analysis")
    
    try:
        # Extract key components from invoice data
        metadata = invoice_data.get('metadata', {})
        line_items = invoice_data.get('line_items', [])
        delivery_note_attached = invoice_data.get('delivery_note_attached', False)
        ocr_confidence = invoice_data.get('confidence', 0.0)
        
        logger.debug(f"📄 Analyzing invoice for supplier: {metadata.get('supplier_name', 'Unknown')}")
        logger.debug(f"📋 Found {len(line_items)} line items")
        logger.debug(f"📦 Delivery note attached: {delivery_note_attached}")
        logger.debug(f"📊 OCR confidence: {ocr_confidence:.1f}%")
        
        # Step 1: Score confidence based on data quality
        confidence_result = score_confidence(
            metadata=metadata,
            line_items=line_items,
            ocr_confidence=ocr_confidence
        )
        
        # Step 2: Check for price mismatches against historical data
        price_flags = check_price_mismatches(
            line_items=line_items,
            historical_prices=historical_prices or {}
        )
        
        # Step 3: Analyze delivery note pairing
        delivery_flags = check_delivery_pairing(
            delivery_note_attached=delivery_note_attached,
            line_items=line_items,
            metadata=metadata
        )
        
        # Step 4: Generate human-readable summary
        all_flags = confidence_result.get('flags', []) + price_flags + delivery_flags
        summary = generate_summary(
            flags=all_flags,
            confidence_score=confidence_result.get('score', 0.0),
            metadata=metadata,
            line_items=line_items
        )
        
        # Step 5: Compile final results
        result = {
            "confidence_score": confidence_result.get('score', 0.0),
            "manual_review_required": confidence_result.get('manual_review_required', True),
            "flags": all_flags,
            "summary": summary,
            "analysis_timestamp": datetime.now().isoformat(),
            "agent_version": "1.0.0"
        }
        
        logger.info(f"✅ Analysis completed. Confidence: {result['confidence_score']:.1f}%")
        logger.info(f"🚩 Found {len(all_flags)} flags")
        logger.info(f"📝 Generated {len(summary)} summary messages")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Owlin Agent analysis failed: {str(e)}")
        # Return fallback result with critical error flag
        return _create_fallback_result(invoice_data, str(e))

def _create_fallback_result(invoice_data: Dict[str, Any], error_message: str) -> Dict[str, Any]:
    """
    Create a fallback result when analysis fails.
    
    Args:
        invoice_data: Original invoice data
        error_message: Description of what went wrong
        
    Returns:
        Fallback analysis result with critical error flag
    """
    return {
        "confidence_score": 0.0,
        "manual_review_required": True,
        "flags": [
            {
                "type": "analysis_failed",
                "severity": "critical",
                "field": "agent_analysis",
                "message": f"Invoice analysis failed: {error_message}",
                "suggested_action": "Review invoice manually and re-upload if needed."
            }
        ],
        "summary": [
            "⚠️ Invoice analysis failed",
            "Please review this invoice manually",
            "Consider re-uploading if OCR quality is poor"
        ],
        "analysis_timestamp": datetime.now().isoformat(),
        "agent_version": "1.0.0"
    }

def get_agent_info() -> Dict[str, Any]:
    """
    Get information about the Owlin Agent and its capabilities.
    
    Returns:
        Dictionary with agent information
    """
    return {
        "name": "Owlin Agent",
        "version": "1.0.0",
        "description": "Smart invoice analysis assistant for hospitality teams",
        "capabilities": [
            "Confidence scoring based on data quality",
            "Price mismatch detection against historical data",
            "Delivery note pairing analysis",
            "Manual review recommendations",
            "Plain language summaries"
        ],
        "offline_capable": True,
        "last_updated": datetime.now().isoformat()
    }

# Convenience function for easy integration
def analyze_invoice(
    invoice_data: Dict[str, Any],
    historical_prices: Optional[Dict[str, List[float]]] = None
) -> Dict[str, Any]:
    """
    Convenience function to analyze a single invoice.
    
    Args:
        invoice_data: Dictionary containing invoice metadata and line items
        historical_prices: Optional dict of recent prices for comparison
        
    Returns:
        Dictionary with confidence score, flags, and summary
    """
    return run_owlin_agent(invoice_data, historical_prices)


if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(level=logging.INFO)
    
    # Sample invoice data
    sample_invoice = {
        "metadata": {
            "supplier_name": "Sample Supplier",
            "invoice_number": "INV-001",
            "invoice_date": "2024-12-01",
            "total_amount": 150.00,
            "subtotal": 125.00,
            "vat": 25.00,
            "vat_rate": 20.0
        },
        "line_items": [
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
        ],
        "delivery_note_attached": True,
        "confidence": 85.0
    }
    
    # Sample historical prices
    sample_historical_prices = {
        "Beef Sirloin": [18.50, 19.00, 20.50, 21.00, 20.00],
        "Chicken Breast": [9.50, 10.00, 10.50, 11.00, 10.25]
    }
    
    # Test the agent
    result = run_owlin_agent(sample_invoice, sample_historical_prices)
    
    print("🔍 Owlin Agent Test Results:")
    print(f"Confidence Score: {result['confidence_score']:.1f}%")
    print(f"Manual Review Required: {result['manual_review_required']}")
    print(f"Flags Found: {len(result['flags'])}")
    print(f"Summary: {result['summary']}")
    
    # Print agent info
    agent_info = get_agent_info()
    print(f"\n🤖 Agent Info: {agent_info['name']} v{agent_info['version']}")
    print(f"Capabilities: {', '.join(agent_info['capabilities'])}") 