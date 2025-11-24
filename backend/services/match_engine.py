# -*- coding: utf-8 -*-
"""
Match Engine Module

This module implements invoice ↔ delivery note pairing logic as specified in
System Bible Section 2.6 (lines 183-188).

Matching Criteria:
- Date window ± 3 days
- Supplier must match
- Total difference ≤ 1% or ≤ £2 absolute
- Line-item match score > 0.8 → confirmed pair
- If no pair found → status UNMATCHED
"""

from __future__ import annotations
import logging
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from backend.db.pairs import (
    db_get_document, db_recent_docs, db_upsert_pair_suggest, date_from
)

LOGGER = logging.getLogger("owlin.services.match_engine")
LOGGER.setLevel(logging.INFO)

DB_PATH = "data/owlin.db"


def _get_db_connection():
    """Get database connection."""
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def find_matches(invoice_id: str, delivery_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Find matching delivery notes for an invoice.
    
    Implements System Bible Section 2.6 matching logic:
    - Date window ± 3 days
    - Supplier must match
    - Total difference ≤ 1% or ≤ £2 absolute
    - Line-item match score > 0.8 → confirmed pair
    
    Args:
        invoice_id: Invoice ID
        delivery_id: Optional specific delivery note ID to check
    
    Returns:
        List of matching pairs with confidence scores
    """
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get invoice details
        cursor.execute("""
            SELECT i.id, i.supplier, i.date, i.value, i.doc_id
            FROM invoices i
            WHERE i.id = ?
        """, (invoice_id,))
        
        inv_row = cursor.fetchone()
        if not inv_row:
            LOGGER.warning(f"Invoice {invoice_id} not found")
            return []
        
        invoice_id_db, supplier, invoice_date, invoice_total, invoice_doc_id = inv_row
        
        # Get invoice document for pairing logic
        invoice_doc = db_get_document(int(invoice_doc_id) if invoice_doc_id and invoice_doc_id.isdigit() else None)
        if not invoice_doc:
            # Try to get from documents table directly
            cursor.execute("""
                SELECT id, supplier, doc_date, total, doc_type
                FROM documents
                WHERE id = ?
            """, (invoice_doc_id,))
            
            doc_row = cursor.fetchone()
            if doc_row:
                invoice_doc = {
                    "id": doc_row[0],
                    "supplier": doc_row[1] or supplier,
                    "doc_date": doc_row[2] or invoice_date,
                    "total": doc_row[3] or invoice_total,
                    "doc_type": doc_row[4] or "invoice"
                }
            else:
                LOGGER.warning(f"Document {invoice_doc_id} not found")
                return []
        
        # Find delivery note candidates
        if delivery_id:
            # Check specific delivery note
            candidates = [db_get_document(int(delivery_id) if delivery_id.isdigit() else None)]
            candidates = [c for c in candidates if c]
        else:
            # Find all recent delivery notes
            candidates = db_recent_docs("delivery_note", supplier=supplier, days=14)
        
        matches = []
        
        for candidate in candidates:
            if not candidate:
                continue
            
            # Apply matching criteria from System Bible Section 2.6
            
            # 1. Supplier must match
            if not supplier or not candidate.get("supplier"):
                continue
            
            if supplier.lower() != candidate["supplier"].lower():
                continue
            
            # 2. Date window ± 3 days
            date_match = False
            if invoice_doc.get("doc_date") and candidate.get("doc_date"):
                try:
                    inv_date = date_from(invoice_doc["doc_date"])
                    del_date = date_from(candidate["doc_date"])
                    
                    if inv_date and del_date:
                        delta_days = abs((inv_date - del_date).days)
                        if delta_days <= 3:
                            date_match = True
                except Exception:
                    pass
            
            if not date_match:
                continue
            
            # 3. Total difference ≤ 1% or ≤ £2 absolute
            total_match = False
            invoice_total_val = invoice_doc.get("total") or invoice_total or 0.0
            delivery_total_val = candidate.get("total") or 0.0
            
            if invoice_total_val and delivery_total_val:
                total_diff = abs(invoice_total_val - delivery_total_val)
                max_total = max(abs(invoice_total_val), abs(delivery_total_val))
                
                # Check both conditions: ≤ 1% OR ≤ £2 absolute
                percent_diff = (total_diff / max_total * 100) if max_total > 0 else 0
                absolute_diff = total_diff
                
                if percent_diff <= 1.0 or absolute_diff <= 2.0:
                    total_match = True
            
            if not total_match:
                continue
            
            # 4. Line-item match score > 0.8 (if line items available)
            line_item_score = _calculate_line_item_match_score(invoice_id, candidate.get("id"))
            
            # Calculate overall confidence
            confidence = 0.0
            
            # Base confidence from date proximity
            if date_match:
                delta_days = abs((date_from(invoice_doc["doc_date"]) - date_from(candidate["doc_date"])).days)
                confidence = 0.90 - (delta_days * 0.02)
            
            # Boost from total match
            if total_match:
                confidence += 0.05
            
            # Boost from line item match
            if line_item_score > 0.8:
                confidence = max(confidence, line_item_score)
                # Confirmed pair
                status = "confirmed"
            else:
                # Suggested pair
                status = "suggested"
            
            confidence = min(confidence, 0.99)
            
            matches.append({
                "invoice_id": invoice_id,
                "delivery_id": str(candidate["id"]),
                "confidence": confidence,
                "status": status,
                "date_delta_days": delta_days if date_match else None,
                "total_delta": total_diff if total_match else None,
                "line_item_score": line_item_score
            })
        
        # Sort by confidence descending
        matches.sort(key=lambda x: x["confidence"], reverse=True)
        
        LOGGER.info(f"Found {len(matches)} matches for invoice {invoice_id}")
        return matches
        
    except Exception as e:
        LOGGER.error(f"Error finding matches: {e}")
        return []
    finally:
        conn.close()


def _calculate_line_item_match_score(invoice_id: str, delivery_id: Optional[str]) -> float:
    """
    Calculate line-item match score between invoice and delivery note.
    
    Returns score > 0.8 for confirmed pairs as per System Bible Section 2.6.
    
    Args:
        invoice_id: Invoice ID
        delivery_id: Delivery note ID
    
    Returns:
        Match score (0.0-1.0)
    """
    if not delivery_id:
        return 0.0
    
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get invoice line items
        cursor.execute("""
            SELECT description, qty, total
            FROM invoice_line_items
            WHERE invoice_id = ?
            ORDER BY line_number
        """, (invoice_id,))
        
        invoice_lines = cursor.fetchall()
        
        # Get delivery note line items (assuming same structure)
        # Note: This may need adjustment based on actual delivery note storage
        cursor.execute("""
            SELECT description, qty, total
            FROM invoice_line_items
            WHERE doc_id = ?
            ORDER BY line_number
        """, (str(delivery_id),))
        
        delivery_lines = cursor.fetchall()
        
        if not invoice_lines or not delivery_lines:
            return 0.0
        
        # Calculate match score using description similarity
        matched_items = 0
        total_items = len(invoice_lines)
        
        # Create lookup for delivery items
        delivery_lookup = {}
        for desc, qty, total in delivery_lines:
            desc_key = (desc or "").lower().strip()
            delivery_lookup[desc_key] = {"qty": qty, "total": total}
        
        # Match invoice items to delivery items
        for inv_desc, inv_qty, inv_total in invoice_lines:
            desc_key = (inv_desc or "").lower().strip()
            
            if desc_key in delivery_lookup:
                # Check quantity and total match
                del_item = delivery_lookup[desc_key]
                qty_match = abs((inv_qty or 0) - (del_item["qty"] or 0)) < 0.01
                total_match = abs((inv_total or 0) - (del_item["total"] or 0)) < 0.01
                
                if qty_match and total_match:
                    matched_items += 1
        
        # Calculate score
        if total_items > 0:
            score = matched_items / total_items
            return score
        
        return 0.0
        
    except Exception as e:
        LOGGER.warning(f"Error calculating line item match score: {e}")
        return 0.0
    finally:
        conn.close()


def score_pairs(invoice_id: str, delivery_id: str) -> float:
    """
    Score a specific invoice-delivery note pair.
    
    Args:
        invoice_id: Invoice ID
        delivery_id: Delivery note ID
    
    Returns:
        Confidence score (0.0-1.0)
    """
    matches = find_matches(invoice_id, delivery_id)
    
    for match in matches:
        if match["delivery_id"] == delivery_id:
            return match["confidence"]
    
    return 0.0


def confirm_pair(invoice_id: str, delivery_id: str) -> bool:
    """
    Confirm a pair (set status to 'confirmed').
    
    Args:
        invoice_id: Invoice ID
        delivery_id: Delivery note ID
    
    Returns:
        True if successful
    """
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Update pair status
        cursor.execute("""
            UPDATE pairs
            SET status = 'confirmed', decided_at = ?
            WHERE invoice_id = ? AND delivery_id = ?
        """, (datetime.now().isoformat(), invoice_id, delivery_id))
        
        if cursor.rowcount > 0:
            # Update invoice paired status
            cursor.execute("""
                UPDATE invoices
                SET paired = 1
                WHERE id = ?
            """, (invoice_id,))
            
            conn.commit()
            LOGGER.info(f"Pair confirmed: invoice={invoice_id}, delivery={delivery_id}")
            return True
        
        return False
        
    except Exception as e:
        LOGGER.error(f"Error confirming pair: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def set_unmatched_status(invoice_id: str) -> bool:
    """
    Set invoice status to UNMATCHED when no pair is found.
    
    Args:
        invoice_id: Invoice ID
    
    Returns:
        True if successful
    """
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if pair exists
        cursor.execute("""
            SELECT COUNT(*) FROM pairs
            WHERE invoice_id = ? AND status = 'confirmed'
        """, (invoice_id,))
        
        pair_count = cursor.fetchone()[0] or 0
        
        if pair_count == 0:
            # Mark as unmatched (could add a status field or use paired=0)
            cursor.execute("""
                UPDATE invoices
                SET paired = 0
                WHERE id = ?
            """, (invoice_id,))
            
            conn.commit()
            LOGGER.info(f"Invoice {invoice_id} marked as UNMATCHED")
            return True
        
        return False
        
    except Exception as e:
        LOGGER.error(f"Error setting unmatched status: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

