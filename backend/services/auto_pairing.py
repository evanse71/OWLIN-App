"""
Auto-pairing service for invoices and delivery notes.

Automatically pairs invoices with high-confidence delivery note suggestions.
"""
import sqlite3
import logging
from typing import Optional, Dict, Any
from backend.app.db import DB_PATH
from datetime import datetime

logger = logging.getLogger("owlin.services.auto_pairing")

# Confidence threshold for automatic pairing
# Based on existing matching logic where 0.85+ is suggested
AUTO_PAIR_THRESHOLD = 0.9


async def auto_pair_invoice_if_confident(invoice_id: str) -> Optional[Dict[str, Any]]:
    """
    For the given invoices.id:
    - Fetch suggestions from existing matching logic
    - If top suggestion has confidence >= AUTO_PAIR_THRESHOLD (0.9),
      call existing manual match logic to create the pair
    - Return info about what happened
    
    Args:
        invoice_id: The invoice ID from invoices table
        
    Returns:
        Dict with pairing result:
        - {"paired": True, "invoice_id": ..., "delivery_id": ..., "score": ...} if paired
        - {"paired": False, "reason": "below_threshold"} if not paired
        - {"paired": False, "reason": "no_suggestions"} if no suggestions
        - {"paired": False, "reason": "invoice_not_found"} if invoice doesn't exist
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get invoice details including doc_id
        cursor.execute("""
            SELECT id, doc_id, supplier, date, value, status, issues_count, paired
            FROM invoices
            WHERE id = ?
        """, (invoice_id,))
        
        inv_row = cursor.fetchone()
        if not inv_row:
            conn.close()
            logger.warning(f"Auto-pair: Invoice {invoice_id} not found")
            return {"paired": False, "reason": "invoice_not_found"}
        
        invoice_db_id = inv_row[0]
        invoice_doc_id = inv_row[1]
        is_already_paired = inv_row[7] or 0
        
        # Skip if already paired
        if is_already_paired:
            conn.close()
            logger.info(f"Auto-pair: Invoice {invoice_id} already paired, skipping")
            return {"paired": False, "reason": "already_paired"}
        
        # Check if pairs table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pairs'")
        pairs_table_exists = cursor.fetchone() is not None
        
        if not pairs_table_exists:
            conn.close()
            logger.warning("Auto-pair: Pairs table doesn't exist")
            return {"paired": False, "reason": "no_pairs_table"}
        
        # Fetch suggestions (pairs with status='suggested' for this invoice's doc_id)
        cursor.execute("""
            SELECT 
                p.id, p.invoice_id, p.delivery_id, p.confidence, p.status, p.created_at,
                d.filename as delivery_filename, d.delivery_no, d.doc_date as delivery_date,
                d.supplier as delivery_supplier, d.total as delivery_total
            FROM pairs p
            JOIN documents d ON p.delivery_id = d.id
            WHERE p.status = 'suggested' AND p.invoice_id = ?
            ORDER BY p.confidence DESC, p.created_at DESC
            LIMIT 1
        """, (invoice_doc_id,))
        
        suggestion = cursor.fetchone()
        
        if not suggestion:
            conn.close()
            logger.info(f"Auto-pair: No suggestions found for invoice {invoice_id}")
            return {"paired": False, "reason": "no_suggestions"}
        
        # Extract suggestion details
        pair_id = suggestion[0]
        delivery_id = suggestion[2]
        confidence = suggestion[3]
        
        # Check if confidence meets threshold
        if confidence < AUTO_PAIR_THRESHOLD:
            conn.close()
            logger.info(f"Auto-pair: Confidence {confidence:.2f} below threshold {AUTO_PAIR_THRESHOLD} for invoice {invoice_id}")
            return {
                "paired": False,
                "reason": "below_threshold",
                "confidence": confidence,
                "threshold": AUTO_PAIR_THRESHOLD
            }
        
        # Confidence is high enough - proceed with pairing
        logger.info(f"Auto-pair: Pairing invoice {invoice_id} with delivery note {delivery_id}, confidence: {confidence:.2f}")
        
        # Update pair status to 'accepted'
        cursor.execute("""
            UPDATE pairs
            SET status = 'accepted', decided_at = datetime('now')
            WHERE id = ?
        """, (pair_id,))
        
        # Update invoice paired status
        cursor.execute("""
            UPDATE invoices
            SET paired = 1
            WHERE id = ?
        """, (invoice_db_id,))
        
        # Run issue detection (optional - import only if available)
        issues_count = 0
        new_status = 'matched'
        try:
            from backend.services.issue_detector import detect_price_mismatch, detect_short_delivery
            
            # Detect price mismatch
            price_issue = detect_price_mismatch(invoice_db_id, delivery_id)
            
            # Detect short delivery
            short_delivery_issue = detect_short_delivery(invoice_db_id, delivery_id)
            
            # Count issues
            detected_issues = []
            if price_issue:
                detected_issues.append(price_issue)
            if short_delivery_issue:
                detected_issues.append(short_delivery_issue)
            
            issues_count = len(detected_issues)
            
            # Update invoice status based on issues
            if issues_count > 0:
                new_status = 'flagged'
            
            # Update invoice status and issues_count
            cursor.execute("""
                UPDATE invoices
                SET status = ?, issues_count = ?
                WHERE id = ?
            """, (new_status, issues_count, invoice_db_id))
            
        except ImportError:
            logger.warning("Auto-pair: Issue detector not available, skipping issue detection")
        except Exception as e:
            logger.warning(f"Auto-pair: Issue detection failed: {e}")
        
        conn.commit()
        conn.close()
        
        # Audit log
        from backend.app.db import append_audit
        append_audit(
            datetime.now().isoformat(),
            "system",
            "auto_pair_invoice",
            f'{{"invoice_id": "{invoice_id}", "delivery_id": "{delivery_id}", "confidence": {confidence}, "status": "{new_status}", "issues_count": {issues_count}}}'
        )
        
        logger.info(f"Auto-pair: Successfully paired invoice {invoice_id} with delivery note {delivery_id}")
        
        return {
            "paired": True,
            "invoice_id": invoice_id,
            "delivery_id": delivery_id,
            "score": confidence,
            "status": new_status,
            "issues_count": issues_count
        }
        
    except Exception as e:
        logger.error(f"Auto-pair: Error pairing invoice {invoice_id}: {e}", exc_info=True)
        return {
            "paired": False,
            "reason": "error",
            "error": str(e)
        }

