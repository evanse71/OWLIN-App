"""
Health Metrics API

Provides comprehensive health monitoring and metrics.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from db_manager_unified import get_db_manager
from flask import Blueprint, jsonify

logger = logging.getLogger(__name__)

router = APIRouter()

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"ok": True})

@router.get("/api/health/post_ocr")
async def get_post_ocr_health() -> Dict[str, Any]:
    """
    Get comprehensive health metrics for post-OCR processing.
    
    Returns:
        Health status with detailed metrics
    """
    try:
        db_manager = get_db_manager()
        
        # Get 24h metrics
        flags_24h = _get_flags_24h(db_manager)
        avg_line_flags_per_invoice_24h = _get_avg_line_flags_per_invoice_24h(db_manager)
        pairing_suggestion_rate_24h = _get_pairing_suggestion_rate_24h(db_manager)
        
        # Determine overall status
        status = _determine_health_status(flags_24h, avg_line_flags_per_invoice_24h)
        
        # Build response
        response = {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "flags_24h": flags_24h,
                "avg_line_flags_per_invoice_24h": avg_line_flags_per_invoice_24h,
                "pairing_suggestion_rate_24h": pairing_suggestion_rate_24h
            },
            "violations": _get_health_violations(flags_24h, avg_line_flags_per_invoice_24h)
        }
        
        logger.info(f"Health check: {status}")
        return response
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

def _get_flags_24h(db_manager) -> Dict[str, int]:
    """Get flag counts for the last 24 hours"""
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get invoices from last 24h
            cursor.execute("""
                SELECT COUNT(*) FROM invoices 
                WHERE uploaded_at >= datetime('now', '-1 day')
            """)
            total_invoices = cursor.fetchone()[0] or 0
            
            if total_invoices == 0:
                return {
                    "PRICE_INCOHERENT": 0,
                    "VAT_MISMATCH": 0,
                    "PACK_MISMATCH": 0,
                    "OCR_LOW_CONF": 0,
                    "OFF_CONTRACT_DISCOUNT": 0
                }
            
            # Get flag counts (assuming flags are stored in JSON format)
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN json_extract(validation_flags, '$.PRICE_INCOHERENT') = 1 THEN 1 ELSE 0 END) as price_incoherent,
                    SUM(CASE WHEN json_extract(validation_flags, '$.VAT_MISMATCH') = 1 THEN 1 ELSE 0 END) as vat_mismatch,
                    SUM(CASE WHEN json_extract(validation_flags, '$.PACK_MISMATCH') = 1 THEN 1 ELSE 0 END) as pack_mismatch,
                    SUM(CASE WHEN json_extract(validation_flags, '$.OCR_LOW_CONF') = 1 THEN 1 ELSE 0 END) as ocr_low_conf,
                    SUM(CASE WHEN json_extract(validation_flags, '$.OFF_CONTRACT_DISCOUNT') = 1 THEN 1 ELSE 0 END) as off_contract_discount
                FROM invoices 
                WHERE uploaded_at >= datetime('now', '-1 day')
            """)
            
            row = cursor.fetchone()
            return {
                "PRICE_INCOHERENT": row[0] or 0,
                "VAT_MISMATCH": row[1] or 0,
                "PACK_MISMATCH": row[2] or 0,
                "OCR_LOW_CONF": row[3] or 0,
                "OFF_CONTRACT_DISCOUNT": row[4] or 0
            }
            
    except Exception as e:
        logger.error(f"❌ Failed to get flags 24h: {e}")
        return {
            "PRICE_INCOHERENT": 0,
            "VAT_MISMATCH": 0,
            "PACK_MISMATCH": 0,
            "OCR_LOW_CONF": 0,
            "OFF_CONTRACT_DISCOUNT": 0
        }

def _get_avg_line_flags_per_invoice_24h(db_manager) -> float:
    """Get average line flags per invoice for last 24h"""
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Count total line flags in last 24h
            cursor.execute("""
                SELECT COUNT(*) FROM invoice_line_items ili
                JOIN invoices i ON ili.invoice_id = i.id
                WHERE i.uploaded_at >= datetime('now', '-1 day')
                AND (ili.line_flags IS NOT NULL AND ili.line_flags != '[]')
            """)
            
            flagged_lines = cursor.fetchone()[0] or 0
            
            # Count total invoices in last 24h
            cursor.execute("""
                SELECT COUNT(*) FROM invoices 
                WHERE uploaded_at >= datetime('now', '-1 day')
            """)
            
            total_invoices = cursor.fetchone()[0] or 0
            
            if total_invoices == 0:
                return 0.0
            
            return round(flagged_lines / total_invoices, 2)
            
    except Exception as e:
        logger.error(f"❌ Failed to get avg line flags: {e}")
        return 0.0

def _get_pairing_suggestion_rate_24h(db_manager) -> float:
    """Get pairing suggestion rate for last 24h"""
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Count pairing suggestions in last 24h
            cursor.execute("""
                SELECT COUNT(*) FROM pairing_suggestions 
                WHERE created_at >= datetime('now', '-1 day')
            """)
            
            suggestions = cursor.fetchone()[0] or 0
            
            # Count delivery notes in last 24h
            cursor.execute("""
                SELECT COUNT(*) FROM delivery_notes 
                WHERE uploaded_at >= datetime('now', '-1 day')
            """)
            
            delivery_notes = cursor.fetchone()[0] or 0
            
            if delivery_notes == 0:
                return 0.0
            
            return round(suggestions / delivery_notes, 2)
            
    except Exception as e:
        logger.error(f"❌ Failed to get pairing suggestion rate: {e}")
        return 0.0

def _determine_health_status(flags_24h: Dict[str, int], avg_line_flags: float) -> str:
    """Determine overall health status"""
    try:
        # Check for critical flags
        critical_flags = flags_24h.get("PRICE_INCOHERENT", 0) + flags_24h.get("VAT_MISMATCH", 0)
        
        if critical_flags > 0:
            return "critical"
        
        # Check for high flag rates
        total_flags = sum(flags_24h.values())
        if total_flags > 10 or avg_line_flags > 2.0:
            return "degraded"
        
        return "healthy"
        
    except Exception as e:
        logger.error(f"❌ Health status determination failed: {e}")
        return "unknown"

def _get_health_violations(flags_24h: Dict[str, int], avg_line_flags: float) -> List[str]:
    """Get list of health violations"""
    violations = []
    
    try:
        # Check for critical violations
        if flags_24h.get("PRICE_INCOHERENT", 0) > 0:
            violations.append(f"Price incoherent detected: {flags_24h['PRICE_INCOHERENT']} invoices")
        
        if flags_24h.get("VAT_MISMATCH", 0) > 0:
            violations.append(f"VAT mismatch detected: {flags_24h['VAT_MISMATCH']} invoices")
        
        # Check for high flag rates
        total_flags = sum(flags_24h.values())
        if total_flags > 10:
            violations.append(f"High flag rate: {total_flags} flags in 24h")
        
        if avg_line_flags > 2.0:
            violations.append(f"High line flag rate: {avg_line_flags} flags per invoice")
        
        return violations
        
    except Exception as e:
        logger.error(f"❌ Health violations check failed: {e}")
        return ["Health check error"]

@router.get("/api/health/system")
async def get_system_health() -> Dict[str, Any]:
    """Get basic system health status"""
    try:
        db_manager = get_db_manager()
        
        # Test database connection
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM invoices")
            invoice_count = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(*) FROM delivery_notes")
            delivery_count = cursor.fetchone()[0] or 0
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "invoices_count": invoice_count,
            "delivery_notes_count": delivery_count
        }
        
    except Exception as e:
        logger.error(f"❌ System health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "database": "disconnected",
            "error": str(e)
        } 